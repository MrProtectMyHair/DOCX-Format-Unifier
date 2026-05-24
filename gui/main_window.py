# -*- coding: utf-8 -*-
"""Main window — file selection, conversion, and log display"""

import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from engine.reader import read_docx
from engine.matcher import match_paragraphs, match_tables
from engine.writer import generate_output


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DOCX Format Unifier")
        self.geometry("700x520")
        self.minsize(600, 400)

        self.input_path = ctk.StringVar()
        self.template_path = ctk.StringVar()
        self.output_path = ctk.StringVar()

        self._build_ui()

    def _build_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))

        title_label = ctk.CTkLabel(
            main_frame, text="DOCX Format Unifier",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(0, 20))

        file_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        file_frame.pack(fill="x", padx=10)

        self._add_file_row(file_frame, "Input File:", self.input_path, 0)
        self._add_file_row(file_frame, "Template File:", self.template_path, 1)
        self._add_file_row(file_frame, "Output Path:", self.output_path, 2)

        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(15, 10))

        self.log_text = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(size=11))
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.mapping_btn = ctk.CTkButton(
            btn_frame, text="Manual Mapping",
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray80"),
            width=130, height=36,
            command=self._on_mapping
        )
        self.mapping_btn.pack(side="left")

        self.convert_btn = ctk.CTkButton(
            btn_frame, text="Start Convert",
            width=120, height=36,
            state="disabled",
            command=self._on_convert
        )
        self.convert_btn.pack(side="right")

        self.status_var = ctk.StringVar(value="Ready")
        status_bar = ctk.CTkLabel(
            self, textvariable=self.status_var,
            font=ctk.CTkFont(size=10), anchor="w",
            fg_color=("gray90", "gray17"),
            corner_radius=0, height=22
        )
        status_bar.pack(fill="x", side="bottom")

        self.input_path.trace_add("write", self._on_paths_changed)
        self.template_path.trace_add("write", self._on_paths_changed)

        self._log("Welcome to DOCX Format Unifier")
        self._log("Please select input file and template file, then click Start Convert")

    def _add_file_row(self, parent, label_text, path_var, row):
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", pady=4)

        label = ctk.CTkLabel(row_frame, text=label_text, width=80, anchor="e")
        label.pack(side="left", padx=(0, 8))

        entry = ctk.CTkEntry(row_frame, textvariable=path_var)
        entry.pack(side="left", fill="x", expand=True)

        browse_btn = ctk.CTkButton(
            row_frame, text="Browse", width=55, height=30,
            command=lambda p=path_var, idx=row: self._on_browse(p, idx)
        )
        browse_btn.pack(side="left", padx=(6, 0))

    def _on_browse(self, path_var, row_idx):
        if row_idx == 2:
            path = filedialog.asksaveasfilename(
                defaultextension=".docx",
                filetypes=[("DOCX files", "*.docx"), ("All files", "*.*")],
                title="Save output as"
            )
        else:
            path = filedialog.askopenfilename(
                filetypes=[("DOCX files", "*.docx"), ("All files", "*.*")],
                title="Select input file" if row_idx == 0 else "Select template file"
            )
        if path:
            path_var.set(path)
            if row_idx == 0 and not self.output_path.get():
                dir_name = os.path.dirname(path)
                base = os.path.splitext(os.path.basename(path))[0]
                suggested = os.path.join(dir_name, f"{base}_formatted.docx")
                self.output_path.set(suggested)

    def _on_paths_changed(self, *args):
        if self.input_path.get() and self.template_path.get():
            self.convert_btn.configure(state="normal")
        else:
            self.convert_btn.configure(state="disabled")

    def _on_convert(self):
        input_path = self.input_path.get()
        tmpl_path = self.template_path.get()
        output_path = self.output_path.get()

        if not os.path.exists(input_path):
            messagebox.showerror("Error", f"Input file not found:\n{input_path}")
            return
        if not os.path.exists(tmpl_path):
            messagebox.showerror("Error", f"Template file not found:\n{tmpl_path}")
            return
        if not output_path:
            messagebox.showerror("Error", "Please specify output path")
            return

        self.convert_btn.configure(state="disabled", text="Processing...")
        self._log("=" * 40)

        thread = threading.Thread(
            target=self._run_conversion,
            args=(input_path, tmpl_path, output_path),
            daemon=True
        )
        thread.start()

    def _run_conversion(self, input_path, tmpl_path, output_path):
        try:
            self._update_status("Reading files...")
            self._log("1/3 Reading files...")
            input_data = read_docx(input_path)
            tmpl_data = read_docx(tmpl_path)

            self._update_status("Matching content...")
            self._log("2/3 Matching text and tables...")
            para_result = match_paragraphs(input_data, tmpl_data)
            cell_result = match_tables(input_data, tmpl_data)

            n_para = len(para_result["para_matches"])
            n_cell = len(cell_result["cell_matches"])
            n_unmatched = len(para_result["unmatched_input"])
            self._log(f"  Paragraph matches: {n_para}")
            self._log(f"  Table cell matches: {n_cell}")
            if n_unmatched > 0:
                self._log(f"  Unmatched paragraphs: {n_unmatched} (appended as-is)")

            self._update_status("Generating output...")
            self._log("3/3 Generating formatted file...")
            generate_output(
                template_path=tmpl_path,
                input_data=input_data,
                template_data=tmpl_data,
                para_matches=para_result["para_matches"],
                cell_matches=cell_result["cell_matches"],
                unmatched_paras=para_result["unmatched_input"],
                output_path=output_path,
            )

            self._log(f"Done! Output: {output_path}")
            self._update_status("Complete")

            self.after(0, lambda: self._on_conversion_done(output_path))

        except Exception as e:
            self._log(f"Error: {e}")
            self._update_status("Failed")
            self.after(0, lambda: self._on_conversion_error(str(e)))

    def _on_conversion_done(self, output_path):
        self.convert_btn.configure(state="normal", text="Start Convert")
        if messagebox.askyesno("Complete", f"Output saved to:\n{output_path}\n\nOpen folder?"):
            os.startfile(os.path.dirname(output_path))

    def _on_conversion_error(self, error_msg):
        self.convert_btn.configure(state="normal", text="Start Convert")
        messagebox.showerror("Error", f"Conversion failed:\n{error_msg}")

    def _on_mapping(self):
        self._log("Manual mapping will be available in a future update")

    def _log(self, message):
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _update_status(self, text):
        self.after(0, lambda: self.status_var.set(text))
