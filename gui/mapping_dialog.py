# -*- coding: utf-8 -*-
"""Manual mapping dialog — collapsible row groups with dropdown selectors."""

import customtkinter as ctk
from tkinter import StringVar

BTN_BLUE = "#1E90FF"


def _safe_font(family="SimHei", size=13, **kwargs):
    try:
        return ctk.CTkFont(family=family, size=size, **kwargs)
    except Exception:
        return ctk.CTkFont(size=size, **kwargs)


class MappingDialog(ctk.CTkToplevel):
    def __init__(self, parent, input_data, template_data, auto_matches):
        super().__init__(parent)
        self.title("字段映射配置")
        self.font = _safe_font("SimHei", 13)
        self.font_bold = _safe_font("SimHei", 13, weight="bold")
        self.font_small = _safe_font("SimHei", 12)
        self.geometry("750x580")
        self.minsize(600, 400)
        self.transient(parent)
        self.grab_set()

        self.input_data = input_data
        self.template_data = template_data
        self.auto_matches = auto_matches
        self.result = None

        self._build_maps()
        self._show_only_mapped = ctk.BooleanVar(value=False)
        self._row_vars = {}
        self._build_ui()
        self._populate()

    def _build_maps(self):
        in_tbl = self.input_data["tables"][0]
        self.in_cell_text = {}
        for cell in in_tbl["cells"]:
            self.in_cell_text[(cell["row"], cell["col"])] = cell["text"]

        tmpl_tbl = self.template_data["tables"][0]
        self.tmpl_cell_text = {}
        for cell in tmpl_tbl["cells"]:
            self.tmpl_cell_text[(cell["row"], cell["col"])] = cell["text"]

        self._auto_map = {}
        for m in self.auto_matches:
            tk = (m["tmpl_row"], m["tmpl_col"])
            ik = (m["input_row"], m["input_col"])
            self._auto_map[tk] = ik

        self._current_map = dict(self._auto_map)
        self._tmpl_rows = sorted(set(r for (r, c) in self.tmpl_cell_text))
        self._all_input_keys = sorted(self.in_cell_text.keys())
        self._dropdown_vars = {}

    def _get_nearby_options(self, tr, tc):
        """返回精简下拉选项：自动匹配项 + 同行附近输入单元格 + 保留模板。"""
        options = ["(保留模板)"]
        seen_keys = set()
        matched_key = self._auto_map.get((tr, tc))

        # 1. 自动匹配项放在最前面
        if matched_key is not None:
            ir, ic = matched_key
            text = self.in_cell_text.get((ir, ic), "")[:20].replace("\n", " ")
            options.append("[I:%d,%d] %s" % (ir, ic, text))
            seen_keys.add((ir, ic))

        # 2. 同行 ±1 行的输入单元格
        nearby = [(ir, ic) for (ir, ic) in self._all_input_keys
                  if abs(ir - tr) <= 1 and (ir, ic) not in seen_keys]
        for ir, ic in nearby[:8]:
            text = self.in_cell_text.get((ir, ic), "")[:20].replace("\n", " ")
            options.append("[I:%d,%d] %s" % (ir, ic, text))

        return options

    def _build_ui(self):
        header = ctk.CTkLabel(self, text="已自动匹配，可下拉调整每个单元格的输入来源",
                              font=self.font_small)
        header.pack(pady=(12, 6))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        self._row_frames = {}
        self._row_inner = {}
        self._cell_widgets = {}

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(btn_frame, text="自动匹配", width=100, height=32,
                      fg_color=BTN_BLUE, font=self.font_small,
                      command=self._reset_auto).pack(side="left", padx=4)

        self._filter_btn = ctk.CTkButton(btn_frame, text="只看已映射", width=100, height=32,
                                          fg_color=BTN_BLUE, font=self.font_small,
                                          command=self._toggle_filter)
        self._filter_btn.pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="全部展开", width=100, height=32,
                      fg_color=BTN_BLUE, font=self.font_small,
                      command=lambda: self._expand_all(True)).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="全部折叠", width=100, height=32,
                      fg_color=BTN_BLUE, font=self.font_small,
                      command=lambda: self._expand_all(False)).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="确认", width=90, height=32,
                      fg_color=BTN_BLUE, font=self.font_small,
                      command=self._on_confirm).pack(side="right", padx=4)
        ctk.CTkButton(btn_frame, text="取消", width=90, height=32,
                      fg_color=BTN_BLUE, font=self.font_small,
                      command=self._on_cancel).pack(side="right", padx=4)

    def _populate(self):
        for row_idx in self._tmpl_rows:
            self._add_row_group(row_idx)

    def _add_row_group(self, row_idx):
        row_cells = [(r, c) for (r, c) in self.tmpl_cell_text if r == row_idx]
        if row_idx == 0:
            row_label = "第 %d 行（表头）" % row_idx
        elif row_idx == max(self._tmpl_rows):
            row_label = "第 %d 行（签名）" % row_idx
        elif self._is_summary_row(row_idx):
            row_label = "第 %d 行（汇总）" % row_idx
        else:
            row_label = "第 %d 行（数据）" % row_idx

        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", pady=2)
        self._row_frames[row_idx] = outer

        # Header bar
        header_bar = ctk.CTkFrame(outer, fg_color=("gray90", "gray20"), corner_radius=6)
        header_bar.pack(fill="x")
        fold_var = StringVar(value="▼ " + row_label)
        self._row_vars[row_idx] = fold_var
        header_btn = ctk.CTkButton(header_bar, textvariable=fold_var, anchor="w",
                                    fg_color="transparent",
                                    text_color=("gray20", "gray90"),
                                    font=self.font_bold,
                                    command=lambda r=row_idx: self._toggle_row(r))
        header_btn.pack(fill="x", padx=4, pady=2)

        # Inner frame
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=(16, 0))
        self._row_inner[row_idx] = inner

        # Column headers
        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x", pady=(4, 2))
        ctk.CTkLabel(hdr, text="模板字段", width=220, anchor="w",
                     font=self.font_bold).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(hdr, text="→", width=20, font=self.font_bold).pack(side="left")
        ctk.CTkLabel(hdr, text="输入来源", width=280, anchor="w",
                     font=self.font_bold).pack(side="left")

        for (tr, tc) in sorted(row_cells, key=lambda x: x[1]):
            self._add_cell_row(inner, tr, tc)

    def _add_cell_row(self, parent, tr, tc):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=1)

        tmpl_text = self.tmpl_cell_text.get((tr, tc), "")
        tmpl_short = tmpl_text[:25].replace("\n", " ")
        tmpl_lbl = ctk.CTkLabel(row_frame, text=tmpl_short, width=220, anchor="w",
                                font=self.font_small)
        tmpl_lbl.pack(side="left", padx=(0, 6))

        arrow = ctk.CTkLabel(row_frame, text="→", width=20, font=self.font_small)
        arrow.pack(side="left")

        var = StringVar()
        self._dropdown_vars[(tr, tc)] = var
        options = self._get_nearby_options(tr, tc)
        current_src = self._current_map.get((tr, tc))
        if current_src is not None:
            opt_text = "[I:%d,%d] %s" % (current_src[0], current_src[1],
                         self.in_cell_text.get(current_src, "")[:20].replace("\n", " "))
            if opt_text in options:
                var.set(opt_text)
            elif options:
                var.set(options[1] if len(options) > 1 else options[0])
            else:
                var.set("(保留模板)")
        else:
            var.set(options[0])

        dd = ctk.CTkOptionMenu(row_frame, variable=var, values=options,
                               width=300, font=self.font_small,
                               command=lambda v, r=tr, c=tc: self._on_dropdown(r, c, v))
        dd.pack(side="left")

        self._cell_widgets[(tr, tc)] = (row_frame, tmpl_lbl, dd)

    def _is_summary_row(self, row_idx):
        texts = [self.tmpl_cell_text[(r, c)] for (r, c) in self.tmpl_cell_text if r == row_idx]
        if not texts:
            return False
        unique = len(set(t.strip() for t in texts))
        return unique <= 2 and any("合计" in t or "人民币" in t for t in texts)

    def _toggle_row(self, row_idx):
        inner = self._row_inner[row_idx]
        if inner.winfo_ismapped():
            inner.pack_forget()
            self._row_vars[row_idx].set(self._row_vars[row_idx].get().replace("▼", "▶"))
        else:
            inner.pack(fill="x", padx=(16, 0))
            self._row_vars[row_idx].set(self._row_vars[row_idx].get().replace("▶", "▼"))

    def _expand_all(self, expand):
        for row_idx in self._tmpl_rows:
            inner = self._row_inner[row_idx]
            if expand and not inner.winfo_ismapped():
                inner.pack(fill="x", padx=(16, 0))
                self._row_vars[row_idx].set(self._row_vars[row_idx].get().replace("▶", "▼"))
            elif not expand and inner.winfo_ismapped():
                inner.pack_forget()
                self._row_vars[row_idx].set(self._row_vars[row_idx].get().replace("▼", "▶"))

    def _on_dropdown(self, tr, tc, value):
        if value == "(保留模板)":
            self._current_map[(tr, tc)] = None
        else:
            import re
            m = re.match(r'\[I:(\d+),(\d+)\]', value)
            if m:
                ir, ic = int(m.group(1)), int(m.group(2))
                self._current_map[(tr, tc)] = (ir, ic)

    def _toggle_filter(self):
        self._show_only_mapped.set(not self._show_only_mapped.get())
        if self._show_only_mapped.get():
            self._filter_btn.configure(text="显示全部")
        else:
            self._filter_btn.configure(text="只看已映射")
        self._apply_filter()

    def _apply_filter(self):
        show_only = self._show_only_mapped.get()
        for row_idx in self._tmpl_rows:
            has_mapped = any(
                self._current_map.get((r, c)) is not None
                for (r, c) in self.tmpl_cell_text if r == row_idx
            )
            outer = self._row_frames[row_idx]
            if show_only and not has_mapped:
                outer.pack_forget()
            else:
                outer.pack(fill="x", pady=2)

    def _reset_auto(self):
        self._current_map = dict(self._auto_map)
        for (tr, tc), var in self._dropdown_vars.items():
            options = self._get_nearby_options(tr, tc)
            src = self._current_map.get((tr, tc))
            if src is None:
                var.set(options[0])
            else:
                opt_text = "[I:%d,%d] %s" % (src[0], src[1],
                             self.in_cell_text.get(src, "")[:20].replace("\n", " "))
                if opt_text in options:
                    var.set(opt_text)
                else:
                    var.set(options[1] if len(options) > 1 else options[0])

    def _on_confirm(self):
        self.result = {}
        for (tr, tc), src in self._current_map.items():
            self.result[(tr, tc)] = src
        for (tr, tc) in self.tmpl_cell_text:
            if (tr, tc) not in self.result:
                self.result[(tr, tc)] = None
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    def get_result(self):
        return self.result
