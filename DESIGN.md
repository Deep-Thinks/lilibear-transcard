# transcard · 设计系统

> 这份文档是 transcard UI 的 single source of truth。所有 token、组件 vocabulary、和它们的设计依据都在这里。改 UI 之前先读这页，改完之后同步这页。
>
> 视觉 DNA 继承自姊妹项目 lilibear-world / explorecipe（同一系列，独立开源）。源文档：`explorecipe/DESIGN.md`。

---

## 0 · 设计哲学

1. **手工纸感**——米黄纸为底、墨色为边、偏移硬阴影为签名。
2. **每个昂贵动作都要先看到目标**——调用 60-90s 上游生成的 click 必须先进 CONFIRM 抽屉（吉祥物 wave + 大字目标 + 缩略图 + ETA + 主/次按钮）。
3. **等待是讲故事的窗口**——60-90s loading 用三阶段进度 + 摇头吉祥物（spin-bob）+ 轮播 quip + 计时器。
4. **删 emoji、用中文 + 情境符号**——只保留 `~` `›` `→` `✓` `✕` 等情境性符号。
5. **错误是平静的、可恢复的**——所有错误统一走顶部 toast banner，5s 自动消（hover 暂停）。

---

## 1 · 视觉 token

完整 CSS variables 见 `index.html` 的 `:root` 块。任何新模块只能引用 token，不得硬编码。

### 1.1 色板

```css
--paper:    #fbf3e4;   /* 米黄底色 · UI 主背景 */
--paper-2:  #f3e7cf;   /* 次级背景 · 卡片填充 */
--paper-3:  #ecdcb8;   /* 三级背景 · hover state */
--ink:      #4a342a;   /* 主文字 · 深褐 / 边框 */
--ink-soft: #6e4d3d;   /* 次级文字 · 灰褐 (4.5:1 对 paper) */
--accent:   #d8593a;   /* 主强调 · 珊瑚红 · CTA / active 状态 */
--accent-2: #b8451f;   /* 强调深 · hover / 大标题 */
--leaf:     #6f9b5a;   /* 状态条 done */
--shadow:   rgba(80, 50, 30, 0.18);  /* 偏移投影色 */
```

### 1.2 字体

```css
--font-display:     'ZCOOL KuaiLe', 'Ma Shan Zheng', sans-serif;  /* 大标题 / 按钮 */
--font-calligraphy: 'Ma Shan Zheng', 'ZCOOL KuaiLe', sans-serif;  /* 副标 / 角标 */
--font-body:        'Noto Sans SC', 'PingFang SC', sans-serif;     /* 正文 */
```

**`-apple-system` / `system-ui` / `BlinkMacSystemFont` 永久禁用作为主字体**——AI slop 信号「我放弃排版」。字体由 Google Fonts 加载，国内访问已在姊妹项目生产环境验证可用。

### 1.3 字号 / 间距 / 圆角 / 边框

```css
--fs-xs: 11px;  --fs-sm: 13px;  --fs-md: 15px;
--fs-lg: 19px;  --fs-xl: 28px;  --fs-xxl: 40px;

--sp-1: 4px;  --sp-2: 8px;  --sp-3: 12px;  --sp-4: 16px;
--sp-5: 24px; --sp-6: 32px; --sp-7: 48px;

--r-sm: 6px; --r-md: 10px; --r-lg: 16px; --r-pill: 28px;
--bw: 2.5px;  --bw-thin: 1.5px;
```

### 1.4 投影（核心视觉签名）

```css
--shadow-stamp:      3px 3px 0 var(--ink);
--shadow-stamp-lg:   4px 4px 0 var(--ink);   /* hover 抬升 */
--shadow-stamp-sm:   2px 2px 0 var(--ink);   /* 小元件 / active 下沉 */
--shadow-stamp-soft: 4px 4px 0 var(--shadow);
```

**永久禁止现代柔光阴影** `0 8px 24px ...`、`drop-shadow(0 4px 12px ...)`。所有阴影必须是偏移硬阴影。

吉祥物 PNG 用两层叠加：`filter: drop-shadow(3px 3px 0 var(--ink)) drop-shadow(0 2px 4px var(--shadow));`——硬阴影做风格，柔影做体积。

### 1.5 动效

```css
--t-fast: 0.15s ease;  --t-mid: 0.25s ease;
--t-slow: 0.4s cubic-bezier(.4,1.4,.5,1);
```

keyframes：`wave`（确认抽屉吉祥物挥手）、`spin-bob`（loading 摇头浮动）、`pulse`（active 进度圈小点）、`rise`（完成态元素浮入）、`toast-in`。

`prefers-reduced-motion` 下：所有动画归零、吉祥物静态。

---

## 2 · 组件 vocabulary

### 2.1 `<Btn>`

| variant | 用途 |
|---|---|
| `.btn.primary` | 主行动。珊瑚红 + offset shadow |
| `.btn.ghost`   | 次级。透明 + ink 边 |
| `.btn.icon`    | 仅图标。36px 圆形、`aria-label` 必需 |
| `.btn.block`   | full-width 修饰类 |

hover：`translate(-1px,-1px) + shadow-stamp-lg`。active：`translate(2px,2px) + shadow-stamp-sm`。focus-visible：`--accent` 2.5px outline。

### 2.2 `<Pill>`

`--r-pill` 圆角 + dashed ink-soft 边 + paper-2 填。用于 ETA / 次要标识。

### 2.3 `<MascotBob>`

吉祥物图像，统一引用 `/refs/lilibear_logo.png`。三种状态：静态（drop-shadow）、`wave`（确认抽屉）、`spin-bob`（loading）。

### 2.4 `<DrawerBottom>`

移动端从底部上拉的 sheet：`border-top: var(--bw) solid var(--ink)` + `border-radius: var(--r-lg) var(--r-lg) 0 0` + `box-shadow: 0 -8px 0 var(--ink)`。带顶部把手 + ESC 关闭 + focus trap。桌面端（≥768px）退化为居中模态（去掉把手、四边 ink 边）。

> **与 explorecipe 的差异**：transcard 流程是线性的，**不需要 `<DrawerRight>` 桌面右抽屉**——确认对话在桌面端用居中模态即可。

### 2.5 `<ToastBanner>`

错误统一形态。顶部 fixed、`--accent` 边、`--shadow-stamp`、`role="alert"` + `aria-live="assertive"`。5s 自动消（hover 暂停）。成功提示用 `.toast.ok`（`--leaf` 边）。永久取代 `alert()` 和嵌入式红块。

### 2.6 `<StageTrack>`

Loading 三段进度圈，虚线连接。`pending` 纸黄填 + 数字；`active` 珊瑚红填 + 脉冲小点；`done` 绿叶填 + ✓。对应三阶段：审核 → 绘制 → 完工。

### 2.7 `<HistoryStrip>`

首页个人收藏夹（localStorage，纯前端）。横向滚动卷轴，缩略图 80×120px、`--bw-thin` ink 边 + `--shadow-stamp-sm`。仅当收藏夹 ≥1 张时显示。点击 → lightbox（下载 / 分享 / 删除）。

### 2.8 结果图薄画框

> **transcard 特定组件**：透卡产物本身就是图，**不使用 explorecipe 的 `<CanvasFrame>` 巨幅深色场景**。

结果图装裱用「薄画框」：`border: var(--bw-thin) solid var(--ink)`（1.5px 墨色细边）+ `box-shadow: var(--shadow-stamp)`（3px 偏移硬阴影）+ `--r-sm` 圆角。

设计依据：border 太粗会盖住透卡本身的设计；没有阴影会失去「贴在纸上的产品」感。

---

## 3 · 屏幕级 patterns

### 3.1 首页 (UPLOAD)

- `<Header>`：mascot（96px，hover 上浮 + 转）+ ZCOOL h1「跟栗栗熊一起出镜」+ Ma Shan Zheng 副标
- `<HistoryStrip>`（条件显示）
- 上传卡：dashed 边上传区 + preview + `<Btn primary>`「让栗栗熊出镜」+ `<Btn ghost>`「换张图」

### 3.2 CONFIRM（痛点解法）

- 触发：上传 + preview 后点「让栗栗熊出镜」
- 形态：`<DrawerBottom>`（移动）/ 居中模态（桌面）
- 内容：把手 + `<MascotBob wave>` + 大字「让栗栗熊跟它合个影？」+ 缩略图（200px）+ `<Pill ETA>` + `<Btn primary>`「开始」+ `<Btn ghost>`「再想想」

### 3.3 LOADING

- `<MascotBob spin-bob>` + `<StageTrack>` + 主 quip + 副 quip（计时器「已用 Ns · 通常 60-90s」）
- 三阶段：审核 → 绘制 → 完工。审核→绘制无后端进度事件，~5s 启发式切换
- 绘制阶段 quip 池 6s 轮播；>90s 显示「上游堵车 / 取消」链接

### 3.4 完成态

- `<MascotBob wave>` 隐含在大字浮现里
- 动效顺序：大字「叮——完工！」浮入 → 结果图（薄画框）→ 三按钮淡入
- 三按钮：`下载透卡`(primary) / `分享给朋友`(ghost) / `换个风格再来一张`(ghost) + `全部重来`(ghost block)
- 二次创作气泡：完成 0.8s 后在「换个风格」按钮上方弹出，3s 消，每 session 一次（sessionStorage）

### 3.5 错误 toast

任何 fetch 失败、审核拒绝、文件超限 → `<ToastBanner>`。文案规范：拒绝技术黑话，用人话 + 加粗行动词。

---

## 4 · 响应式断点

```
mobile  : < 768    默认；CONFIRM 走 DrawerBottom
desktop : >= 768   CONFIRM 走居中模态
```

---

## 5 · A11y 清单

- [x] 所有 button 有可读 label（icon-only 加 `aria-label`）
- [x] 关键 `<img>` 有具体 alt
- [x] focus-visible：button 显示 `--accent` outline
- [x] 触摸目标 ≥ 44px（`.btn` min-height 44px）
- [x] `--ink-soft` = `#6e4d3d` 满足 4.5:1
- [x] `prefers-reduced-motion`：动画归零、吉祥物静态
- [x] ESC 关闭抽屉 / lightbox、focus trap、关闭时焦点回触发元素
- [x] 错误 toast `role="alert"` + `aria-live="assertive"`

---

## 6 · 反模式（永远不要做）

1. 不要用 emoji 当装饰。
2. 不要用 `system-ui` / default font stack 当主字体。
3. 不要用现代柔光阴影 `0 8px 24px ...`，一律 `--shadow-stamp`。
4. 不要用 `alert()` / 嵌入式红块，一律走 `<ToastBanner>`。
5. 不要让 60-90s loading 是静态 spinner——必须含阶段进度 + quip + 计时器。
6. 不要在确认前提交昂贵生成——必须先进 CONFIRM 抽屉。
7. 不要给透卡结果图套 explorecipe 的 `<CanvasFrame>`——用薄画框。

---

## 7 · short_id 公开分享系统（C2）

后端 `server.py` 为每张透卡分配 8 字符 URL-safe `short_id`，`logs/cards.jsonl` 维护 `short_id → 归档 PNG` 映射。

| 路由 | 行为 |
|---|---|
| `GET /c/<short_id>` | 302 跳到 `/api/card/<short_id>.png` |
| `GET /api/card/<short_id>.png` | 直出归档 PNG，`Cache-Control: public, max-age=31536000, immutable` |

前端分享 URL = `https://transcard.xmu-cuisine.club/c/<short_id>`。微信 / Telegram / iMessage 粘贴 PNG URL 自动出图片预览，**不做服务端 OG 合成**。

---

## 8 · 引用 & 来源

- 视觉 DNA：`explorecipe/DESIGN.md`、姊妹项目 lilibear-world
- 升级方案：本仓库 `PLAN_DESIGN_UPGRADE.md`
- 决策日期：2026-05-16
