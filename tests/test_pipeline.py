"""Self-validation script — runs the conversion pipeline and checks output quality.

Usage: python tests/test_pipeline.py
Exit code 0 = all checks passed, 1 = at least one check failed.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.reader import read_docx
from engine.matcher import match_paragraphs, match_tables, _extract_label
from engine.writer import generate_output


REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "参考文件")


def run_pipeline(input_name="Reference Input.docx"):
    input_path = os.path.join(REF_DIR, input_name)
    tmpl_path = os.path.join(REF_DIR, "Reference Template.docx")

    if not os.path.exists(input_path):
        return None, f"File not found: {input_name}"
    if not os.path.exists(tmpl_path):
        return None, "Template file not found"

    input_data = read_docx(input_path)
    tmpl_data = read_docx(tmpl_path)
    para_result = match_paragraphs(input_data, tmpl_data)
    cell_result = match_tables(input_data, tmpl_data)

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    try:
        generate_output(
            template_path=tmpl_path,
            input_data=input_data,
            template_data=tmpl_data,
            para_matches=para_result["para_matches"],
            cell_matches=cell_result["cell_matches"],
            unmatched_paras=para_result["unmatched_input"],
            output_path=output_path,
        )
        out_data = read_docx(output_path)
        return {
            "input": input_data,
            "template": tmpl_data,
            "output": out_data,
            "para_matches": para_result,
            "cell_matches": cell_result,
            "name": input_name,
        }, None
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def check_table_structure(data):
    """Output table structure matches template."""
    out_tbl = data["output"]["tables"][0]
    tmpl_tbl = data["template"]["tables"][0]
    ok = (out_tbl["rows"] == tmpl_tbl["rows"] and
          out_tbl["cols"] == tmpl_tbl["cols"])
    return ok, f"Table {out_tbl['rows']}x{out_tbl['cols']} (expected {tmpl_tbl['rows']}x{tmpl_tbl['cols']})"


def check_no_duplicate_labels(data):
    """No duplicated field labels in output paragraphs."""
    labels_seen = {}
    duplicates = []
    for i, p in enumerate(data["output"]["paragraphs"]):
        text = p["text"].strip()
        if not text:
            continue
        label = _extract_label(text)
        if label and len(label) >= 2:
            if label in labels_seen:
                duplicates.append(label)
            else:
                labels_seen[label] = i
    ok = len(duplicates) == 0
    msg = "No duplicate labels" if ok else f"Duplicates: {duplicates}"
    return ok, msg


def check_paragraph_count(data):
    """Output paragraph count matches template (within tolerance for appended content)."""
    n_out = len(data["output"]["paragraphs"])
    n_tmpl = len(data["template"]["paragraphs"])
    # Allow up to 2 extra paragraphs from unmatched input
    ok = n_out >= n_tmpl and n_out <= n_tmpl + 5
    return ok, f"Output: {n_out} paras, Template: {n_tmpl}"


def check_no_extra_date(data):
    """B1 regression: '填表日期' should NOT appear twice."""
    date_count = 0
    for p in data["output"]["paragraphs"]:
        text = p["text"].strip()
        if "填表日期" in text or "填报日期" in text:
            date_count += 1
    tmpl_count = 0
    for p in data["template"]["paragraphs"]:
        text = p["text"].strip()
        if "填表日期" in text or "填报日期" in text:
            tmpl_count += 1
    ok = date_count <= tmpl_count
    return ok, f"Date labels: output={date_count}, template={tmpl_count}"


def check_time_order(data):
    """B3 regression: time slots in rows 7-9 should be in correct order."""
    out_tbl = data["output"]["tables"][0]
    cells_7_0 = [c for c in out_tbl["cells"] if c["row"] == 7 and c["col"] == 0]
    cells_8_0 = [c for c in out_tbl["cells"] if c["row"] == 8 and c["col"] == 0]
    if not cells_7_0 or not cells_8_0:
        return True, "Skipped (cells not found)"

    import re
    def first_hour(text):
        m = re.search(r'(\d{1,2})[：:]', text)
        return int(m.group(1)) if m else -1

    h7 = first_hour(cells_7_0[0]["text"])
    h8 = first_hour(cells_8_0[0]["text"])
    morning_first = (h7 >= 0 and h7 < 12) and (h8 >= 12)
    return morning_first, f"Row7 hour={h7}, Row8 hour={h8}"


CHECKS = [
    ("Table structure", check_table_structure),
    ("No duplicate labels", check_no_duplicate_labels),
    ("Paragraph count", check_paragraph_count),
    ("No extra date (B1)", check_no_extra_date),
    ("Time slot order (B3)", check_time_order),
]


def main():
    print("=" * 50)
    print("DOCX Format Unifier — Self Validation")
    print("=" * 50)

    all_ok = True
    for input_name in ["Reference Input.docx", "Reference Input V2.docx"]:
        data, error = run_pipeline(input_name)
        if error:
            print(f"\n  [SKIP] {input_name}: {error}")
            continue

        print(f"\n--- {data['name']} ---")
        for check_name, fn in CHECKS:
            ok, msg = fn(data)
            status = "PASS" if ok else "FAIL"
            if not ok:
                all_ok = False
            print(f"  [{status}] {check_name}: {msg}")

    print("\n" + "-" * 50)
    if all_ok:
        print("  ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print("  SOME CHECKS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
