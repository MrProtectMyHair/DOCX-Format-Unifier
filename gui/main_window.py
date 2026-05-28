# -*- coding: utf-8 -*-
# DOCX Format Unifier - Main Window

import os, threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from engine.reader import read_docx
from engine.matcher import match_paragraphs, match_tables
from engine.writer import generate_output
from gui.mapping_dialog import MappingDialog

C_PRIMARY   = "#2563EB"
C_PRIMARY_H = "#1D4ED8"
C_BG_CARD   = ("#F8FAFC", "#1E293B")
C_BORDER    = ("#E2E8F0", "#334155")
C_TEXT_SUB  = ("#64748B", "#94A3B8")


def _safe_font(family="Microsoft YaHei", size=13, **kwargs):
    try: return ctk.CTkFont(family=family, size=size, **kwargs)
    except Exception: return ctk.CTkFont(size=size, **kwargs)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DOCX 格式统一工具")
        self.geometry("760x580")
        self.minsize(660, 460)
        self.configure(fg_color=("gray95", "gray10"))
        f_title  = _safe_font("Microsoft YaHei", 22, weight="bold")
        self._f_label = _safe_font("Microsoft YaHei", 13)
        f_log    = _safe_font("Microsoft YaHei", 12)
        f_status = _safe_font("Microsoft YaHei", 10)
        self.input_path    = ctk.StringVar()
        self.template_path = ctk.StringVar()
        self.output_path   = ctk.StringVar()
        self._input_data = self._tmpl_data = self._cell_config = None
        self._build_ui(f_title, f_log, f_status)

    def _build_ui(self, f_title, f_log, f_status):
        ctk.CTkLabel(self, text="DOCX  格式统一工具",
                     font=f_title, text_color=C_PRIMARY).pack(pady=(24, 4))
        ctk.CTkLabel(self, text="输入文件  ·  模板文件  ·  输出文件",
                     font=f_status, text_color=C_TEXT_SUB).pack(pady=(0, 16))

        card = ctk.CTkFrame(self, fg_color=C_BG_CARD, corner_radius=10,
                            border_width=1, border_color=C_BORDER)
        card.pack(fill="x", padx=20, pady=(0, 12))
        self._add_file_row(card, "输入文件",   self.input_path,    0)
        self._add_file_row(card, "模板文件",   self.template_path, 1)
        self._add_file_row(card, "输出位置",   self.output_path,   2)

        log_card = ctk.CTkFrame(self, fg_color=C_BG_CARD, corner_radius=10,
                                border_width=1, border_color=C_BORDER)
        log_card.pack(fill="both", expand=True, padx=20, pady=(0, 12))
        self.log_text = ctk.CTkTextbox(log_card, font=f_log, wrap="word",
                                        fg_color="transparent", border_width=0)
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=(0, 10))
        self.mapping_btn = ctk.CTkButton(
            btn_bar, text="手动调整映射", fg_color="transparent",
            border_width=1.5, border_color=C_PRIMARY, text_color=C_PRIMARY,
            corner_radius=8, width=140, height=38, font=self._f_label,
            hover_color=(C_PRIMARY, C_PRIMARY_H), command=self._on_mapping)
        self.mapping_btn.pack(side="left")
        self.convert_btn = ctk.CTkButton(
            btn_bar, text="开始转换", fg_color=C_PRIMARY,
            hover_color=C_PRIMARY_H, text_color="white", corner_radius=8,
            width=140, height=38, font=self._f_label,
            state="disabled", command=self._on_convert)
        self.convert_btn.pack(side="right")

        self.status_var = ctk.StringVar(value="就绪")
        ctk.CTkLabel(self, textvariable=self.status_var, font=f_status,
                     anchor="w", fg_color=("gray90", "gray15"),
                     corner_radius=0, height=22, padx=12
                     ).pack(fill="x", side="bottom")

        self.input_path.trace_add("write", self._on_paths_changed)
        self.template_path.trace_add("write", self._on_paths_changed)
        self._log("欢迎使用 DOCX 格式统一工具")

    def _add_file_row(self, parent, label, path_var, row):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=(10 if row == 0 else 6, 10 if row == 2 else 6))
        ctk.CTkLabel(f, text=label, width=90, anchor="w",
                     font=self._f_label, text_color=C_TEXT_SUB).pack(side="left", padx=(0, 8))
        ctk.CTkEntry(f, textvariable=path_var, font=self._f_label,
                     corner_radius=6, height=34, border_width=1
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f, text="浏览", width=60, height=34, font=self._f_label,
                      corner_radius=6, fg_color=C_PRIMARY, hover_color=C_PRIMARY_H,
                      command=lambda p=path_var, i=row: self._on_browse(p, i)
                      ).pack(side="left", padx=(8, 0))

    def _on_browse(self, path_var, row_idx):
        if row_idx == 2:
            path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("DOCX files", "*.docx"), ("All files", "*.*")],
                title="Save output as")
        else:
            path = filedialog.askopenfilename(
                filetypes=[("DOCX files", "*.docx"), ("All files", "*.*")],
                title="Select input" if row_idx == 0 else "Select template")
        if path:
            path_var.set(path)
            if row_idx == 0 and not self.output_path.get():
                d = os.path.dirname(path)
                b = os.path.splitext(os.path.basename(path))[0]
                self.output_path.set(os.path.join(d, b + "_formatted.docx"))

    def _on_paths_changed(self, *args):
        ok = bool(self.input_path.get() and self.template_path.get())
        self.convert_btn.configure(state="normal" if ok else "disabled")
        self._cell_config = self._input_data = self._tmpl_data = None

    def _on_convert(self):
        ip = self.input_path.get(); tp = self.template_path.get()
        op = self.output_path.get()
        if not os.path.exists(ip): return messagebox.showerror("错误", "输入文件不存在:\n" + ip)
        if not os.path.exists(tp): return messagebox.showerror("错误", "模板文件不存在:\n" + tp)
        if not op: return messagebox.showerror("错误", "请指定输出位置")
        if not ip.lower().endswith('.docx'): return messagebox.showerror("错误", "输入文件必须是 .docx 格式")
        if not tp.lower().endswith('.docx'): return messagebox.showerror("错误", "模板文件必须是 .docx 格式")
        if os.path.exists(op):
            try: os.remove(op)
            except PermissionError:
                return messagebox.showerror("错误", "输出文件被占用，请关闭后重试:\n" + op)
        self.convert_btn.configure(state="disabled", text="处理中...")
        self._log("-" * 36)
        threading.Thread(target=self._run_conversion, args=(ip, tp, op), daemon=True).start()

    def _run_conversion(self, ip, tp, op):
        try:
            self._update_status("正在读取...")
            self._log("[1/3] 正在读取文件...")
            id_ = read_docx(ip); td_ = read_docx(tp)
            self._update_status("正在匹配...")
            self._log("[2/3] 正在匹配文字和表格...")
            pr = match_paragraphs(id_, td_)
            cr = match_tables(id_, td_, cell_config=self._cell_config)
            self._log("  段落匹配: %d 对  |  表格匹配: %d 对" % (len(pr["para_matches"]), len(cr["cell_matches"])))
            if pr["unmatched_input"]:
                self._log("  未匹配: %d (保留原样)" % len(pr["unmatched_input"]))
            self._update_status("正在生成...")
            self._log("[3/3] 正在生成格式化文件...")
            generate_output(template_path=tp, input_data=id_, template_data=td_,
                            para_matches=pr["para_matches"], cell_matches=cr["cell_matches"],
                            unmatched_paras=pr["unmatched_input"], output_path=op)
            self._log("完成 -> " + op)
            self._update_status("转换完成")
            self.after(0, lambda: self._on_done(op))
        except Exception as e:
            m = str(e); self._log("错误: " + m); self._update_status("转换失败")
            self.after(0, lambda msg=m: self._on_error(msg))

    def _on_done(self, op):
        self.convert_btn.configure(state="normal", text="开始转换")
        if messagebox.askyesno("转换完成", "已保存到:\n" + op + "\n\n打开文件夹?"):
            os.startfile(os.path.dirname(op))

    def _on_error(self, msg):
        self.convert_btn.configure(state="normal", text="开始转换")
        messagebox.showerror("转换失败", msg)

    def _on_mapping(self):
        ip = self.input_path.get(); tp = self.template_path.get()
        if not ip or not tp: return messagebox.showwarning("提示", "请先选择输入文件和模板文件")
        if not os.path.exists(ip) or not os.path.exists(tp):
            return messagebox.showerror("错误", "文件不存在")
        if self._input_data is None: self._input_data = read_docx(ip)
        if self._tmpl_data is None:  self._tmpl_data  = read_docx(tp)
        cr = match_tables(self._input_data, self._tmpl_data)
        dlg = MappingDialog(self, self._input_data, self._tmpl_data, cr["cell_matches"])
        self.wait_window(dlg)
        if dlg.get_result() is not None:
            self._cell_config = dlg.get_result()
            n = sum(1 for v in self._cell_config.values() if v is not None)
            k = sum(1 for v in self._cell_config.values() if v is None)
            self._log("手动映射: %d 个替换, %d 个保留模板" % (n, k))

    def _log(self, msg):
        self.after(0, lambda: self._append(msg))

    def _append(self, msg):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def _update_status(self, text):
        self.after(0, lambda: self.status_var.set(text))
