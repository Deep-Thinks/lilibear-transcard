# transcard 设计升级方案

> 这份文档是 transcard 视觉 + UX + 留存升级的 single source of truth。
> 实施前先读一遍，实施完更新对应章节。
>
> **核心目标**：让 transcard 接入 lilibear-world / explorecipe 已经建立的视觉 DNA，把"调性 / 设计感"提到 9/10，并补上目前完全缺失的留存与分享回路。
>
> **决策日期**：2026-05-16
> **评审工具**：plan-design-review
> **依据文档**：`/niuniu869_dev/explorecipe/DESIGN.md`

---

## 0 · 当前问题诊断

| 维度 | 当前评分 | 目标评分 | 兑现阶段 |
|------|----------|----------|----------|
| 与姊妹项目视觉一致性 | 2/10 | 9/10 | A |
| 调性 / 设计语言 | 3/10 | 9/10 | A |
| UX（等待 / 错误 / 完成态）| 5/10 | 9/10 | B |
| 留存机制 | 0/10 | 7/10 | C |
| 分享机制 | 0/10 | 7/10 | B + C |

**核心问题**：姊妹项目（lilibear-world / explorecipe）已经在 `explorecipe/DESIGN.md` 沉淀了一套极强、极独特的设计 DNA——米黄纸 + 墨色 + 珊瑚红 + ZCOOL KuaiLe + 偏移硬阴影 + dashed 边 + 吉祥物 wave/bob 动效。

transcard 当前 `index.html` 每一条都踩反了：

- `font-family: -apple-system, "PingFang SC"` → 姊妹反模式 #2「我放弃排版」
- `box-shadow: 0 8px 28px rgba(170, 110, 40, 0.12)` → 姊妹反模式 #3 现代柔光阴影
- 色板 `#fff5e6 + #f4a259` 橙色系 → 跟姊妹的米黄 + 珊瑚红是两个宇宙
- logo 圆框无 drop-shadow 手绘感 → mascot 没人格
- 吉祥物零动效 → 失去品牌动作

用户从 `world.xmu-cuisine.club` 跳到 `transcard.xmu-cuisine.club` 会觉得是两个团队做的产品。**这是品牌资产被浪费的问题，不是工具好不好用的问题。**

---

## 1 · 三阶段路线图

```
A (视觉 DNA 接入) → B (UX 升级) → C (留存 + 分享 · 轻量版)
   ~3h 手工 / CC ~15min   ~半天 / CC ~30min   ~半天 / CC ~20min
```

依赖关系：A 是地基（提供 token / 组件 vocabulary），B 和 C 的所有新组件直接复用。倒序做会返工。

---

## A 阶段 · 视觉 DNA 接入

### A1 · 写 `transcard/DESIGN.md`

继承 `explorecipe/DESIGN.md` 的 token + 字体 + 阴影 + 反模式，记录 transcard 特定差异点：
- 没有 `<CanvasFrame>` 巨幅深色场景（transcard 产物本身就是图）
- 没有 `<DrawerRight>` 桌面右抽屉模式（transcard flow 是线性的，不需要持续抽屉）
- 结果图用**薄画框**（1.5px ink + 3px offset hard shadow），不是完整 CanvasFrame

### A2 · `:root` token 替换

```css
:root {
  --paper:    #fbf3e4;
  --paper-2:  #f3e7cf;
  --paper-3:  #ecdcb8;
  --ink:      #4a342a;
  --ink-soft: #6e4d3d;
  --accent:   #d8593a;    /* 珊瑚红 · 抛弃当前 #f4a259 橙色 */
  --accent-2: #b8451f;
  --leaf:     #6f9b5a;    /* 状态条 done 用 */
  --shadow:   rgba(80, 50, 30, 0.18);

  --font-display: 'ZCOOL KuaiLe', 'Ma Shan Zheng', sans-serif;
  --font-calligraphy: 'Ma Shan Zheng', 'ZCOOL KuaiLe', sans-serif;
  --font-body: 'Noto Sans SC', 'PingFang SC', sans-serif;

  --fs-xs: 11px; --fs-sm: 13px; --fs-md: 15px;
  --fs-lg: 19px; --fs-xl: 28px; --fs-xxl: 40px;

  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px;
  --sp-5: 24px; --sp-6: 32px; --sp-7: 48px;

  --r-sm: 6px; --r-md: 10px; --r-lg: 16px; --r-pill: 28px;
  --bw: 2.5px; --bw-thin: 1.5px;

  --shadow-stamp:      3px 3px 0 var(--ink);
  --shadow-stamp-lg:   4px 4px 0 var(--ink);
  --shadow-stamp-sm:   2px 2px 0 var(--ink);
  --shadow-stamp-soft: 4px 4px 0 var(--shadow);

  --t-fast: 0.15s ease;
  --t-mid:  0.25s ease;
  --t-slow: 0.4s cubic-bezier(.4,1.4,.5,1);
}
```

**全文搜索删除** 当前 CSS 里所有 `0 8px 28px rgba(...)` 形态柔光阴影，全部改 `--shadow-stamp` 系列。

### A3 · Google Fonts 接入

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=ZCOOL+KuaiLe&family=Ma+Shan+Zheng&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
```

已在 lilibear-world / explorecipe 生产环境验证国内访问可用。

### A4 · Header / Logo 改造

```css
header .logo-wrap {
  width: 96px; height: 96px;
  filter: drop-shadow(3px 3px 0 var(--ink)) drop-shadow(0 2px 4px var(--shadow));
  transition: transform 0.2s ease;
}
header .logo-wrap:hover { transform: translateY(-2px) rotate(-3deg); }
```

去掉 logo 的 `border-radius: 50%` + `background: #fff` 圆白底——直接出 mascot drop-shadow 手绘感。

### A5 · Tagline 文案 + 字体

```html
<h1>跟栗栗熊一起出镜</h1>
<p class="tagline">PVC 拍照透卡 · 厦门大学美食协会</p>
```

```css
h1 {
  font-family: var(--font-display);   /* ZCOOL KuaiLe */
  font-size: var(--fs-xl);            /* 28px */
  font-weight: 400;
  letter-spacing: 2px;
  color: var(--accent-2);
  text-shadow: 2px 2px 0 var(--paper-2);
  line-height: 1.1;
}
.tagline {
  font-family: var(--font-calligraphy);  /* Ma Shan Zheng */
  font-size: var(--fs-md);
  color: var(--ink-soft);
}
```

### A6 · 按钮系统重写

按 `explorecipe/DESIGN.md` § 2.1 的 `<Btn>` 形态：

```css
.btn {
  font-family: var(--font-display);
  padding: var(--sp-3) var(--sp-5);
  border-radius: var(--r-pill);
  border: var(--bw) solid var(--ink);
  background: var(--paper-2);
  color: var(--ink);
  letter-spacing: 1px;
  transition: transform var(--t-fast), box-shadow var(--t-fast);
  min-height: 44px;
}
.btn.primary {
  background: var(--accent);
  color: #fff;
  box-shadow: var(--shadow-stamp);
}
.btn.primary:hover {
  background: var(--accent-2);
  transform: translate(-1px, -1px);
  box-shadow: var(--shadow-stamp-lg);
}
.btn.primary:active {
  transform: translate(2px, 2px);
  box-shadow: var(--shadow-stamp-sm);
}
.btn.ghost { background: transparent; box-shadow: none; }
```

### A7 · 上传卡 + 状态条改造

```css
.card {
  background: var(--paper-2);
  border: var(--bw) solid var(--ink);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow-stamp);
}
.uploader {
  border: var(--bw-thin) dashed var(--ink-soft);
  background: var(--paper);
}
.uploader:hover, .uploader.dragover {
  background: var(--paper-3);
  border-color: var(--accent);
}
```

### A8 · 结果图薄画框（关键产品视觉）

```css
.result-img {
  width: 100%; height: auto;
  border: var(--bw-thin) solid var(--ink);  /* 1.5px 墨色细边 */
  border-radius: var(--r-sm);
  box-shadow: var(--shadow-stamp);  /* 3px 偏移硬阴影 */
}
```

**强调**：1.5px 细边 + 3px 偏移阴影。如果 border 太粗会盖住透卡本身的设计；如果没有阴影会失去"贴在纸上的产品"感。

### A9 · Footer 升级

```css
footer {
  font-family: var(--font-calligraphy);
  color: var(--ink-soft);
}
footer a {
  color: var(--accent-2);
  text-decoration: none;
  border-bottom: var(--bw-thin) dashed var(--accent-2);
}
```

### A 阶段验证标准

- [ ] 用户从 `world.xmu-cuisine.club` 跳到 `transcard.xmu-cuisine.club`，"视觉一致"——同一系列产品观感
- [ ] 截图发朋友圈，能被认出"栗栗熊出品"
- [ ] DevTools 全文搜索 `box-shadow: 0` 找不到柔光阴影残留
- [ ] DevTools 全文搜索 `system-ui` / `-apple-system` 找不到主字体引用
- [ ] 移动端 logo hover 时 wave 动效正常

---

## B 阶段 · UX 升级（依赖 A）

### B1 · CONFIRM 抽屉（消除 explorecipe 痛点 #2）

**触发**：上传 + preview 后，点主按钮"让栗栗熊出镜"

**形态**：
- 移动端（<768px）：`<DrawerBottom>` 从底部上拉，`border-top: var(--bw) solid var(--ink) + border-radius: var(--r-lg) var(--r-lg) 0 0 + box-shadow: 0 -8px 0 var(--ink)`，含顶部把手 + ESC 关闭 + focus trap
- 桌面端：inline confirm——preview 卡变形，按钮区换成 "确认 / 再想想"

**内容**：
```
  把手
  ┌─────────────────────────────────────┐
  │ [mascot wave 96px]                   │
  │                                       │
  │   让栗栗熊跟它合个影？               │  ← ZCOOL KuaiLe, fs-xl
  │                                       │
  │ [缩略图 200px max-edge]               │
  │                                       │
  │ [Pill: ETA ~60s]                      │
  │                                       │
  │ ┌─────────────────┐ ┌─────────────┐ │
  │ │ 开始 (primary)   │ │ 再想想 (ghost) │
  │ └─────────────────┘ └─────────────┘ │
  └─────────────────────────────────────┘
```

### B2 · 三阶段进度（替换当前静态 ①②③）

**形态**：

```
  [MascotBob spin-bob 96px]

       ●━━━━━━●━━━━━━○
     审核中   绘制中   完工

  主 quip: "栗栗熊正在调长宽比…"
  副 quip: "已用 12s · 通常 60-90s"
```

**进度圈状态**（参考 `explorecipe/DESIGN.md` § 2.7）：
- `pending`: 纸黄填充 + 墨色细边
- `active`: 珊瑚红填充 + 墨色粗边 + 内部小 dot 脉冲
- `done`: 绿叶色填充 + 墨色粗边 + ✓

**绘制阶段 quip 池**（5-7s 轮播）：
- 「栗栗熊在调长宽比…」
- 「栗栗熊在挑滤镜…」
- 「栗栗熊在选 INS 取景角度…」
- 「栗栗熊在数像素…」
- 「栗栗熊在排版站位…」

**超时**：>90s 显示「上游堵车，再等等 / 取消」链接

### B3 · Toast 错误（替换当前 `.status.error` 嵌入式红块）

**形态**：顶部 fixed banner，珊瑚红边，墨色偏移阴影，`role="alert" + aria-live="assertive"`，5s 自动消（hover 暂停）

**文案池**：

| 错误类型 | 当前 | 升级 |
|----------|------|------|
| 审核拒绝 | `上游错误 503 · g3f reason: not_food` | 「栗栗熊看了半天没认出食物 · **换一张** 试试」 |
| 上游 5xx | `上游错误 500` | 「AI 这一关挤堵了 · **重试**」 |
| 文件超限 | `图片过大（最大 12MB）` | 「图片太大啦（>12MB）· **换张小点的**」 |
| 格式错误 | `只支持 JPG / PNG / WEBP 格式` | 「这格式栗栗熊不认 · JPG / PNG / WEBP 都行」 |

### B4 · 完成态仪式感

**触发**：透卡 base64 解码完成、`resultImg.src` 设置完成

**动效顺序**：
1. mascot wave 一次性 0.8s
2. 大字「叮——完工！」从下方滑入 0.4s
3. 三个按钮淡入

**三按钮**（按重要性排）：

| 文案 | 形态 | 行为 |
|------|------|------|
| **下载透卡** | primary | 现有逻辑 |
| **分享给朋友** | ghost | `navigator.share({files: [pngFile]})`，不支持时降级 `navigator.clipboard.write([new ClipboardItem(...)])` |
| **换个风格再来一张** | ghost | 保留 `currentFile`，直接调 `submit()` 拿新结果 |

### B5 · 杂项默认决策

- 当前 `换一张 / 再做一张` 语义混淆 → 改成：
  - 上传卡内：**换张图**（清空上传，回上传态）
  - 完成态：**换个风格再来一张**（保留 currentFile，重新提交）+ **全部重来**（清空回首页）
- 错误状态 spinner 立刻停（修当前 `setStages('idle')` 的 race）
- 状态条文案删 `①②③` → 改用 `<StageTrack>` 进度圈

### B 阶段验证标准

- [ ] 上传后点主按钮 → 出 CONFIRM 抽屉，确认后才发请求
- [ ] 60s loading 期间 mascot spin-bob 持续摇头，quip 每 5-7s 切换
- [ ] 故意 503 / 上传 >12MB / 上传 .gif，三种错误走 Toast，不嵌卡内
- [ ] 完成态 mascot wave + 大字浮现 + 三按钮顺序正确
- [ ] 移动 Safari / Chrome 上 navigator.share 能弹出系统分享面板
- [ ] 桌面 Chrome navigator.share 不支持时自动降级"复制图片"提示

---

## C 阶段 · 留存 + 分享（轻量版，依赖 A、B）

### C1 · localStorage 个人收藏夹（纯前端）

**数据结构**：
```js
// localStorage key: 'lilibear_transcard_gallery'
[
  {
    id: 'local-1716000000000-x4f2',     // 本地 uuid
    short_id: 'a7b3c9d2',                // 后端 8 字符 nanoid (C2 之后回填)
    thumb_b64: 'iVBORw0KGgoAAAA...',     // 256px max-edge 压缩缩略图
    filename: 'food.jpg',                 // 原文件名
    ts: 1716000000000,                    // 生成时间
    size: '1024x1536'                     // 尺寸
  },
  ...
]
```

**容量管理**：
- max 100 张（FIFO 滚动）
- 缩略图压缩：原图 PNG → canvas resize 到 256px max-edge → toDataURL('image/webp', 0.85)（webp 比 png 小 70%）
- 估算：100 张 × 30KB = 3MB，留 2MB buffer

**首页位置**：
- 标题下方加一个新卡片 `<HistoryStrip>`
- 仅当 localStorage 有 ≥1 张时显示
- 横向滚动卷轴，每张缩略图 80×120px
- 点击缩略图 → 弹出大图 + 「下载 / 分享 / 删除」三按钮

### C2 · 后端 short_id + 公开 PNG

**改动 `server.py`**：

1. 生成时分配 `short_id`：
```python
import secrets
def gen_short_id():
    return secrets.token_urlsafe(6)[:8]  # 8 字符 URL-safe
```

2. 生成 + 归档时多写一个 mapping 文件：
```python
# logs/images/{ts}_{short_id}.png 已经在归档了
# 新增 logs/cards.jsonl 维护映射
{"short_id": "a7b3c9d2", "file": "20260516_120000_a7b3c9d2.png", "ts": "...", "size": "1024x1536"}
```

3. 新增路由 `GET /c/<short_id>`：
```python
# 读 cards.jsonl 找到对应文件，redirect 到 /api/card/<short_id>.png
```

4. 新增路由 `GET /api/card/<short_id>.png`：
```python
# 从 logs/images/ 直接吐文件，Cache-Control: public, max-age=31536000
```

5. `/api/generate` 响应里多带 `short_id` 字段，前端拿到后写进 localStorage 那条记录

**前端**：
- 分享按钮点击时优先用 `https://transcard.xmu-cuisine.club/c/${short_id}` 作为分享 URL
- navigator.share 同时带 url + files，对方收到的体验是：链接预览 = 透卡图

**为什么不写 HTML 页**：
- 微信 / Telegram / iMessage 粘贴 PNG URL 都会自动出图片预览
- 不需要 OG 合成，节省 PIL + 模板逻辑
- 后续如果要升级到完整 OG 卡片，C2 已经把 short_id 系统搭好了，只需要加一层 HTML wrapper

### C4 · 二次创作钩子

完成态出现 0.8s 后，"换个风格再来一张" 按钮上方弹出一次性小气泡：

```
  ┌──────────────────────┐
  │ 想试试别的风格？     │  ← Ma Shan Zheng, fs-sm
  └──────────────────────┘
        ↓
  [换个风格再来一张]
```

气泡 3s 后自动消，或用户点了按钮立即消。每个 session 只显示一次（sessionStorage 标记）。

### C 阶段不做的事

- ❌ **公开广场**——超出"很简单"定位，跑一段时间看数据再决定升级
- ❌ **OG image 服务端合成**——粘贴 PNG URL 体验已经够用
- ❌ **公开页面 HTML 模板**——直接 PNG redirect 更简单
- ❌ **opt-in 隐私 toggle**——没有广场就没有隐私问题
- ❌ **举报机制**——没有公开内容就不需要

### C 阶段验证标准

- [ ] 生成一张透卡 → 刷新首页 → "我的透卡" 卷轴显示这张
- [ ] localStorage 满 100 张时新增不报错，最老的被滚出
- [ ] 完成态分享按钮 → 移动 Safari 系统分享 → 复制链接 → 粘贴到微信 → 出图片预览
- [ ] 直接访问 `https://transcard.xmu-cuisine.club/c/a7b3c9d2` → 返回 PNG（302 redirect 或直出均可）
- [ ] 完成态 0.8s 后气泡出现，3s 后消失，sessionStorage 标记不重复弹

---

## 2 · 完整文件改动清单

### A 阶段
- ✏️ `index.html`（重写 `<style>` 块 + header DOM 结构 + button class 名）
- 🆕 `DESIGN.md`（新建）

### B 阶段
- ✏️ `index.html`（加 CONFIRM 抽屉 DOM + StageTrack DOM + Toast DOM + 完成态三按钮；JS 加 navigator.share、quip 轮播定时器、CONFIRM 状态机）
- ✏️ `DESIGN.md`（更新组件 vocabulary）

### C 阶段
- ✏️ `index.html`（加 HistoryStrip DOM + localStorage CRUD + 缩略图压缩函数 + 气泡组件 + 分享 URL 拼接）
- ✏️ `server.py`（加 short_id 生成 + cards.jsonl 写入 + `/c/<id>` 和 `/api/card/<id>.png` 两个路由）
- ✏️ `nginx-transcard.conf` 可能需要：`/c/` 和 `/api/card/` 路径走反代（默认通配应该已经够）
- ✏️ `DESIGN.md`（更新 HistoryStrip 组件）

---

## 3 · 风险点 + 回滚

| 风险 | 概率 | 缓解 | 回滚 |
|------|------|------|------|
| Google Fonts 国内访问慢 | 低 | lilibear-world / explorecipe 已验证 | 加 `font-display: swap` |
| `navigator.share` 桌面浏览器不支持 | 高（设计内） | 降级"复制图片到剪贴板" | 已在 B4 设计内 |
| localStorage 超 5MB | 低 | FIFO + webp 压缩 | catch QuotaExceededError 弹 Toast |
| short_id 碰撞 | 极低 | 8 字符 URL-safe = 64^8 ≈ 281T 空间，单日 <1000 张时碰撞概率 <1e-10 | jsonl 写前查重 |
| OG 预览效果不达预期 | 中 | 先用 PNG redirect 测试 1 周，再决定是否上完整 HTML 页 | C2 已留扩展位 |
| 透卡 PNG URL 被爬虫批量拉 | 低 | logs/images/ 已经是公开归档（生成时落地）；加 nginx rate limit 兜底 | 改 short_id 长度到 12 字符提升暴力难度 |

每个阶段独立可验证、独立可回滚。建议每阶段单独 PR：

- PR #1: A 阶段（纯前端，不动后端 / systemd）
- PR #2: B 阶段（纯前端，不动后端 / systemd）
- PR #3: C 阶段（前端 + server.py 小改 + 可能的 nginx 调整）

---

## 4 · 实施顺序建议（每阶段内）

### A 阶段（建议一次提交）
1. import Google Fonts + 替换 `:root` token
2. 改 header / logo / tagline / h1 字体
3. 改按钮系统
4. 改卡片 / 上传区 / 状态条
5. 改结果图薄画框
6. 改 footer
7. 写 DESIGN.md

### B 阶段（建议分 4 个子提交）
1. Toast 组件 + 错误文案池
2. CONFIRM 抽屉
3. StageTrack 三阶段进度 + quip 轮播
4. 完成态仪式 + 三按钮 + navigator.share

### C 阶段（建议分 2 个子提交）
1. 后端：`short_id` + `/c/<id>` + `/api/card/<id>.png` + cards.jsonl
2. 前端：HistoryStrip + 缩略图压缩 + 气泡 + 分享 URL 拼接

---

## 5 · 决策日志

| 决策 ID | 议题 | 选定 | 日期 |
|---------|------|------|------|
| D1 | 升级方向优先级 | A → B → C 顺序 | 2026-05-16 |
| D2 | 结果图装裱 | 薄墙画框（1.5px ink + 3px offset shadow）| 2026-05-16 |
| D3 | Tagline 调性 | 极简口号「跟栗栗熊一起出镜」+ 副 | 2026-05-16 |
| D4 | 实施节奏 | 先把 B、C 也详细规划完再动手 | 2026-05-16 |
| D5 | CONFIRM 抽屉 | 保留（姊妹一致）| 2026-05-16 |
| D6 | 分享按钮上线时机 | B 阶段上 navigator.share + C 阶段拓展 short_id | 2026-05-16 |
| D7 | C 阶段重量 | 轻量版（贴合 "很简单很简单" 定位）| 2026-05-16 |

---

## 6 · 引用

- 视觉 DNA 来源：`/niuniu869_dev/explorecipe/DESIGN.md`
- 姊妹项目实现参考：`/niuniu869_dev/lilibear_world/index.html`、`/niuniu869_dev/explorecipe/index_v2.html`
- 评审记录：本仓库 `git log` + 本文件
- 评审工具：plan-design-review

---

## 7 · GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Design Review | `/plan-design-review` | UI/UX 升级评审 | 1 | CLEAR (PLAN) | 评分 3/10 → 9/10（A 阶段达成）；7 个决策已锁定；3 个 PR 路径已规划 |
| CEO Review | `/plan-ceo-review` | 战略 / 范围 | 0 | — | — |
| Eng Review | `/plan-eng-review` | 架构 / 测试 | 0 | — | — |
| DX Review | `/plan-devex-review` | 开发者体验 | 0 | — | — |

- **UNRESOLVED**: 0
- **VERDICT**: DESIGN CLEARED — 可以进入实施。如果需要进一步的工程审视（特别是 C2 的后端 short_id 系统 + nginx 路由），可在 A、B 完成后跑一次 `/plan-eng-review`。
