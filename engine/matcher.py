"""匹配引擎 — 标签匹配 + 顺序匹配"""

import re
from difflib import SequenceMatcher


def match_paragraphs(input_data, template_data):
    input_paras = input_data["paragraphs"]
    tmpl_paras = template_data["paragraphs"]

    input_non_empty = [(i, p) for i, p in enumerate(input_paras) if p["text"].strip()]
    tmpl_non_empty = [(i, p) for i, p in enumerate(tmpl_paras) if p["text"].strip()]

    matched_input = set()
    matched_tmpl = set()
    matches = []

    # Phase 1: label matching
    for ii, ip in input_non_empty:
        in_label = _extract_label(ip["text"])
        if not in_label:
            continue
        best_ti = None
        best_score = 0.0
        for ti, tp in tmpl_non_empty:
            if ti in matched_tmpl:
                continue
            tmpl_label = _extract_label(tp["text"])
            if not tmpl_label:
                continue
            score = _label_similarity(in_label, tmpl_label)
            if score > best_score and score >= 0.6:
                best_score = score
                best_ti = ti
        if best_ti is not None:
            matches.append((ii, best_ti))
            matched_input.add(ii)
            matched_tmpl.add(best_ti)

    # Phase 1.5: detect compound paragraphs — input text that contains
    # labels for multiple unmatched template paragraphs
    _split_compound_paragraphs(input_non_empty, tmpl_non_empty,
                               matched_input, matched_tmpl, matches)

    # Phase 2: positional fallback
    unmatched_in = [(i, p) for i, p in input_non_empty if i not in matched_input]
    unmatched_tmpl = [(i, p) for i, p in tmpl_non_empty if i not in matched_tmpl]

    for idx in range(min(len(unmatched_in), len(unmatched_tmpl))):
        ii = unmatched_in[idx][0]
        ti = unmatched_tmpl[idx][0]
        matches.append((ii, ti))
        matched_input.add(ii)
        matched_tmpl.add(ti)

    unmatched_input_list = [i for i, p in input_non_empty if i not in matched_input]

    return {
        "para_matches": matches,
        "unmatched_input": unmatched_input_list,
    }


def _split_compound_paragraphs(input_non_empty, tmpl_non_empty,
                               matched_input, matched_tmpl, matches):
    """检测已匹配输入段落的文本是否还包含未匹配模板段落的标签。

    如输入"项目名称: XXXX   填表日期: YYYY"匹配到模板"项目名称"后，
    检测到文本中还包含"填表日期"标签，模板中也有未匹配的"填表日期"段落，
    则额外建立匹配。
    """
    unmatched_tmpl_labels = {}
    for ti, tp in tmpl_non_empty:
        if ti not in matched_tmpl:
            lbl = _extract_label(tp["text"])
            if lbl and len(lbl) >= 2:
                unmatched_tmpl_labels[lbl] = ti

    if not unmatched_tmpl_labels:
        return

    # 对每个已匹配的输入段落，扫描其中是否包含未匹配模板标签
    for ii, ip in input_non_empty:
        if ii not in matched_input:
            continue
        text = ip["text"]
        for tmpl_label, ti in unmatched_tmpl_labels.items():
            if ti in matched_tmpl:
                continue
            pos = text.find(tmpl_label)
            if pos < 0:
                continue
            # 验证标签边界：前为空/行首/空白，后为冒号/空白
            if pos > 0 and text[pos - 1] not in (' ', '\t', '\n'):
                continue
            after = pos + len(tmpl_label)
            if after < len(text) and text[after] not in (':', '：', ' ', '\t', '\n'):
                continue
            # 找到复合匹配
            matches.append((ii, ti))
            matched_tmpl.add(ti)


def match_tables(input_data, template_data):
    if not input_data["tables"] or not template_data["tables"]:
        return {"cell_matches": [], "unmatched_input_cells": []}

    in_tbl = input_data["tables"][0]
    tmpl_tbl = template_data["tables"][0]

    in_cells = {}
    for cell in in_tbl["cells"]:
        text = cell["text"].strip()
        if text:
            in_cells[(cell["row"], cell["col"])] = text

    tmpl_cells = {}
    for cell in tmpl_tbl["cells"]:
        text = cell["text"].strip()
        if text:
            tmpl_cells[(cell["row"], cell["col"])] = text

    matched_in = set()
    matched_tmpl = set()
    matches = []

    # Phase 1: global exact match for unique text in template
    _match_unique_exact(in_cells, tmpl_cells, matched_in, matched_tmpl, matches)

    # Phase 2: global label match with proximity preference
    _match_label_global(in_cells, tmpl_cells, matched_in, matched_tmpl, matches)

    # No global positional fallback — unmatched template cells keep original text

    unmatched_input_cells = [
        {"row": r, "col": c} for (r, c) in in_cells if (r, c) not in matched_in
    ]

    return {
        "cell_matches": matches,
        "unmatched_input_cells": unmatched_input_cells,
    }


def _match_unique_exact(in_cells, tmpl_cells, matched_in, matched_tmpl, matches):
    # Count occurrences of each first-line text in template
    tmpl_first_counts = {}
    for (_tr, _tc), text in tmpl_cells.items():
        first = text.split("\n")[0].strip()
        if len(first) >= 2:
            tmpl_first_counts[first] = tmpl_first_counts.get(first, 0) + 1

    # Map unique template texts to their position
    unique_pos = {}
    for (tr, tc), text in tmpl_cells.items():
        first = text.split("\n")[0].strip()
        if len(first) >= 2 and tmpl_first_counts.get(first, 0) == 1:
            unique_pos[first] = (tr, tc)

    # Find matching input cells
    for (ir, ic), in_text in sorted(in_cells.items(), key=lambda k: (k[0][0], k[0][1])):
        if (ir, ic) in matched_in:
            continue
        in_first = in_text.split("\n")[0].strip()
        if len(in_first) < 2 or in_first not in unique_pos:
            continue
        tr, tc = unique_pos[in_first]
        if (tr, tc) not in matched_tmpl:
            matches.append({
                "input_row": ir, "input_col": ic,
                "tmpl_row": tr, "tmpl_col": tc,
            })
            matched_in.add((ir, ic))
            matched_tmpl.add((tr, tc))


def _match_label_global(in_cells, tmpl_cells, matched_in, matched_tmpl, matches):
    for (ir, ic), in_text in sorted(in_cells.items(), key=lambda k: (k[0][0], k[0][1])):
        if (ir, ic) in matched_in:
            continue
        in_label = _extract_label(in_text)
        if not in_label:
            continue

        best_key = None
        best_score = 0.0
        best_dist = float("inf")
        best_text_sim = 0.0
        for (tr, tc), tmpl_text in tmpl_cells.items():
            if (tr, tc) in matched_tmpl:
                continue
            tmpl_label = _extract_label(tmpl_text)
            if not tmpl_label:
                continue
            score = _label_similarity(in_label, tmpl_label)
            if score < 0.85:
                continue
            dist = abs(ir - tr) + abs(ic - tc)
            text_sim = SequenceMatcher(None, in_text, tmpl_text).ratio()
            # 三重排序：标签分 > 全文相似 > 位置近
            # （全文相似优先于位置距离，因为输入和模板的行列结构可能不一致）
            better = False
            if score > best_score:
                better = True
            elif score == best_score:
                if text_sim > best_text_sim:
                    better = True
                elif text_sim == best_text_sim and dist < best_dist:
                    better = True
            if better:
                best_score = score
                best_dist = dist
                best_text_sim = text_sim
                best_key = (tr, tc)

        if best_key is not None:
            matches.append({
                "input_row": ir, "input_col": ic,
                "tmpl_row": best_key[0], "tmpl_col": best_key[1],
            })
            matched_in.add((ir, ic))
            matched_tmpl.add(best_key)


def _extract_label(text):
    text = text.strip()
    if not text:
        return ""
    first_line = text.split("\n")[0].strip()
    match = re.split(r"[:：：\s]+", first_line, maxsplit=1)
    candidate = match[0].strip()
    candidate = candidate.strip("[]()（）")
    if len(candidate) >= 2:
        return candidate
    return first_line[:10]


def _label_similarity(a, b):
    if not a or not b:
        return 0.0
    a = a.strip()
    b = b.strip()
    if a == b:
        return 1.0
    # 包含关系：仅当较短标签 >= 3 个字符时才适用，避免 2 字短词误配
    shorter = a if len(a) <= len(b) else b
    if shorter in (b if shorter == a else a):
        if len(shorter) >= 3:
            return 0.85
        return 0.5
    common = len(set(a) & set(b))
    total = len(set(a) | set(b))
    if total == 0:
        return 0.0
    return common / total
