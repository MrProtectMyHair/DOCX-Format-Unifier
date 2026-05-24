"""匹配引擎 — 标签匹配 + 顺序匹配"""

import re


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
            if score > best_score or (score == best_score and dist < best_dist):
                best_score = score
                best_dist = dist
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
