# -*- coding: utf-8 -*-
"""Main window — file selection, conversion, and log display"""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from engine.reader import read_docx
from engine.matcher import match_paragraphs, match_tables
from engine.writer import generate_output
from gui.mapping_dialog import MappingDialog


BTN_BLUE = "#1E90FF"


def _safe_font(family="SimHei", size=13, **kwargs):
    try:
        return ctk.CTkFont(family=family, size=size, **kwargs)
    except Exception:
        return ctk.CTkFont(size=size, **kwargs)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DOCX 格式统一工具")
        self.geometry("750x560")
        self.minsize(650, 440)
        self._f_title = _safe_font("SimHei", 20, weight="bold")
        self._f_label = _safe_font("SimHei", 13)
        self._f_log = _safe_font("SimHei", 12)
        self._f_status = _safe_font("SimHei", 11)

        self.input_path = ctk.StringVar()
        self.template_path = ctk.StringVar()
        self.output_path = ctk.StringVar()

        self._input_data = None
        self._tmpl_data = None
        self._cell_config = None  # user manual mapping overrides

        self._build_ui()

    def _build_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(
            main_frame, text="DOCX 格式统一工具",
            font=self._f_title
        )
        title_label.pack(pady=(0, 20))

        file_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        file_frame.pack(fill="x", padx=10)

        self._add_file_row(file_frame, "输入文件:", self.input_path, 0)
        self._add_file_row(file_frame, "模板文件:", self.template_path, 1)
        self._add_file_row(file_frame, "输出位置:", self.output_path, 2)

        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(15, 10))

        self.log_text = ctk.CTkTextbox(log_frame, font=self._f_log, wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.mapping_btn = ctk.CTkButton(
            btn_frame, text="手动调整映射",
            fg_color=BTN_BLUE, border_width=0,
            text_color="white",
            width=130, height=36,
            font=self._f_label,
            command=self._on_mapping
        )
        self.mapping_btn.pack(side="left")

        self.convert_btn = ctk.CTkButton(
            btn_frame, text="开始转换",
            width=120, height=36,
            font=self._f_label,
            state="disabled",
            command=self._on_convert
        )
        self.convert_btn.pack(side="right")

        self.status_var = ctk.StringVar(value="就绪")
        status_bar = ctk.CTkLabel(
            self, textvariable=self.status_var,
            font=ctk.CTkFont(family="SimHei", size=11), anchor="w",
            fg_color=("gray90", "gray17"),
            corner_radius=0, height=24
        )
        status_bar.pack(fill="x", side="bottom")

        self.input_path.trace_add("write", self._on_paths_changed)
        self.template_path.trace_add("write", self._on_paths_changed)

        self._log("欢迎使用 DOCX 格式统一工具")
        self._log('请选择输入文件和模板文件后，点击“开始转换”')

    def _add_file_row(self, parent, label_text, path_var, row):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=5)

        label = ctk.CTkLabel(row_frame, text=label_text, width=80, anchor="e",
                             font=self._f_label)
        label.pack(side="left", padx=(0, 8))

        entry = ctk.CTkEntry(row_frame, textvariable=path_var,
                             font=self._f_label)
        entry.pack(side="left", fill="x", expand=True)

        browse_btn = ctk.CTkButton(
            row_frame, text="浏览", width=60, height=32,
            font=self._f_label,
            command=lambda p=path_var, idx=row: self._on_browse(p, idx)
        )
        browse_btn.pack(side="left", padx=(6, 0))

    def _on_browse(self, path_var, row_idx):
        if row_idx == 2:
            path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("DOCX 文件", "*.docx"), ("所有文件", "*.*")],
                title="选择输出文件保存位置"
            )
        else:
            path = filedialog.askopenfilename(
                filetypes=[("DOCX 文件", "*.docx"), ("所有文件", "*.*")],
                title="选择输入文件" if row_idx == 0 else "选择模板文件"
            )
        if path:
            path_var.set(path)
            if row_idx == 0 and not self.output_path.get():
                dir_name = os.path.dirname(path)
                base = os.path.splitext(os.path.basename(path))[0]
                suggested = os.path.join(dir_name, base + "_格式化.docx")
                self.output_path.set(suggested)

    def _on_paths_changed(self, *args):
        if self.input_path.get() and self.template_path.get():
            self.convert_btn.configure(state="normal")
        else:
            self.convert_btn.configure(state="disabled")
        # Reset manual mapping when files change
        self._cell_config = None
        self._input_data = None
        self._tmpl_data = None

    # ---- Conversion ----
    def _on_convert(self):
        input_path = self.input_path.get()
        tmpl_path = self.template_path.get()
        output_path = self.output_path.get()

        if not os.path.exists(input_path):
            messagebox.showerror("错误", "输入文件不存在:\n" + input_path)
            return
        if not os.path.exists(tmpl_path):
            messagebox.showerror("错误", "模板文件不存在:\n" + tmpl_path)
            return
        if not output_path:
            messagebox.showerror("错误", "请指定输出位置")
            return
        if not input_path.lower().endswith('.docx'):
            messagebox.showerror("错误", "输入文件不是 .docx 格式")
            return
        if not tmpl_path.lower().endswith('.docx'):
            messagebox.showerror("错误", "模板文件不是 .docx 格式")
            return

        # 如果输出文件已存在，先尝试删除（防止被 Word 等程序占用导致保存失败）
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except PermissionError:
                messagebox.showerror("错误",
                    "输出文件被占用，请关闭已打开的输出文件后重试:\n" + output_path)
                return

        self.convert_btn.configure(state="disabled", text="处理中...")
        self._log("=" * 40)

        thread = threading.Thread(
            target=self._run_conversion,
            args=(input_path, tmpl_path, output_path),
            daemon=True
        )
        thread.start()

    def _run_conversion(self, input_path, tmpl_path, output_path):
        try:
            self._update_status("正在读取文件...")
            self._log("1/3 正在读取文件...")
            input_data = read_docx(input_path)
            tmpl_data = read_docx(tmpl_path)

            self._update_status("正在匹配内容...")
            self._log("2/3 正在匹配文字和表格...")
            para_result = match_paragraphs(input_data, tmpl_data)
            cell_result = match_tables(input_data, tmpl_data,
                                       cell_config=self._cell_config)

            n_para = len(para_result["para_matches"])
            n_cell = len(cell_result["cell_matches"])
            n_unmatched = len(para_result["unmatched_input"])
            self._log("  段落匹配: %d 对" % n_para)
            self._log("  表格匹配: %d 对" % n_cell)
            if n_unmatched > 0:
                self._log("  未匹配段落: %d (将保留原样)" % n_unmatched)
            if self._cell_config is not None:
                n_keep = sum(1 for v in self._cell_config.values() if v is None)
                self._log("  手动映射: %d 个单元格保留模板" % n_keep)

            self._update_status("正在生成输出文件...")
            self._log("3/3 正在生成格式化文件...")
            generate_output(
                template_path=tmpl_path,
                input_data=input_data,
                template_data=tmpl_data,
                para_matches=para_result["para_matches"],
                cell_matches=cell_result["cell_matches"],
                unmatched_paras=para_result["unmatched_input"],
                output_path=output_path,
            )

            self._log("转换完成！输出: " + output_path)
            self._update_status("转换完成")

            self.after(0, lambda: self._on_conversion_done(output_path))

        except Exception as e:
            err_msg = str(e)
            self._log("错误: " + err_msg)
            self._update_status("转换失败")
            self.after(0, lambda msg=err_msg: self._on_conversion_error(msg))

    def _on_conversion_done(self, output_path):
        self.convert_btn.configure(state="normal", text="开始转换")
        if messagebox.askyesno("转换完成",
                                "输出文件已保存到:\n" + output_path + "\n\n是否打开文件所在文件夹?"):
            os.startfile(os.path.dirname(output_path))

    def _on_conversion_error(self, error_msg):
        self.convert_btn.configure(state="normal", text="开始转换")
        messagebox.showerror("转换失败", "处理过程中出现错误:\n" + error_msg)

    # ---- Manual Mapping ----
    def _on_mapping(self):
        input_path = self.input_path.get()
        tmpl_path = self.template_path.get()

        if not input_path or not tmpl_path:
            messagebox.showwarning("提示", "请先选择输入文件和模板文件")
            return
        if not os.path.exists(input_path) or not os.path.exists(tmpl_path):
            messagebox.showerror("错误", "文件不存在，请重新选择")
            return

        # Load files if not already cached
        if self._input_data is None:
            self._input_data = read_docx(input_path)
        if self._tmpl_data is None:
            self._tmpl_data = read_docx(tmpl_path)

        # Run auto-match to get suggestions
        auto_result = match_tables(self._input_data, self._tmpl_data)
        auto_matches = auto_result["cell_matches"]

        # Open mapping dialog
        dialog = MappingDialog(self, self._input_data, self._tmpl_data, auto_matches)
        self.wait_window(dialog)

        if dialog.get_result() is not None:
            self._cell_config = dialog.get_result()
            n_mapped = sum(1 for v in self._cell_config.values() if v is not None)
            n_kept = sum(1 for v in self._cell_config.values() if v is None)
            self._log("手动映射已保存: %d 个替换, %d 个保留模板" % (n_mapped, n_kept))

    # ---- Logging ----
    def _log(self, message):
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _update_status(self, text):
        self.after(0, lambda: self.status_var.set(text))
