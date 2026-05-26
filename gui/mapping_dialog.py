# -*- coding: utf-8 -*-
"""Manual mapping dialog — collapsible row groups with dropdown selectors."""

import customtkinter as ctk
from tkinter import StringVar


class MappingDialog(ctk.CTkToplevel):
    def __init__(self, parent, input_data, template_data, auto_matches):
        super().__init__(parent)
        self.title("字段映射配置")
        self.geometry("700x550")
        self.minsize(550, 400)
        self.transient(parent)
        self.grab_set()

        self.input_data = input_data
        self.template_data = template_data
        self.auto_matches = auto_matches
        self.result = None  # cell_config or None (cancelled)

        # Build lookup maps
        self._build_maps()

        # State
        self._show_only_mapped = ctk.BooleanVar(value=False)
        self._row_vars = {}  # row_idx -> StringVar for fold/unfold label

        self._build_ui()
        self._populate()

    # ---- data prep ----
    def _build_maps(self):
        # Input cell text lookup: (r, c) -> text
        in_tbl = self.input_data["tables"][0]
        self.in_cell_text = {}
        for cell in in_tbl["cells"]:
            self.in_cell_text[(cell["row"], cell["col"])] = cell["text"]

        # Template cell text lookup: (r, c) -> text
        tmpl_tbl = self.template_data["tables"][0]
        self.tmpl_cell_text = {}
        for cell in tmpl_tbl["cells"]:
            self.tmpl_cell_text[(cell["row"], cell["col"])] = cell["text"]

        # Existing auto-match lookup: tmpl (r,c) -> input (r,c)
        self._auto_map = {}
        for m in self.auto_matches:
            tk = (m["tmpl_row"], m["tmpl_col"])
            ik = (m["input_row"], m["input_col"])
            self._auto_map[tk] = ik

        # Current working map (starts as copy of auto)
        self._current_map = dict(self._auto_map)

        # Rows that have template cells
        self._tmpl_rows = sorted(set(r for (r, c) in self.tmpl_cell_text))

        # Input cell options list for dropdowns
        self._input_options = sorted(self.in_cell_text.keys())
        # Option strings: index 0 = "(保留模板)", then each input cell
        self._option_strings = ["(保留模板)"] + [
            "[I:%d,%d] %s" % (r, c, self.in_cell_text[(r, c)][:20].replace("\n", " "))
            for (r, c) in self._input_options
        ]
        # Each dropdown holds an index into _option_strings
        self._dropdown_vars = {}  # (tr, tc) -> StringVar

    # ---- UI build ----
    def _build_ui(self):
        # Title
        header = ctk.CTkLabel(self, text="已自动匹配，可下拉调整每个单元格的输入来源",
                              font=ctk.CTkFont(size=12))
        header.pack(pady=(12, 6))

        # Scrollable area
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # Row group frames stored here
        self._row_frames = {}   # row_idx -> outer frame
        self._row_inner = {}    # row_idx -> inner (collapsible) frame
        self._cell_widgets = {}  # (tr, tc) -> (label, dropdown)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkButton(btn_frame, text="自动匹配", width=100, height=30,
                      fg_color="transparent", border_width=1,
                      command=self._reset_auto).pack(side="left", padx=4)

        self._filter_btn = ctk.CTkButton(btn_frame, text="只看已映射", width=100, height=30,
                                          fg_color="transparent", border_width=1,
                                          command=self._toggle_filter)
        self._filter_btn.pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="全部展开", width=100, height=30,
                      fg_color="transparent", border_width=1,
                      command=lambda: self._expand_all(True)).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="全部折叠", width=100, height=30,
                      fg_color="transparent", border_width=1,
                      command=lambda: self._expand_all(False)).pack(side="left", padx=4)

        ctk.CTkButton(btn_frame, text="确认", width=90, height=30,
                      command=self._on_confirm).pack(side="right", padx=4)
        ctk.CTkButton(btn_frame, text="取消", width=90, height=30,
                      fg_color="transparent", border_width=1,
                      command=self._on_cancel).pack(side="right", padx=4)

    # ---- populate rows ----
    def _populate(self):
        for row_idx in self._tmpl_rows:
            self._add_row_group(row_idx)

    def _add_row_group(self, row_idx):
        # Row type label
        row_cells = [(r, c) for (r, c) in self.tmpl_cell_text if r == row_idx]
        # Simple row-type guess
        if row_idx == 0:
            row_label = "第 %d 行（表头）" % row_idx
        elif row_idx == max(self._tmpl_rows):
            row_label = "第 %d 行（签名）" % row_idx
        elif self._is_summary_row(row_idx):
            row_label = "第 %d 行（汇总）" % row_idx
        else:
            row_label = "第 %d 行（数据）" % row_idx

        # Outer frame
        outer = ctk.CTkFrame(self._scroll, fg_color="transparent")
        outer.pack(fill="x", pady=2)
        self._row_frames[row_idx] = outer

        # Header bar (click to fold)
        header_bar = ctk.CTkFrame(outer, fg_color=("gray90", "gray20"), corner_radius=6)
        header_bar.pack(fill="x")
        fold_var = StringVar(value="▼ " + row_label)
        self._row_vars[row_idx] = fold_var
        header_btn = ctk.CTkButton(header_bar, textvariable=fold_var, anchor="w",
                                    fg_color="transparent", text_color=("gray20", "gray90"),
                                    font=ctk.CTkFont(size=12, weight="bold"),
                                    command=lambda r=row_idx: self._toggle_row(r))
        header_btn.pack(fill="x", padx=4, pady=2)

        # Inner frame (collapsible)
        inner = ctk.CTkFrame(outer, fg_color="transparent")
        inner.pack(fill="x", padx=(16, 0))
        self._row_inner[row_idx] = inner

        # Cell rows
        for (tr, tc) in sorted(row_cells, key=lambda x: x[1]):
            self._add_cell_row(inner, tr, tc)

    def _add_cell_row(self, parent, tr, tc):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=1)

        # Template cell label
        tmpl_text = self.tmpl_cell_text.get((tr, tc), "")
        tmpl_short = tmpl_text[:25].replace("\n", " ")
        tmpl_lbl = ctk.CTkLabel(row_frame, text=tmpl_short, width=220, anchor="w",
                                font=ctk.CTkFont(size=11))
        tmpl_lbl.pack(side="left", padx=(0, 6))

        # Arrow
        arrow = ctk.CTkLabel(row_frame, text="→", width=20,
                             font=ctk.CTkFont(size=11))
        arrow.pack(side="left")

        # Dropdown
        var = StringVar()
        self._dropdown_vars[(tr, tc)] = var
        current_src = self._current_map.get((tr, tc))
        if current_src is None:
            var.set("(保留模板)")
        else:
            idx = self._input_options.index(current_src) + 1  # +1 for "(保留模板)" at index 0
            var.set(self._option_strings[idx])

        dd = ctk.CTkOptionMenu(row_frame, variable=var, values=self._option_strings,
                               width=280, font=ctk.CTkFont(size=11),
                               command=lambda v, r=tr, c=tc: self._on_dropdown(r, c, v))
        dd.pack(side="left")

        self._cell_widgets[(tr, tc)] = (row_frame, tmpl_lbl, dd)

    def _is_summary_row(self, row_idx):
        """Guess whether a row is a summary/aggregate row."""
        texts = [self.tmpl_cell_text[(r, c)] for (r, c) in self.tmpl_cell_text if r == row_idx]
        if not texts:
            return False
        unique = len(set(t.strip() for t in texts))
        return unique <= 2 and any("合计" in t or "人民币" in t for t in texts)

    # ---- actions ----
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
            # Parse "[I:r,c] text" -> (r, c)
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
                outer.pack(fill="x", pady=2, before=self._scroll._parent)

    def _reset_auto(self):
        self._current_map = dict(self._auto_map)
        for (tr, tc), var in self._dropdown_vars.items():
            src = self._current_map.get((tr, tc))
            if src is None:
                var.set("(保留模板)")
            else:
                idx = self._input_options.index(src) + 1
                var.set(self._option_strings[idx])

    # ---- result ----
    def _on_confirm(self):
        # Build cell_config: {(tr, tc): (ir, ic) or None}
        self.result = {}
        for (tr, tc), src in self._current_map.items():
            self.result[(tr, tc)] = src
        # Also include template cells NOT in current_map as None (keep template)
        for (tr, tc) in self.tmpl_cell_text:
            if (tr, tc) not in self.result:
                self.result[(tr, tc)] = None
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()

    def get_result(self):
        """Return cell_config dict or None if cancelled."""
        return self.result
