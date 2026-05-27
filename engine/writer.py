"""DOCX 生成模块 — 以模板为骨架，替换文字内容"""

import shutil
from docx import Document


def generate_output(template_path, input_data, template_data, para_matches, cell_matches, unmatched_paras, output_path):
    """生成输出文件。

    策略：复制模板文件，将输入文件的文字内容填入模板对应位置。
    """
    # 1. 复制模板文件
    try:
        shutil.copy2(template_path, output_path)
    except (IOError, PermissionError) as e:
        raise IOError("无法写入输出文件，请检查文件是否被其他程序占用或路径是否有写入权限") from e

    # 2. 打开副本进行修改
    doc = Document(output_path)

    # 3. 替换段落文本
    _replace_paragraphs(doc, input_data, template_data, para_matches, unmatched_paras)

    # 4. 替换表格单元格文本
    _replace_table_cells(doc, input_data, template_data, cell_matches)

    # 5. 保存
    try:
        doc.save(output_path)
    except (IOError, PermissionError) as e:
        raise IOError("无法保存输出文件，请关闭已打开的输出文件后重试") from e


def _replace_paragraphs(doc, input_data, template_data, para_matches, unmatched_paras):
    """替换模板段落中的文本为输入文件的文本。

    当一个输入段落匹配到多个模板段落时（复合段落），按标签位置分割文本。
    """
    input_paras = input_data["paragraphs"]
    tmpl_paras = template_data["paragraphs"]
    from engine.matcher import _extract_label

    # 建立: 模板索引 → 输入索引
    tmpl_to_input = {ti: ii for ii, ti in para_matches}

    # 检测复合段落：同一个输入索引对应多个模板段落
    input_to_tmpls = {}
    for ii, ti in para_matches:
        if ii not in input_to_tmpls:
            input_to_tmpls[ii] = []
        input_to_tmpls[ii].append(ti)

    # 计算切分映射: (input_idx, template_idx) -> text_subset
    _split_map = {}
    for ii, ti_list in input_to_tmpls.items():
        if len(ti_list) <= 1:
            continue
        text = input_paras[ii]["text"]
        label_positions = []
        for ti2 in ti_list:
            lbl = _extract_label(tmpl_paras[ti2]["text"])
            if lbl:
                pos = text.find(lbl)
                if pos >= 0:
                    label_positions.append((pos, lbl, ti2))
        label_positions.sort()
        for idx, (pos, lbl, ti2) in enumerate(label_positions):
            start = pos
            if idx + 1 < len(label_positions):
                end = label_positions[idx + 1][0]
            else:
                end = len(text)
            _split_map[(ii, ti2)] = text[start:end].strip()

    for ti, para in enumerate(doc.paragraphs):
        if ti in tmpl_to_input:
            ii = tmpl_to_input[ti]
            if (ii, ti) in _split_map:
                new_text = _split_map[(ii, ti)]
            else:
                new_text = input_paras[ii]["text"]
            # 如果输入段落含「标签：值」格式但模板段落只有值（无标签），剥离标签
            new_text = _strip_label_if_template_has_none(
                new_text, tmpl_paras[ti]["text"])
            _set_paragraph_text(para, new_text)

    # 追加未匹配的输入段落
    unmatched_indices = [i for i in unmatched_paras if input_paras[i]["text"].strip()]
    for ii in unmatched_indices:
        new_text = input_paras[ii]["text"]
        last_para = doc.paragraphs[-1] if doc.paragraphs else None
        new_para = doc.add_paragraph(new_text)
        in_para = input_paras[ii]
        if in_para["font_name"]:
            for run in new_para.runs:
                run.font.name = in_para["font_name"]
        if in_para["font_size"]:
            for run in new_para.runs:
                run.font.size = in_para["font_size"]


def _replace_table_cells(doc, input_data, template_data, cell_matches):
    """替换模板表格单元格中的文本为输入文件的文本。

    策略：为模板表格的每个单元格分配顺序 ID（与 reader 遍历顺序一致），
    通过 ID 建立映射，在输出文档中以相同顺序遍历并替换。
    此方法不依赖行列索引，天然处理合并单元格。
    """
    if not doc.tables or not cell_matches:
        return

    table = doc.tables[0]
    in_tbl = input_data["tables"][0]
    tmpl_tbl = template_data["tables"][0]

    # 建立输入单元格的文本查找: (row, col) → text
    in_cell_map = {}
    for cell in in_tbl["cells"]:
        in_cell_map[(cell["row"], cell["col"])] = cell["text"]

    # 给模板每个单元格分配顺序 ID（与 reader 遍历顺序相同）
    tmpl_pos_to_id = {}
    tmpl_id = 0
    for cell in tmpl_tbl["cells"]:
        key = (cell["row"], cell["col"])
        if key not in tmpl_pos_to_id:
            tmpl_pos_to_id[key] = tmpl_id
            tmpl_id += 1

    # 建立: 模板顺序 ID → 替换文本
    id_mapping = {}
    for m in cell_matches:
        in_key = (m["input_row"], m["input_col"])
        tmpl_key = (m["tmpl_row"], m["tmpl_col"])
        if in_key in in_cell_map and tmpl_key in tmpl_pos_to_id:
            cell_id = tmpl_pos_to_id[tmpl_key]
            id_mapping[cell_id] = in_cell_map[in_key]

    # 按相同遍历顺序在输出文档中替换
    out_id = 0
    for row in table.rows:
        for cell in row.cells:
            if out_id in id_mapping:
                _set_cell_text(cell, id_mapping[out_id])
            out_id += 1


def _set_paragraph_text(para, text):
    """设置段落的文本，保留模板的字符格式。"""
    # 保留第一个 run 的格式，用其承载全部文本
    if para.runs:
        # 将所有文本合并到第一个 run，清空其余 run
        first_run = para.runs[0]
        first_run.text = text
        for run in para.runs[1:]:
            run.text = ""
    else:
        # 没有 run 时添加一个
        run = para.add_run(text)


def _set_cell_text(cell, text):
    """设置单元格的文本，保留模板的字符格式。

    按换行符拆分为多段，匹配模板的段落结构。
    多余的空段落从 XML 中物理移除，避免空行占高。
    """
    # 按换行拆分，过滤空字符串（连续换行不产生空段落）
    raw_parts = text.split("\n") if text else [""]
    parts = [p for p in raw_parts if p.strip()]
    if not parts:
        parts = [""]
    n_paras = len(cell.paragraphs)

    # 填充前 N 个段落（N = min(len(parts), n_paras)）
    for i, part in enumerate(parts):
        if i < n_paras:
            _set_paragraph_text(cell.paragraphs[i], part)
        else:
            # 输入文本的段数超过模板段落数，在末尾段落追加
            _set_paragraph_text(cell.paragraphs[-1],
                               cell.paragraphs[-1].text + "\n" + part)

    # 移除多余的空段落（物理删除，而非仅置空）
    for i in range(len(parts), n_paras):
        para = cell.paragraphs[i]
        p_elem = para._element
        p_elem.getparent().remove(p_elem)


def _strip_label_if_template_has_none(input_text, template_text):
    """如果输入含「标签：值」但模板不含该标签，则剥离输入的标签部分。

    例：输入 "填表及制发日期: 2026.4.1"，模板 "2026.4.1"
    → 返回 "2026.4.1"
    """
    from engine.matcher import _extract_label
    in_label = _extract_label(input_text)

    if not in_label or len(in_label) < 2:
        return input_text
    # 检查模板是否包含输入的标签（作为独立词出现）
    if in_label not in template_text:
        import re
        m = re.search(r'[:：]\s*(.+)', input_text)
        if m:
            return m.group(1).strip()
    return input_text
