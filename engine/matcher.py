"""匹配引擎 — 标签匹配 + 顺序匹配"""

import re
from difflib import SequenceMatcher

# 常见标题字段 — 这些文本在模板和输入中都是字段名，应保留模板原文
FIELD_LABELS = {
    "序号", "姓名", "性别", "学历", "职称", "职务",
    "身份证号", "身份证号码", "银行卡号", "银行账号", "开户行",
    "开户行支行", "联系方式", "联系电话", "手机号",
    "事由", "授课名称", "讲座名称", "课时数", "总金额",
    "申报类别", "培训类型", "培训内容", "培训需求学院",
    "专家类型", "专家信息", "专家职称", "专家简介",
    "时段", "时间", "内容", "实施方式", "培训目标",
    "专家课酬", "食宿安排", "辅导对象", "及人数",
    "项目名称", "填表日期", "申报项目", "课程名称", "申报日期",
    "负责人", "经办人", "分管负责人", "审核人", "审批人",
}


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


def match_tables(input_data, template_data, cell_config=None):
    if not input_data["tables"] or not template_data["tables"]:
        return {"table_matches": []}

    table_matches = []
    n_tables = min(len(input_data["tables"]), len(template_data["tables"]))

    for t_idx in range(n_tables):
        in_tbl = input_data["tables"][t_idx]
        tmpl_tbl = template_data["tables"][t_idx]

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

        if cell_config is not None and t_idx == 0:
            result = _match_by_cell_config(in_cells, tmpl_cells, cell_config)
        else:
            matched_in = set()
            matched_tmpl = set()
            matches = []

            _match_by_header(in_cells, tmpl_cells, matched_in, matched_tmpl, matches)
            _match_unique_exact(in_cells, tmpl_cells, matched_in, matched_tmpl, matches)
            _match_label_global(in_cells, tmpl_cells, matched_in, matched_tmpl, matches)

            unmatched = [{"row": r, "col": c} for (r, c) in in_cells if (r, c) not in matched_in]
            result = {"cell_matches": matches, "unmatched_input_cells": unmatched}

        table_matches.append(result)

    return {"table_matches": table_matches}


def _match_by_cell_config(in_cells, tmpl_cells, cell_config):
    """按用户手动配置的 cell_config 生成匹配结果。

    cell_config: {(tmpl_row, tmpl_col): (in_row, in_col) or None}
    None = 保留模板原文，不生成匹配。
    """
    matches = []
    matched_in = set()
    for (tr, tc), src in cell_config.items():
        if src is None:
            continue  # 保留模板
        ir, ic = src
        if (ir, ic) in in_cells and (tr, tc) in tmpl_cells:
            matches.append({
                "input_row": ir, "input_col": ic,
                "tmpl_row": tr, "tmpl_col": tc,
            })
            matched_in.add((ir, ic))
    unmatched = [{"row": r, "col": c} for (r, c) in in_cells if (r, c) not in matched_in]
    return {"cell_matches": matches, "unmatched_input_cells": unmatched}


def _match_by_header(in_cells, tmpl_cells, matched_in, matched_tmpl, matches):
    """Phase 0: 列头引导匹配。

    通过匹配表头行（row 0）的标签建立 input_col → template_col 映射，
    然后将数据行（row >= 1）的单元格按列映射填入，解决数据值不同但语义相同的问题。
    """
    # 提取表头行标签
    in_headers = {}
    for (ir, ic), text in in_cells.items():
        if ir == 0:
            lbl = _extract_label(text)
            if lbl:
                in_headers[ic] = (lbl, text)

    tmpl_headers = {}
    for (tr, tc), text in tmpl_cells.items():
        if tr == 0:
            lbl = _extract_label(text)
            if lbl:
                tmpl_headers[tc] = (lbl, text)

    if not in_headers or not tmpl_headers:
        return

    # 匹配表头列 → 建立列映射
    col_map = {}  # input_col → template_col
    used_tmpl = set()
    for ic, (in_lbl, _) in in_headers.items():
        best_tc = None
        best_score = 0.0
        for tc, (tm_lbl, _) in tmpl_headers.items():
            if tc in used_tmpl:
                continue
            score = _label_similarity(in_lbl, tm_lbl)
            if score > best_score and score >= 0.5:
                best_score = score
                best_tc = tc
        if best_tc is not None:
            col_map[ic] = best_tc
            used_tmpl.add(best_tc)

            # 也匹配表头行本身
            if (0, ic) not in matched_in and (0, best_tc) not in matched_tmpl:
                matches.append({
                    "input_row": 0, "input_col": ic,
                    "tmpl_row": 0, "tmpl_col": best_tc,
                })
                matched_in.add((0, ic))
                matched_tmpl.add((0, best_tc))

    # 质量检查：表头标签必须全部唯一（数据表特征），至少 3 列且 >= 33% 覆盖率
    in_labels_list = [lbl for _, (lbl, _) in in_headers.items()]
    tmpl_labels_list = [lbl for _, (lbl, _) in tmpl_headers.items()]
    if len(set(in_labels_list)) < len(in_labels_list):  # 输入表头有重复
        return
    if len(set(tmpl_labels_list)) < len(tmpl_labels_list):  # 模板表头有重复
        return
    total_cols = max(len(in_headers), len(tmpl_headers))
    if len(col_map) < 3 or len(col_map) / total_cols < 0.33:
        return

    # 按列映射匹配数据行（仅匹配内容简单、非标签行的数据行）
    max_in_row = max(k[0] for k in in_cells) if in_cells else 0
    max_tmpl_row = max(k[0] for k in tmpl_cells) if tmpl_cells else 0

    # 数据行候选：跳过全行相同文本的行（如签名行、合计行）
    data_rows = []
    for row in range(1, min(max_in_row, max_tmpl_row) + 1):
        # 检查该行是否所有列文本都相同（合并行特征）
        row_in_texts = [v for (r, c), v in in_cells.items() if r == row and v.strip()]
        row_tm_texts = [v for (r, c), v in tmpl_cells.items() if r == row and v.strip()]
        in_all_same = len(set(row_in_texts)) <= 1
        tm_all_same = len(set(row_tm_texts)) <= 1
        # 跳过签名行和全行相同的标签行
        if in_all_same and tm_all_same and len(row_in_texts) > 0 and len(row_tm_texts) > 0:
            first_in = row_in_texts[0].strip() if row_in_texts else ""
            first_tm = row_tm_texts[0].strip() if row_tm_texts else ""
            if _same_colon_labels(first_in, first_tm):
                continue
            if first_in == first_tm and len(first_in) <= 5:
                continue  # 相同短文本（如"合计"），保留模板
        data_rows.append(row)

    # 收集表头标签用于字段检测
    in_lbls = {lbl for _, (lbl, _) in in_headers.items()}
    tm_lbls = {lbl for _, (lbl, _) in tmpl_headers.items()}

    for row in data_rows:
        for ic, tc in col_map.items():
            in_key = (row, ic)
            tmpl_key = (row, tc)
            if in_key in in_cells and tmpl_key in tmpl_cells:
                if in_key not in matched_in and tmpl_key not in matched_tmpl:
                    in_val = in_cells[in_key].strip()
                    tm_val = tmpl_cells[tmpl_key].strip()
                    if in_val != tm_val:
                        matches.append({
                            "input_row": row, "input_col": ic,
                            "tmpl_row": row, "tmpl_col": tc,
                        })
                        matched_in.add(in_key)
                        matched_tmpl.add(tmpl_key)


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
            # 跳过同结构的冒号标签行（如签名行），保留模板原文
            if _same_colon_labels(in_text, tmpl_text):
                continue
            # 阻止不同类型的纯数字串交叉匹配（身份证 vs 银行卡）
            if _digit_type(in_text) != _digit_type(tmpl_text):
                continue
            dist = abs(ir - tr) + abs(ic - tc)
            text_sim = SequenceMatcher(
                None, _normalize_text(in_text), _normalize_text(tmpl_text)
            ).ratio()
            # 时间感知加分：如果两段文本含有同一时段（上午/下午），+0.15
            text_sim += _time_period_boost(in_text, tmpl_text)
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


def _time_period_boost(text_a, text_b):
    """如果两段文本属于同一时段（上午/下午），返回 +0.15 加分。

    提取文本中的第一个时间 (HH:MM)，判断小时是否同时 < 12 或同时 >= 12。
    用于区分 '4.11 09:00-12:00'（上午）与 '4.11 13:00-17:00'（下午）。
    """
    time_pat = re.compile(r'(\d{1,2})[：:](\d{2})')
    def extract_hour(text):
        match = time_pat.search(_normalize_text(text))
        if match:
            return int(match.group(1))
        return None

    hour_a = extract_hour(text_a)
    hour_b = extract_hour(text_b)
    if hour_a is not None and hour_b is not None:
        if (hour_a < 12) == (hour_b < 12):
            return 0.15
    return 0.0


def _normalize_text(text):
    """标准化文本，将全角字符转为半角，提高 SequenceMatcher 比对精度。

    例如 '8：00' (全角冒号) → '8:00' (半角)，使 '09:00-12:00'
    能更准确地区分 '8:00' (上午) vs '13:00' (下午)。
    """
    result = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:  # 全角空格 → 半角空格
            result.append(' ')
        elif 0xFF01 <= code <= 0xFF5E:  # 全角标点/字母/数字（含全角数字 0xFF10-0xFF19）
            result.append(chr(code - 0xFEE0))
        else:
            result.append(ch)
    return ''.join(result)


def _extract_label(text):
    text = text.strip()
    if not text:
        return ""
    first_line = text.split("\n")[0].strip()
    # 先按冒号分隔（标签：值格式）
    match = re.split(r"[:：]", first_line, maxsplit=1)
    candidate = match[0].strip()
    # 去掉括号及其内容（左右括号配对或仅有左括号时均处理）
    candidate = re.sub(r"[（(][^)）]*(?:[)）])?", "", candidate).strip()
    candidate = candidate.strip("[]()（）")
    # 去掉标签内的空白（如"姓 名" → "姓名"）
    candidate = re.sub(r"\s+", "", candidate)
    if len(candidate) >= 2:
        return candidate
    return first_line[:10]


def _is_field_label(text, row, in_headers=None, tmpl_headers=None):
    """判断该单元格是否为字段标签（应保留模板原文）。

    条件：文本在常见字段列表中，或出现在表头行，或输入和模板内容相同。
    """
    if not text or not text.strip():
        return False
    clean = text.strip().replace("\n", "").replace(" ", "")
    # 1. 在已知字段列表中
    if clean in FIELD_LABELS:
        return True
    # 2. 文本出现在表头行
    if in_headers:
        for lbl in in_headers:
            if clean and lbl and clean in lbl:
                return True
    if tmpl_headers:
        for lbl in tmpl_headers:
            if clean and lbl and clean in lbl:
                return True
    return False


def _same_colon_labels(text_a, text_b):
    """检查两段文本是否含有同一组冒号前缀标签。

    用于识别签名行等结构化文本：如果两段文本中「：」前的关键词集合相同，
    说明是同一类格式文本，应保留模板的原文（保持模板的排版）。
    例："负责人：  经办人：  ..." → 标签集 {负责人, 经办人, ...}
    """
    import re
    def extract_labels(text):
        labels = set()
        for m in re.finditer(r'([一-鿿\w]+)[：:]', text):
            labels.add(m.group(1))
        return labels

    labels_a = extract_labels(text_a)
    labels_b = extract_labels(text_b)
    if not labels_a or not labels_b:
        return False
    # 如果两段文本共享至少 2 个标签且重叠率 >= 60%，视为同类文本
    common = labels_a & labels_b
    if len(common) >= 2:
        overlap = len(common) / max(len(labels_a), len(labels_b))
        return overlap >= 0.6
    return False


def _digit_type(text):
    """识别纯数字串类型：'id'=身份证, 'card'=银行卡, 'unknown'=其他。

    身份证特征：18 位 + 第 7-14 位为合法日期 (YYYYMMDD)。
    银行卡特征：16-19 位纯数字但不符合身份证日期特征。
    """
    if not text:
        return 'unknown'
    clean = re.sub(r'\D', '', text)
    if len(clean) == 18:
        try:
            bdate = clean[6:14]
            y, m, d = int(bdate[:4]), int(bdate[4:6]), int(bdate[6:8])
            if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                return 'id'
        except (ValueError, IndexError):
            pass
        return 'card'
    if 16 <= len(clean) <= 19:
        return 'card'
    return 'unknown'


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
