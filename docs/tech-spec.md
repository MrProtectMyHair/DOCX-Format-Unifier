# 技术规范

## 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 语言 | Python | 3.8.6 |
| DOCX 读写 | python-docx | 1.1.2 |
| GUI 框架 | customtkinter | 5.2.2 |
| 打包工具 | PyInstaller | 3.6 |

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
- 提取段落列表：每段包含文本、字体名、字号
- 提取表格列表：每个表格包含行列结构、单元格文本、行列坐标
- 按遍历顺序为单元格分配顺序 ID，正确处理合并单元格

### matcher.py — 匹配模块

**段落匹配** (`match_paragraphs`)：
- Phase 1：标签匹配（阈值 0.6），使用 `_label_similarity`
- Phase 1.5：复合段落检测（一个输入段落含多个模板标签）
- Phase 2：位置回退匹配（剩余未匹配段落按顺序配对）

**表格匹配** (`match_tables`)：
- 返回 `table_matches` 结构，每对 table 独立匹配
- Phase 0：列头引导匹配（数据表特征检测，≥3 列且覆盖率 ≥33%）
- Phase 1：全局精确唯一文本匹配
- Phase 2：全局标签匹配 + 就近优先 + 全文相似 tiebreaker
- 不执行全局兜底 → 未匹配模板单元格保留原文

**关键辅助函数**：
- `_extract_label(text)`：提取标签（冒号分割 + 去括号 + 去空格）
- `_label_similarity(a, b)`：精确=1.0，包含≥3字=0.85，包含<3字=0.5，字符重叠率
- `_normalize_text(text)`：全角→半角
- `_digit_type(text)`：身份证(18位+日期) vs 银行卡(16-19位)
- `_same_colon_labels(a, b)`：识别同结构签名行
- `_time_period_boost(a, b)`：同时段文本 +0.15

### writer.py — 生成模块

**生成流程** (`generate_output`)：
1. 复制模板到临时文件（输出目录，uuid 文件名）
2. 段落替换（`_replace_paragraphs`）
3. 表格单元格替换（`_replace_table_cells`，遍历所有表）
4. 空值填充（`_fill_empty_cells_by_label`，遍历所有表）
5. 保存到临时文件，移动到输出路径

**段落处理**：
- `_fill_form_paragraph(para, input_text)`：检测 blank run（纯下划线或带下划线空格），用固定文本锚点定位输入值，保留 run 格式
- `_strip_label_if_template_has_none(input, template)`：去空格+去下划线核心标签比对，避免误剥离
- 未匹配段落追加到末尾，label 匹配的未匹配段落可合并回 form

**表格处理**：
- `_replace_table_cells(table, in_tbl, tmpl_tbl, matches)`：顺序 ID 映射替换
- `_fill_empty_cells_by_label(table, in_tbl, tmpl_tbl, matches)`：标签领地填充 + 列头引导填充
- `_is_summary_label(text)`：合计/总计/小计 仅填紧邻一格
- `_has_skip_keyword(text)`：签字/盖章/审批等 8 个行政标签跳过
- `_copy_label_format(row, label_col, target_col)`：复制字体格式到填入单元格

## 核心数据结构

```python
DocData = {
    "paragraphs": [{"text": str, "font_name": str, "font_size": int}, ...],
    "tables": [{"rows": int, "cols": int, "cells": [{"text": str, "row": int, "col": int}, ...]}, ...],
}

# match_tables 返回值
TableMatches = {
    "table_matches": [
        {"cell_matches": [{"input_row": int, "input_col": int, "tmpl_row": int, "tmpl_col": int}, ...],
         "unmatched_input_cells": [{"row": int, "col": int}, ...]},
        ...
    ],
}

# match_paragraphs 返回值
ParaMatches = {
    "para_matches": [(input_idx, template_idx), ...],
    "unmatched_input": [int, ...],
}
```

## 关键常量

- `FIELD_LABELS`：47 个常见中文字段标签
- `_SKIP_LABELS`：8 个签章/行政关键词（签字、盖章、审批、审核、日期、负责人、经办人、分管）
- GUI 配色：Professional Blue（主色 #2563EB，悬停 #1D4ED8）
- 字体：Microsoft YaHei + SimHei fallback
