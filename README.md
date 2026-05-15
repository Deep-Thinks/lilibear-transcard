# lilibear-transcard · 栗栗熊透卡生成器

> 厦门大学美食协会的第三个 AI 产品（姊妹篇：[lilibear-world](https://github.com/Deep-Thinks/lilibear-world) · [explorecipe](https://github.com/Deep-Thinks/explorecipe)）

上传一张美食照片，让吉祥物**栗栗熊**和你的食物一起出镜，生成一张 INS 风 PVC 拍照透卡。

🐼 在线体验：<https://transcard.xmu-cuisine.club>

## 它是怎么工作的

```
[用户上传食物图]
      │
      ▼
[Gemini 3 Flash] ── is_food=false ──► 拒绝（"图片主体看起来不是食物"）
      │ is_food=true
      ▼
[gpt-image-2 /v1/images/edits]
   inputs:
     - 6 张栗栗熊参考图（refs/）
     - 1 张用户上传的食物图
   prompt: 固定的"INS 风 PVC 透卡"创意稿
      │
      ▼
[返回透卡 PNG] → 前端展示 + 下载
```

整个流程同步 ~30-60s，无 DB / 无任务队列。

## 本地跑

```bash
git clone https://github.com/Deep-Thinks/lilibear-transcard.git
cd lilibear-transcard
cp .env.example .env  # 填入 IMAGE_API_KEY 与 GEMINI_API_KEY
python3 server.py
# 浏览器打开 http://localhost:18084
```

依赖：仅 Python 3.8+ 标准库；可选 `python3-pil` 让生成图的长宽比自动匹配原图。

## 路由

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 单页前端 |
| GET | `/refs/<name>` | 栗栗熊参考图 |
| GET | `/api/healthz` | 健康检查 |
| POST | `/api/generate` | `multipart/form-data` 上传 `image` 字段，返回 `{ok, image_b64, image_mime, size, elapsed_sec, audit}` |

## 致谢

- 栗栗熊形象 · 厦门大学美食协会
- 图像生成 · OpenAI gpt-image-2（通过反代）
- 入口审核 · Google Gemini 3 Flash

## License

MIT
