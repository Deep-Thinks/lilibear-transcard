"""lilibear-transcard · 透卡生成器后端

姊妹项目：lilibear-world / explorecipe
依赖：仅 Python 标准库（可选 PIL 用于读取图片长宽比）

路由：
  GET  /                  → index.html
  GET  /refs/<name>       → 栗栗熊参考图（栗栗熊原始设计图、表情包等）
  POST /api/generate      → 上传食物图 → g3f 审核 → gpt-image-2 生成透卡 → 返回 PNG
  GET  /api/healthz       → 健康检查

设计原则：KISS——同步请求 / 不落 DB / 无任务队列。
用户上传 → 审核 → 生成 → 返回。整个流程 ~30-60s，前端 loading 等。
"""

# ============================================================
# stdlib
# ============================================================
import base64
import datetime
import http.server
import io
import json
import os
import re
import secrets
import socketserver
import ssl
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid


DOC_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_ROOT = os.path.join(DOC_ROOT, "logs")
REFS_DIR = os.path.join(DOC_ROOT, "refs")
IMG_LOG_DIR = os.path.join(LOG_ROOT, "images")
EVENT_LOG_PATH = os.path.join(LOG_ROOT, "events.jsonl")
CARDS_LOG_PATH = os.path.join(LOG_ROOT, "cards.jsonl")
INDEX_HTML_PATH = os.path.join(DOC_ROOT, "index.html")


# ============================================================
# .env 加载
# ============================================================
def _load_env():
    for fname in (".env.local", ".env"):
        p = os.path.join(DOC_ROOT, fname)
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()


# ============================================================
# 配置
# ============================================================
PORT = int(os.environ.get("PORT", "18084"))
BIND_HOST = os.environ.get("BIND_HOST", "::")

# —— gpt-image-2 ——
IMAGE_API_KEY = os.environ.get("IMAGE_API_KEY", "")
IMAGE_UPSTREAM_URL = os.environ.get(
    "IMAGE_UPSTREAM_URL", "https://image.token-recyclebin.com/v1/images/edits"
)
IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gpt-image-2")

# —— Gemini 3 Flash 审核（OpenAI 兼容协议中转） ——
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
# Google 的 OpenAI 兼容端点（Gemini API for OpenAI compat）：
#   POST {GEMINI_BASE_URL}/chat/completions
# 默认走官方 /v1beta/openai；CN 服务器若不通可改成 OpenAI-兼容中转的 base URL
GEMINI_BASE_URL = os.environ.get(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
).rstrip("/")
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "60"))

# 审核 fail-open：极低置信度的 not_food 放行（中转抖动兜底）
AUDIT_FAIL_OPEN_BELOW = float(os.environ.get("AUDIT_FAIL_OPEN_BELOW", "0.5"))

# —— 通用 ——
UPSTREAM_TIMEOUT = 600
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
RETRY_TIMES = 3
RETRY_BACKOFF_BASE = 2.0


# ============================================================
# 透卡生成 prompt（来自用户原始设计稿，禁改）
# ============================================================
TRANSCARD_PROMPT = """这是我们厦门大学美食协会的吉祥物栗栗熊的原始设计图（是一只小熊猫，不是小浣熊）。

参考图片中有一张图片是用户上传的美食照片，你需要根据用户上传的图像的食物和我们的栗栗熊，设计一张【INS风格的PVC吃饭拍照透卡】，叠加到原始照片上

**注意**：你必须120%参考我们的栗栗熊的画风，透卡的长宽比例应该与原图一致，且设计有INS风可爱的窄边框，【透卡应该占全图95%以上，基本覆盖全图】。栗栗熊必须吃的是图片上的食物其中之一，且位于画面右下角或者左下角。

**必须120%完全模仿参考图片的栗栗熊**来生成的照片，照片与透卡长宽比与原图必须完全一致，要有一只手拿着这张透卡的一个小角拍照，透卡上不能存在任何文字，占全图95%以上"""


# ============================================================
# g3f 审核 prompt（精简版：只判 is_food）
# ============================================================
AUDIT_PROMPT = """你是"透卡生成器"应用的入口图片审核器。判断图片**主体**是否为可食用的食物 / 菜品 / 饮品 / 食材。

判断规则：
- "主体"指占据画面注意力中心的物体；手、餐具、桌面、背景文字属于配角，不影响判断
- 即使是宣传图、菜单图，只要主体是食物，is_food = true
- 宠物、玩偶、毛绒玩具、人物、衣物、风景、随手物品、文档明确不是食物，is_food = false
- 模糊情况（半成品 / 原材料 / 包装食品）按"如果烹饪/打开后就是食物"判 true

严格 JSON 输出，不要额外文字：
{
  "is_food": true/false,
  "confidence": 0.0-1.0,
  "reason": "≤40字中文，说明图里主体是什么"
}
"""


# ============================================================
# 工具函数
# ============================================================
def _now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _ensure_dirs():
    os.makedirs(LOG_ROOT, exist_ok=True)
    os.makedirs(IMG_LOG_DIR, exist_ok=True)


def _detect_image_mime(data):
    """按字节签名判断真实 MIME。
    必须给真实类型 —— 上游会透传给 vision API，application/octet-stream 会被拒。"""
    if not data or len(data) < 12:
        return "application/octet-stream"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def _build_multipart(boundary, fields):
    """fields: list[(name, filename_or_None, bytes)].
    文件部分 Content-Type 按字节签名识别。"""
    out = []
    bnd = ("--" + boundary).encode("latin-1")
    for name, fn, data in fields:
        out.append(bnd + b"\r\n")
        if fn:
            ctype = (_detect_image_mime(data)
                     if isinstance(data, (bytes, bytearray))
                     else "application/octet-stream")
            disp = 'form-data; name="%s"; filename="%s"' % (name, fn)
            out.append(("Content-Disposition: " + disp + "\r\n").encode("latin-1"))
            out.append(("Content-Type: " + ctype + "\r\n\r\n").encode("latin-1"))
        else:
            out.append(('Content-Disposition: form-data; name="%s"\r\n\r\n'
                        % name).encode("latin-1"))
        if isinstance(data, str):
            data = data.encode("utf-8")
        out.append(data)
        out.append(b"\r\n")
    out.append(("--" + boundary + "--\r\n").encode("latin-1"))
    return b"".join(out)


def _parse_multipart(headers, body):
    """极简 multipart/form-data 解析。返回 list[(name, filename, bytes)]。
    用 list 而非 dict —— 上游会发同名 'image' 多次时不能互相覆盖。"""
    ctype = headers.get("Content-Type", "")
    m = re.search(r"boundary=([^;]+)", ctype)
    if not m:
        return None
    boundary = ("--" + m.group(1).strip().strip('"')).encode("latin-1")
    parts = body.split(boundary)
    out = []
    for p in parts:
        if not p or p in (b"--\r\n", b"--"):
            continue
        p = p.lstrip(b"\r\n")
        if p.endswith(b"\r\n"):
            p = p[:-2]
        if p.endswith(b"--"):
            p = p[:-2]
        sep = p.find(b"\r\n\r\n")
        if sep == -1:
            continue
        head_blob = p[:sep].decode("latin-1", errors="replace")
        data = p[sep + 4:]
        if data.endswith(b"\r\n"):
            data = data[:-2]
        dispo = ""
        for line in head_blob.split("\r\n"):
            if line.lower().startswith("content-disposition"):
                dispo = line
                break
        nm = re.search(r'name="([^"]*)"', dispo)
        fn = re.search(r'filename="([^"]*)"', dispo)
        if not nm:
            continue
        out.append((nm.group(1), fn.group(1) if fn else None, data))
    return out


_log_lock = threading.Lock()


def _write_event(payload):
    try:
        _ensure_dirs()
        payload.setdefault("ts", _now_iso())
        with _log_lock:
            with open(EVENT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        print("[event] write failed: %s" % e, file=sys.stderr)


def _strip_json_fence(s):
    s = s.strip()
    if s.startswith("```"):
        # 去掉首行 ```json 或 ```
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


def _safe_json_loads(text):
    try:
        return json.loads(text)
    except Exception:
        try:
            return json.loads(_strip_json_fence(text))
        except Exception:
            return None


# ============================================================
# 长宽比检测：根据原图选 gpt-image-2 size
# ============================================================
# gpt-image-2 / token-recyclebin 反代支持的常见尺寸（竖、横、方）
SUPPORTED_SIZES = [
    ("1024x1024", 1.0),
    ("1024x1536", 1024.0 / 1536.0),   # 竖 2:3
    ("1024x1792", 1024.0 / 1792.0),   # 竖 9:16
    ("1536x1024", 1536.0 / 1024.0),   # 横 3:2
    ("1792x1024", 1792.0 / 1024.0),   # 横 16:9
]


def _pick_size(img_bytes):
    """根据原图长宽比选最接近的 gpt-image-2 支持尺寸。失败回退 1024x1024。"""
    try:
        from PIL import Image
        w, h = Image.open(io.BytesIO(img_bytes)).size
        if not w or not h:
            return "1024x1024"
        ratio = w / float(h)
        best = min(SUPPORTED_SIZES, key=lambda x: abs(x[1] - ratio))
        return best[0]
    except Exception:
        return "1024x1024"


# ============================================================
# Gemini 3 Flash 审核（OpenAI 兼容协议）
# ============================================================
def call_gemini_audit(image_bytes):
    """单次 Gemini 调用判 is_food。
    返回 dict: {is_food, confidence, reason, elapsed}。失败抛 RuntimeError。"""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 未配置（检查 .env）")
    mime = _detect_image_mime(image_bytes) or "image/jpeg"
    if mime == "application/octet-stream":
        mime = "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {"role": "user", "content": [
                {"type": "text", "text": AUDIT_PROMPT},
                {"type": "image_url",
                 "image_url": {"url": "data:%s;base64,%s" % (mime, b64)}},
            ]},
        ],
        "temperature": 0.2,
        # Gemini 3 在 thinking 模式下会先吃掉一批 reasoning tokens，
        # max_tokens 太小会让 JSON 被截在中途。和 explorecipe 对齐到 4000。
        "max_tokens": 4000,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = GEMINI_BASE_URL + "/chat/completions"
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": "Bearer " + GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    t0 = time.time()
    last_err = None
    text = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=GEMINI_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
            j = json.loads(raw)
            choices = j.get("choices") or []
            if not choices:
                last_err = "上游无 choices: %s" % str(j)[:300]
            else:
                msg = choices[0].get("message") or {}
                content = msg.get("content")
                if isinstance(content, list):
                    text = "".join(
                        p.get("text", "") for p in content if isinstance(p, dict)
                    )
                else:
                    text = content or ""
                text = text.strip()
                break
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            last_err = "HTTP %d: %s" % (e.code, body_text)
        except Exception as e:
            last_err = "%s: %s" % (type(e).__name__, e)
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))

    if text is None:
        raise RuntimeError("Gemini 3 次重试均失败：%s" % last_err)

    elapsed = round(time.time() - t0, 2)
    parsed = _safe_json_loads(text)
    if parsed is None:
        raise RuntimeError("Gemini 返回非 JSON：%s" % text[:300])
    return {
        "is_food": bool(parsed.get("is_food")),
        "confidence": float(parsed.get("confidence") or 0.0),
        "reason": str(parsed.get("reason") or "")[:80],
        "elapsed": elapsed,
    }


# ============================================================
# gpt-image-2 生成透卡（用户图 + 6 张栗栗熊参考图）
# ============================================================
def _load_ref_images():
    """返回参考图字节列表：第 0 张是栗栗熊原始 logo，之后依次为 refs/*。
    multipart filename 用 ASCII-safe 占位（refs/ 里的中文文件名会让 latin-1 header 炸）。"""
    blobs = []
    logo_path = os.path.join(REFS_DIR, "lilibear_logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            blobs.append(("lilibear_logo.png", f.read()))
    if os.path.isdir(REFS_DIR):
        i = 0
        for name in sorted(os.listdir(REFS_DIR)):
            if name == "lilibear_logo.png":
                continue
            low = name.lower()
            if not (low.endswith(".jpg") or low.endswith(".jpeg")
                    or low.endswith(".png") or low.endswith(".webp")):
                continue
            with open(os.path.join(REFS_DIR, name), "rb") as f:
                blob = f.read()
            ext = low.rsplit(".", 1)[-1]
            blobs.append(("ref_%d.%s" % (i, ext), blob))
            i += 1
    return blobs


def call_image_gen(user_image_bytes, size):
    """调 gpt-image-2 生成透卡。
    multipart 字段：model / prompt / size / n / image (n+1 张) —— 用户图放最后一张。
    返回 (png_bytes, elapsed_sec)。失败抛 RuntimeError。"""
    if not IMAGE_API_KEY:
        raise RuntimeError("IMAGE_API_KEY 未配置（检查 .env）")

    ref_blobs = _load_ref_images()
    if not ref_blobs:
        raise RuntimeError("refs/ 目录为空，无栗栗熊参考图")

    boundary = "----transcard-" + uuid.uuid4().hex
    fields = [
        ("model", None, IMAGE_MODEL),
        ("prompt", None, TRANSCARD_PROMPT),
        ("size", None, size),
        ("n", None, "1"),
    ]
    # 栗栗熊参考图（多张 image 字段）
    for fname, blob in ref_blobs:
        fields.append(("image", fname, blob))
    # 用户图放最后，prompt 里写明"参考图片中有一张图片是用户上传的美食照片"
    user_mime = _detect_image_mime(user_image_bytes)
    user_ext = user_mime.split("/")[-1] if "/" in user_mime else "jpg"
    fields.append(("image", "user_food." + user_ext, user_image_bytes))

    body = _build_multipart(boundary, fields)
    headers = {
        "Authorization": "Bearer " + IMAGE_API_KEY,
        "Content-Type": "multipart/form-data; boundary=" + boundary,
        "Content-Length": str(len(body)),
    }
    ctx = ssl.create_default_context()

    t0 = time.time()
    last_err = None
    for attempt in range(RETRY_TIMES):
        req = urllib.request.Request(IMAGE_UPSTREAM_URL, data=body,
                                     headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=UPSTREAM_TIMEOUT) as resp:
                raw = resp.read()
            try:
                j = json.loads(raw.decode("utf-8"))
            except Exception:
                last_err = "上游响应非 JSON"
                if attempt < RETRY_TIMES - 1:
                    time.sleep(RETRY_BACKOFF_BASE * (attempt + 1))
                continue
            if not j or "data" not in j or not j["data"]:
                last_err = "上游返回无 data: %s" % str(j)[:200]
                if attempt < RETRY_TIMES - 1:
                    time.sleep(RETRY_BACKOFF_BASE * (attempt + 1))
                continue
            item = j["data"][0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"]), round(time.time() - t0, 2)
            if item.get("url"):
                with urllib.request.urlopen(item["url"], context=ctx, timeout=UPSTREAM_TIMEOUT) as ir:
                    return ir.read(), round(time.time() - t0, 2)
            last_err = "上游 data[0] 无 b64 或 url"
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                pass
            last_err = "HTTP %d: %s" % (e.code, body_text)
        except Exception as e:
            last_err = "%s: %s" % (type(e).__name__, e)
        if attempt < RETRY_TIMES - 1:
            time.sleep(RETRY_BACKOFF_BASE * (attempt + 1))

    raise RuntimeError("gpt-image-2 %d 次重试均失败：%s" % (RETRY_TIMES, last_err))


# ============================================================
# 持久化生成结果（debug / 归档用）
# ============================================================
def _persist_output(user_bytes, output_bytes, audit_info, short_id=None):
    """落盘到 logs/images/YYYYMMDD/<ts>_<id>/{input.jpg,output.png,meta.json}。
    返回 output.png 的绝对路径（供 cards.jsonl 映射）；失败返回 None。"""
    try:
        _ensure_dirs()
        day = datetime.datetime.now().strftime("%Y%m%d")
        hms = datetime.datetime.now().strftime("%H%M%S")
        rid = uuid.uuid4().hex[:8]
        sub = os.path.join(IMG_LOG_DIR, day, "%s_%s" % (hms, rid))
        os.makedirs(sub, exist_ok=True)
        in_ext = _detect_image_mime(user_bytes).split("/")[-1] or "jpg"
        with open(os.path.join(sub, "input." + in_ext), "wb") as f:
            f.write(user_bytes)
        out_path = os.path.join(sub, "output.png")
        with open(out_path, "wb") as f:
            f.write(output_bytes)
        with open(os.path.join(sub, "meta.json"), "w", encoding="utf-8") as f:
            json.dump({
                "ts": _now_iso(),
                "short_id": short_id,
                "audit": audit_info,
                "input_bytes": len(user_bytes),
                "output_bytes": len(output_bytes),
            }, f, ensure_ascii=False, indent=2)
        return out_path
    except Exception as e:
        print("[persist] failed: %s" % e, file=sys.stderr)
        return None


# ============================================================
# short_id 公开分享系统（C2）
# ============================================================
# short_id：8 字符 URL-safe，64^8 ≈ 281T 空间，单日 <1000 张碰撞概率 <1e-10。
# cards.jsonl 维护 short_id → 归档 PNG 的映射，供 /c/<id> 与 /api/card/<id>.png。
_SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,16}$")
_cards_lock = threading.Lock()


def _gen_short_id():
    return secrets.token_urlsafe(6)[:8]


def _existing_short_ids():
    """读 cards.jsonl 收集已用 short_id（写入前查重用）。"""
    ids = set()
    try:
        with open(CARDS_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sid = json.loads(line).get("short_id")
                    if sid:
                        ids.add(sid)
                except Exception:
                    continue
    except FileNotFoundError:
        pass
    return ids


def _record_card(short_id, output_path, size):
    """把 short_id → 归档 PNG 的映射追加进 cards.jsonl。
    写入成功返回 True；失败返回 False —— 调用方据此决定是否对外暴露 short_id。"""
    try:
        _ensure_dirs()
        rec = {
            "short_id": short_id,
            "file": os.path.relpath(output_path, DOC_ROOT),
            "ts": _now_iso(),
            "size": size,
        }
        with _cards_lock:
            with open(CARDS_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print("[cards] write failed: %s" % e, file=sys.stderr)
        return False


def _lookup_card(short_id):
    """在 cards.jsonl 里找 short_id，返回归档 PNG 的绝对路径；找不到返回 None。
    路径必须落在 IMG_LOG_DIR 内，防 jsonl 被篡改导致目录穿越。"""
    hit = None
    try:
        with open(CARDS_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("short_id") == short_id:
                    hit = rec   # 取最后一条匹配（理论上唯一）
    except FileNotFoundError:
        return None
    if not hit:
        return None
    abs_path = os.path.normpath(os.path.join(DOC_ROOT, hit.get("file", "")))
    if not abs_path.startswith(IMG_LOG_DIR):
        return None
    return abs_path if os.path.isfile(abs_path) else None


# ============================================================
# HTTP Handler
# ============================================================
class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # 沉默 BaseHTTPRequestHandler 默认 stderr 噪音；保留 print/_write_event
        sys.stderr.write("[%s] %s - %s\n" % (
            _now_iso(), self.address_string(), fmt % args))

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            return self._serve_file(INDEX_HTML_PATH, "text/html; charset=utf-8")
        if path == "/api/healthz":
            return self._send_json(200, {
                "ok": True,
                "ts": _now_iso(),
                "image_key": bool(IMAGE_API_KEY),
                "gemini_key": bool(GEMINI_API_KEY),
            })
        if path.startswith("/refs/"):
            return self._serve_ref(path[len("/refs/"):])
        if path.startswith("/api/card/"):
            return self._serve_card_png(path[len("/api/card/"):])
        if path.startswith("/c/"):
            return self._serve_card_redirect(path[len("/c/"):])
        return self._send_json(404, {"error": "not found", "path": path})

    def _serve_card_png(self, rel):
        """GET /api/card/<short_id>.png → 直接吐归档透卡 PNG，长缓存。"""
        rel = rel.strip("/")
        if rel.endswith(".png"):
            rel = rel[:-4]
        if not _SHORT_ID_RE.match(rel):
            return self._send_json(400, {"error": "bad short_id"})
        abs_path = _lookup_card(rel)
        if not abs_path:
            return self._send_json(404, {"error": "card not found"})
        return self._serve_file(abs_path, "image/png",
                                cache="public, max-age=31536000, immutable")

    def _serve_card_redirect(self, rel):
        """GET /c/<short_id> → 302 跳到 /api/card/<short_id>.png。"""
        rel = rel.strip("/")
        if not _SHORT_ID_RE.match(rel):
            return self._send_json(400, {"error": "bad short_id"})
        self.send_response(302)
        self.send_header("Location", "/api/card/%s.png" % rel)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve_file(self, abs_path, ctype, cache="no-store"):
        try:
            with open(abs_path, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            return self._send_json(404, {"error": "file not found"})
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    def _serve_ref(self, rel):
        # 防穿越
        if ".." in rel or rel.startswith("/"):
            return self._send_json(400, {"error": "bad path"})
        abs_path = os.path.normpath(os.path.join(REFS_DIR, rel))
        if not abs_path.startswith(REFS_DIR):
            return self._send_json(400, {"error": "bad path"})
        if not os.path.isfile(abs_path):
            return self._send_json(404, {"error": "ref not found"})
        low = abs_path.lower()
        ctype = ("image/png" if low.endswith(".png")
                 else "image/webp" if low.endswith(".webp")
                 else "image/jpeg")
        return self._serve_file(abs_path, ctype)

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/generate":
            return self._handle_generate()
        return self._send_json(404, {"error": "not found", "path": path})

    def _read_body(self, max_bytes):
        try:
            cl = int(self.headers.get("Content-Length", "0"))
        except Exception:
            cl = 0
        if cl <= 0:
            return None
        if cl > max_bytes:
            return False
        return self.rfile.read(cl)

    def _send_json(self, code, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _handle_generate(self):
        body = self._read_body(MAX_UPLOAD_BYTES + 1024 * 1024)
        if body is None:
            return self._send_json(400, {"error": "empty body"})
        if body is False:
            return self._send_json(413, {
                "error": "图片过大，最大 %d MB" % (MAX_UPLOAD_BYTES // 1024 // 1024)
            })
        parts = _parse_multipart(self.headers, body)
        if not parts:
            return self._send_json(400, {"error": "invalid multipart"})

        user_bytes = None
        for name, fn, data in parts:
            if name == "image":
                user_bytes = data
                break
        if not user_bytes:
            return self._send_json(400, {"error": "缺少字段 image"})

        if len(user_bytes) > MAX_UPLOAD_BYTES:
            return self._send_json(413, {"error": "图片过大"})

        mime = _detect_image_mime(user_bytes)
        if mime == "application/octet-stream":
            return self._send_json(400, {"error": "不支持的图片格式（仅 JPG/PNG/WEBP）"})

        # 1) g3f 审核
        try:
            audit = call_gemini_audit(user_bytes)
        except Exception as e:
            traceback.print_exc()
            _write_event({"type": "audit_error", "msg": str(e)[:300]})
            return self._send_json(503, {"error": "审核服务异常：" + str(e)[:200]})

        if not audit["is_food"]:
            # fail-open：极低置信度的 not_food 放行
            if audit["confidence"] < AUDIT_FAIL_OPEN_BELOW:
                _write_event({"type": "audit_fail_open", "audit": audit})
            else:
                _write_event({"type": "audit_reject", "audit": audit})
                return self._send_json(400, {
                    "error": "图片主体看起来不是食物",
                    "reason": audit.get("reason") or "",
                    "audit": audit,
                })

        _write_event({"type": "audit_pass", "audit": audit})

        # 2) 选 size + 调 gpt-image-2
        size = _pick_size(user_bytes)
        try:
            out_bytes, elapsed = call_image_gen(user_bytes, size)
        except Exception as e:
            traceback.print_exc()
            _write_event({"type": "image_gen_error", "msg": str(e)[:300],
                          "size": size})
            return self._send_json(502, {"error": "图像生成失败：" + str(e)[:200]})

        # 3) 分配 short_id（写前查重，碰撞极低概率兜底）+ 落盘 + 映射
        short_id = _gen_short_id()
        existing = _existing_short_ids()
        while short_id in existing:
            short_id = _gen_short_id()

        out_b64 = base64.b64encode(out_bytes).decode("ascii")
        saved = _persist_output(user_bytes, out_bytes, audit, short_id)
        # 仅当归档 + cards.jsonl 映射都落地，short_id 才可对外分享；
        # 否则 /c/<id> 必然 404，宁可不暴露分享 ID。
        shared = bool(saved) and _record_card(short_id, saved, size)
        _write_event({
            "type": "generate_done",
            "short_id": short_id,
            "shareable": shared,
            "audit": audit,
            "size": size,
            "elapsed_sec": elapsed,
            "input_bytes": len(user_bytes),
            "output_bytes": len(out_bytes),
            "saved_to": saved and os.path.relpath(saved, DOC_ROOT),
        })

        return self._send_json(200, {
            "ok": True,
            "short_id": short_id if shared else None,
            "size": size,
            "elapsed_sec": elapsed,
            "audit": audit,
            "image_b64": out_b64,
            "image_mime": "image/png",
        })


# ============================================================
# 启动
# ============================================================
import socket as _socket


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        host = (server_address[0] or "").strip()
        # 选地址族：含冒号视为 IPv6；空串/0.0.0.0/127.0.0.1 → IPv4
        if ":" in host:
            self.address_family = _socket.AF_INET6
        else:
            self.address_family = _socket.AF_INET
        super().__init__(server_address, RequestHandlerClass)


def _bind_server(host, port):
    """优先按 host 直接 bind；IPv6 不可用时回退到 0.0.0.0。"""
    try:
        return ThreadingHTTPServer((host, port), Handler), host
    except (OSError, _socket.gaierror) as e:
        if ":" in (host or ""):
            print("[server] %s bind 失败（%s），回退 0.0.0.0" % (host, e),
                  file=sys.stderr)
            return ThreadingHTTPServer(("0.0.0.0", port), Handler), "0.0.0.0"
        raise


def main():
    _ensure_dirs()
    print("=" * 60)
    print(" 栗栗熊透卡生成器 · 本地服务")
    print("=" * 60)
    print("  端口      : %d" % PORT)
    print("  监听      : %s" % BIND_HOST)
    print("  IMAGE_KEY : %s" % ("已配置" if IMAGE_API_KEY else "缺失！"))
    print("  GEMINI_KEY: %s" % ("已配置" if GEMINI_API_KEY else "缺失！"))
    print("  refs/     : %d 张参考图" % len(_load_ref_images()))
    print("  上游      : %s" % IMAGE_UPSTREAM_URL)
    print("=" * 60)

    server, actual_host = _bind_server(BIND_HOST, PORT)
    if actual_host != BIND_HOST:
        print("  实际监听: %s:%d" % (actual_host, PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] 关闭中…")
        server.server_close()


if __name__ == "__main__":
    main()
