# 技术规范

## 技术栈

| 层级 | 技术 | 版本 | 理由 |
|------|------|------|------|
| 语言 | Python | 3.8.6 | 用户环境已安装 |
| DOCX 读写 | python-docx | 1.1.2+ | 最成熟的 Python DOCX 库 |
| GUI 框架 | customtkinter | 最新 | 基于 tkinter 的现代化封装，无需额外运行时 |
| 默认 GUI | tkinter | 内置 | 文件对话框等基础组件 |
| 打包工具 | PyInstaller | 3.6 | 通过 .spec 文件配置资源与依赖 |

## 模块职责

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  reader.py  │────▶│   matcher.py     │────▶│  writer.py  │
│  (读取)     │     │   (匹配)         │     │  (生成)     │
└─────────────┘     └──────────────────┘     └─────────────┘
       │                    ▲                       │
       │              ┌─────┴──────┐                │
       │              │  GUI 层    │                │
       │              │ main_window│                │
       │              │ mapping_dlg│                │
       │              └────────────┘                │
       ▼                                            ▼
  Input DOCX                                   Output DOCX
  Template DOCX
```

### reader.py — 读取模块
- `read_docx(filepath) -> DocData`
- 提取段落列表：每段包含文本、样式信息
- 提取表格列表：每个表格包含行列结构、单元格文本
- 数据结构定义见下方

### matcher.py — 匹配模块
- `match_paragraphs(input_data, template_data) -> MatchResult`
- `match_tables(input_data, template_data) -> MatchResult`
- 标签提取：从文本中分离字段名（以冒号、中文冒号等为分隔符）
- 相似度计算：使用字符串包含匹配 + 编辑距离
- 顺序匹配兜底

### writer.py — 生成模块
- `generate_output(template_path, match_result, output_path)`
- 以模板文件为骨架
- 按匹配结果替换段落文本和表格单元格文本
- 保留模板所有格式属性

### GUI 层
- `main_window.py`：主窗口、文件选择、转换触发、日志显示
- `mapping_dialog.py`：手动映射弹窗

## 核心数据结构

```python
# 段落信息
ParaInfo = {
    "text": str,           # 段落文本
    "alignment": int,      # 对齐方式 (0=左, 1=中, 2=右)
    "font_name": str,      # 字体名
    "font_size": int,      # 字号 (EMU)
    "bold": bool,
    "italic": bool,
    "line_spacing": float, # 行间距
    "space_before": int,   # 段前间距
    "space_after": int,    # 段后间距
}

# 表格信息
TableInfo = {
    "rows": int,
    "cols": int,
    "cells": [[CellInfo, ...], ...],
    "merged_cells": [(r1,c1,r2,c2), ...],
}

CellInfo = {
    "text": str,
    "row": int,
    "col": int,
}

# 文档数据
DocData = {
    "paragraphs": [ParaInfo, ...],
    "tables": [TableInfo, ...],
}

# 匹配结果
MatchResult = {
    "para_matches": [(input_idx, template_idx, score), ...],
    "table_cell_matches": [(input_cell_ref, template_cell_ref, score), ...],
    "unmatched_input_paras": [int, ...],
    "unmatched_input_cells": [str, ...],
}
```

## 关键算法

### 标签提取算法
1. 取文本首行/首句
2. 寻找分隔符：冒号(`:` `：`)、括号(`（` `(`)、空格
3. 分隔符前的文本为标签
4. 若无分隔符，整句作为标签

### 段落匹配算法
1. 提取模板每个段落的标签列表 `T_labels`
2. 提取输入每个段落的标签列表 `I_labels`
3. 对每个 `I_labels[i]`，在 `T_labels` 中查找最佳匹配：
   - 完全相同 → 得分 1.0
   - 包含关系（较短标签 ≥3 字）→ 得分 0.85
   - 包含关系（较短标签 <3 字）→ 得分 0.5
   - 字符集重叠率 → 得分 = |交集| / |并集|
4. 用贪心算法分配匹配（高分优先，阈值 0.6）
5. 剩余未匹配的按出现顺序兜底匹配
6. 最终无法匹配的输入段落标记为"多余"

### 表格单元格匹配算法

两阶段全局匹配，不执行行列顺序兜底：

1. **精确唯一文本匹配**：统计模板中每个单元格首行文本的出现次数，仅在模板中**唯一出现**的文本参与精确匹配。避免"学历"等多处出现的文本产生歧义。
2. **标签匹配（就近优先）**：对剩余未匹配的单元格，提取标签（`_extract_label`），使用 `_label_similarity` 计算相似度。阈值 0.85，行+列曼哈顿距离作为 tiebreaker。短标签（<3字）的包含匹配降权为 0.5 防止误配。
3. **不执行全局兜底匹配**：未匹配的模板单元格保留模板原文，未匹配的输入单元格暂不处理。此设计避免了不同行列结构间的强制错配。
