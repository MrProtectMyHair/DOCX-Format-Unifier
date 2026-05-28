---
name: customtkinter-ui-optimizer
description: CustomTkinter桌面应用UI优化。当用户要求改善、美化、优化桌面应用的界面外观、配色方案、字体、按钮样式、布局间距，或提到界面看起来不够现代化时使用。适用于所有使用customtkinter框架的Python桌面应用。
---

# CustomTkinter UI 优化

将 Frontend Design 的设计原则翻译为 customtkinter 可用的代码模式。适用于任何 customtkinter 桌面应用。

## 设计工作流

### 1. 先定视觉方向

在改代码前，和用户确认方向：

| 方向 | 特征 | 适合 |
|------|------|------|
| 专业蓝 | 深蓝主色+白底+灰辅色 | 企业工具、办公软件 |
| 暗黑优雅 | 深灰底+金/白点缀 | 技术工具、夜间偏好 |
| 清爽极简 | 白底+单色点缀+大留白 | 简单工具、表单应用 |

不要混合风格。选一种并干净落地。

### 2. 构建视觉系统

#### 颜色

customtkinter 用 hex 字符串定义颜色。建立层次：

```python
# 主色（按钮、强调元素）
PRIMARY = "#1E90FF"       # 蓝色，可用 "#2563EB" (更沉) 或 "#3B82F6" (更亮)

# 功能色
SUCCESS = "#10B981"       # 绿色，成功状态
WARNING = "#F59E0B"       # 橙色，警告
DANGER  = "#EF4444"       # 红色，错误/危险

# 表面色
SURFACE_LIGHT = "#F8FAFC"  # 浅色模式下卡片/面板底色
SURFACE_DARK  = "#1E293B"  # 深色模式下卡片/面板底色
```

避免：紫色渐变+白底（AI陈词滥调）。

#### 字体

Windows 中文字体选择：

| 用途 | 推荐 | 回退 |
|------|------|------|
| 标题(18-20pt) | SimHei bold | Microsoft YaHei bold |
| 正文(13pt) | SimHei / Microsoft YaHei | 系统默认 |
| 日志/小字(11-12pt) | Microsoft YaHei | 系统默认 |

```python
def _safe_font(family="Microsoft YaHei", size=13, **kwargs):
    try:
        return ctk.CTkFont(family=family, size=size, **kwargs)
    except Exception:
        return ctk.CTkFont(size=size, **kwargs)
```

#### 间距节奏

使用 4px 倍数系统：

```python
PAD_XS  = 4    # 紧凑
PAD_SM  = 8    # 标签间距
PAD_MD  = 12   # 组件内边距
PAD_LG  = 16   # 区域间距
PAD_XL  = 24   # 大区域间隔
PAD_XXL = 32   # 页面边距
```

#### 圆角

```python
RADIUS_SM  = 4   # 输入框
RADIUS_MD  = 8   # 按钮/卡片
RADIUS_LG  = 12  # 大面板
```

### 3. Widget 样式规范

#### 按钮

```python
# 主按钮：实心主色
ctk.CTkButton(
    fg_color=PRIMARY, hover_color="#1D4ED8",
    text_color="white", corner_radius=RADIUS_MD,
    font=font_body, height=36, border_width=0
)

# 次按钮：透明底+边框
ctk.CTkButton(
    fg_color="transparent", border_width=1,
    text_color=("gray30", "gray80"),
    corner_radius=RADIUS_MD, font=font_body, height=36
)
```

#### 输入框

```python
ctk.CTkEntry(
    corner_radius=RADIUS_SM, height=34,
    font=font_body, border_width=1
)
```

#### 日志/文本区域

```python
ctk.CTkTextbox(
    corner_radius=RADIUS_SM, border_width=1,
    font=font_small, wrap="word",
    fg_color=("gray95", "gray12")  # 略深于背景
)
```

#### 状态栏

```python
ctk.CTkLabel(
    height=24, corner_radius=0, anchor="w",
    font=font_status,
    fg_color=("gray90", "gray17")
)
```

### 4. 配色方案预设

#### 专业蓝（默认推荐）

```python
PRIMARY = "#2563EB"
HOVER   = "#1D4ED8"
SURFACE = "#F8FAFC"
TEXT    = "#1E293B"
SUBTLE  = "#94A3B8"
BORDER  = "#E2E8F0"
```

#### 暗黑优雅

```python
PRIMARY = "#F59E0B"       # 金/琥珀色点缀
HOVER   = "#D97706"
BG      = "#0F172A"       # 深色背景
SURFACE = "#1E293B"
TEXT    = "#F1F5F9"
BORDER  = "#334155"
```

启用方式：
```python
ctk.set_appearance_mode("dark")
```

#### 清爽极简

```python
PRIMARY = "#10B981"       # 绿色点缀
HOVER   = "#059669"
SURFACE = "#FFFFFF"
TEXT    = "#374151"
BORDER  = "#E5E7EB"
```

### 5. 窗口尺寸

```python
# 默认尺寸 (宽x高)
DEFAULT_SIZE = "750x560"

# 最小尺寸
MINSIZE = (650, 440)

# 响应式原则：
# - 窗口高度 = 页眉高度 + 组件区 + 日志区 + 按钮区 + 状态栏
# - 日志区应 fill="both", expand=True 以利用剩余空间
```

### 6. 快速检查清单

优化 customtkinter UI 时逐项检查：

- [ ] 是否定义了 PRIMARY / HOVER 主色并统一使用？
- [ ] 按钮是否有 hover_color（比 fg_color 略深）？
- [ ] 所有文字是否使用 _safe_font() 创建（含 fallback）？
- [ ] 间距是否使用统一的 4px 倍数？
- [ ] 圆角是否统一（按钮/卡片/输入框）？
- [ ] 日志区是否设置了 wrap="word"？
- [ ] 状态栏/日志等辅助文字是否用小字号+灰色调？
- [ ] 是否避免了紫色渐变+白底？

### 参考文件

- 项目设计规范: `docs/design-spec.md`
- 当前 GUI 实现: `gui/main_window.py`, `gui/mapping_dialog.py`
