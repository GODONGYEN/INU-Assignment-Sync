import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import webbrowser

try:
    import customtkinter as ctk

    GUI_MODE = "customtkinter"
except ModuleNotFoundError:
    ctk = None
    GUI_MODE = "tkinter"

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from src.config import DATABASE_PATH, ENV_EXAMPLE_PATH, ENV_PATH, LOG_FILE_PATH, PROJECT_ROOT, README_PATH
from src.env_utils import parse_env_file, update_env_file
from src.logging_utils import setup_file_logging


DEFAULT_SETTINGS = {
    "BASE_URL": "https://cyber.inu.ac.kr",
    "CALENDAR_NAME": "INU 과제",
    "CALENDAR_MONTHS_BACK": "2",
    "CALENDAR_MONTHS_FORWARD": "6",
    "INCLUDE_PAST_ASSIGNMENTS": "false",
    "REMINDER_MINUTES": "1440,180",
    "DRY_RUN": "true",
}


class SyncAppGUI:
    """GUI로 .env를 편집하고 CLI 동기화를 실행하는 창입니다."""

    def __init__(self) -> None:
        self.logger = setup_file_logging(LOG_FILE_PATH)
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.process: subprocess.Popen | None = None
        self.summary_lines: list[str] = []

        self._ensure_env_exists()
        self.settings = self._load_settings()

        if GUI_MODE == "customtkinter" and ctk is not None:
            ctk.set_appearance_mode("system")
            ctk.set_default_color_theme("blue")
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("INU Assignment Sync")
        self.root.geometry("980x760")

        self.base_url_var = tk.StringVar(value=self.settings["BASE_URL"])
        self.calendar_name_var = tk.StringVar(value=self.settings["CALENDAR_NAME"])
        self.months_back_var = tk.StringVar(value=self.settings["CALENDAR_MONTHS_BACK"])
        self.months_forward_var = tk.StringVar(value=self.settings["CALENDAR_MONTHS_FORWARD"])
        self.include_past_var = tk.BooleanVar(value=self.settings["INCLUDE_PAST_ASSIGNMENTS"].lower() == "true")
        self.dry_run_var = tk.BooleanVar(value=self.settings["DRY_RUN"].lower() == "true")
        self.reminder_minutes_var = tk.StringVar(value=self.settings["REMINDER_MINUTES"])
        self.status_var = tk.StringVar(value="준비 완료")
        self.summary_var = tk.StringVar(value="결과 요약이 여기에 표시됩니다.")

        self._build_ui()
        self.root.after(200, self._poll_output_queue)

    def _ensure_env_exists(self) -> None:
        """`.env`가 없으면 `.env.example`을 복사해 기본 설정을 만듭니다."""
        if ENV_PATH.exists():
            return

        if ENV_EXAMPLE_PATH.exists():
            shutil.copy2(ENV_EXAMPLE_PATH, ENV_PATH)
            self.logger.info(".env 파일이 없어 .env.example에서 새로 만들었습니다.")
            return

        update_env_file(ENV_PATH, DEFAULT_SETTINGS)
        self.logger.info(".env.example이 없어 기본값으로 .env 파일을 만들었습니다.")

    def _load_settings(self) -> dict[str, str]:
        """현재 .env 설정을 읽고 기본값과 합칩니다."""
        settings = DEFAULT_SETTINGS.copy()
        settings.update(parse_env_file(ENV_PATH))
        return settings

    def _make_frame(self, parent, **kwargs):
        if GUI_MODE == "customtkinter" and ctk is not None:
            return ctk.CTkFrame(parent, **kwargs)
        return ttk.Frame(parent, padding=kwargs.get("padding", 8))

    def _make_label(self, parent, text: str = "", textvariable=None, **kwargs):
        if GUI_MODE == "customtkinter" and ctk is not None:
            return ctk.CTkLabel(parent, text=text, textvariable=textvariable, **kwargs)
        return ttk.Label(parent, text=text, textvariable=textvariable)

    def _make_entry(self, parent, textvariable=None, readonly: bool = False, **kwargs):
        if GUI_MODE == "customtkinter" and ctk is not None:
            entry = ctk.CTkEntry(parent, textvariable=textvariable, **kwargs)
            if readonly:
                entry.configure(state="disabled")
            return entry
        entry = ttk.Entry(parent, textvariable=textvariable)
        if readonly:
            entry.state(["readonly"])
        return entry

    def _make_button(self, parent, text: str, command, **kwargs):
        if GUI_MODE == "customtkinter" and ctk is not None:
            return ctk.CTkButton(parent, text=text, command=command, **kwargs)
        return ttk.Button(parent, text=text, command=command)

    def _make_checkbox(self, parent, text: str, variable, **kwargs):
        if GUI_MODE == "customtkinter" and ctk is not None:
            return ctk.CTkCheckBox(parent, text=text, variable=variable, onvalue=True, offvalue=False, **kwargs)
        return ttk.Checkbutton(parent, text=text, variable=variable)

    def _make_log_widget(self, parent):
        if GUI_MODE == "customtkinter" and ctk is not None:
            return ctk.CTkTextbox(parent, wrap="word")
        return scrolledtext.ScrolledText(parent, wrap="word")

    def _build_ui(self) -> None:
        main_frame = self._make_frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        title = self._make_label(main_frame, text="INU Assignment Sync")
        title.pack(anchor="w", pady=(0, 12))

        form_frame = self._make_frame(main_frame)
        form_frame.pack(fill="x", padx=4, pady=4)

        self._add_form_row(form_frame, "BASE_URL", self.base_url_var, row=0, readonly=True)
        self._add_form_row(form_frame, "Calendar 이름", self.calendar_name_var, row=1)
        self._add_form_row(form_frame, "이전 몇 개월", self.months_back_var, row=2)
        self._add_form_row(form_frame, "이후 몇 개월", self.months_forward_var, row=3)
        self._add_form_row(form_frame, "알림 분 설정", self.reminder_minutes_var, row=4)

        checkbox_row = self._make_frame(form_frame)
        checkbox_row.grid(row=5, column=0, columnspan=2, sticky="w", padx=8, pady=8)
        self.include_past_checkbox = self._make_checkbox(checkbox_row, "지난 과제 포함", self.include_past_var)
        self.include_past_checkbox.pack(side="left", padx=(0, 16))
        self.dry_run_checkbox = self._make_checkbox(checkbox_row, "DRY_RUN", self.dry_run_var)
        self.dry_run_checkbox.pack(side="left")

        button_frame = self._make_frame(main_frame)
        button_frame.pack(fill="x", padx=4, pady=(12, 8))

        self.save_button = self._make_button(button_frame, "설정 저장", self.save_settings)
        self.save_button.pack(side="left", padx=(0, 8))
        self.run_button = self._make_button(button_frame, "동기화 실행", self.run_sync)
        self.run_button.pack(side="left", padx=(0, 8))
        self.dry_run_button = self._make_button(button_frame, "DRY RUN 실행", self.run_dry_run)
        self.dry_run_button.pack(side="left", padx=(0, 8))
        self.reset_button = self._make_button(button_frame, "동기화 기록 초기화", self.reset_sync_history)
        self.reset_button.pack(side="left", padx=(0, 8))
        self.readme_button = self._make_button(button_frame, "README 열기", self.open_readme)
        self.readme_button.pack(side="left")

        status_frame = self._make_frame(main_frame)
        status_frame.pack(fill="x", padx=4, pady=8)
        self.status_label = self._make_label(status_frame, textvariable=self.status_var)
        self.status_label.pack(anchor="w")
        self.summary_label = self._make_label(status_frame, textvariable=self.summary_var)
        self.summary_label.pack(anchor="w", pady=(6, 0))

        log_frame = self._make_frame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=4, pady=(12, 4))
        log_title = self._make_label(log_frame, text="실행 로그")
        log_title.pack(anchor="w", pady=(0, 8))
        self.log_widget = self._make_log_widget(log_frame)
        self.log_widget.pack(fill="both", expand=True)

        self._append_log(f"[INFO] GUI 모드: {GUI_MODE}")
        self._append_log(f"[INFO] 로그 파일: {LOG_FILE_PATH}")

    def _add_form_row(self, parent, label_text: str, variable, row: int, readonly: bool = False) -> None:
        label = self._make_label(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", padx=8, pady=6)
        entry = self._make_entry(parent, textvariable=variable, readonly=readonly)
        entry.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
        parent.grid_columnconfigure(1, weight=1)

    def _append_log(self, text: str) -> None:
        self.log_widget.insert("end", text + "\n")
        self.log_widget.see("end")
        self.logger.info(text)

    def save_settings(self) -> bool:
        updates = {
            "BASE_URL": self.base_url_var.get().strip(),
            "CALENDAR_NAME": self.calendar_name_var.get().strip(),
            "CALENDAR_MONTHS_BACK": self.months_back_var.get().strip(),
            "CALENDAR_MONTHS_FORWARD": self.months_forward_var.get().strip(),
            "INCLUDE_PAST_ASSIGNMENTS": str(self.include_past_var.get()).lower(),
            "REMINDER_MINUTES": self.reminder_minutes_var.get().strip(),
            "DRY_RUN": str(self.dry_run_var.get()).lower(),
        }

        try:
            int(updates["CALENDAR_MONTHS_BACK"])
            int(updates["CALENDAR_MONTHS_FORWARD"])
        except ValueError:
            messagebox.showerror("설정 오류", "이전/이후 개월 수는 숫자여야 합니다.")
            self.status_var.set("설정 오류")
            return False

        update_env_file(ENV_PATH, updates)
        self._append_log("[INFO] 설정을 저장했습니다.")
        self.status_var.set("설정 저장 완료")
        return True

    def _run_main_subprocess(self, env_overrides: dict[str, str]) -> None:
        env = os.environ.copy()
        env.update(env_overrides)
        cmd = [sys.executable, str(PROJECT_ROOT / "main.py")]

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as error:
            self.output_queue.put(f"[ERROR] 프로세스 시작 실패: {error}")
            self.output_queue.put("__PROCESS_DONE__")
            return

        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.output_queue.put(line.rstrip("\n"))

        self.process.wait()
        self.output_queue.put("__PROCESS_DONE__")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for widget in [self.save_button, self.run_button, self.dry_run_button, self.reset_button, self.readme_button]:
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def _start_run(self, force_dry_run: bool) -> None:
        if not self.save_settings():
            self._append_log("[ERROR] 설정 검증에 실패해 실행을 중단했습니다.")
            return
        self.summary_lines.clear()
        self._set_buttons_enabled(False)
        self.status_var.set("실행 중...")
        self.summary_var.set("동기화 진행 중입니다.")

        overrides = {
            "DRY_RUN": "true" if force_dry_run else str(self.dry_run_var.get()).lower(),
            "CALENDAR_NAME": self.calendar_name_var.get().strip(),
            "CALENDAR_MONTHS_BACK": self.months_back_var.get().strip(),
            "CALENDAR_MONTHS_FORWARD": self.months_forward_var.get().strip(),
            "INCLUDE_PAST_ASSIGNMENTS": str(self.include_past_var.get()).lower(),
            "REMINDER_MINUTES": self.reminder_minutes_var.get().strip(),
        }

        thread = threading.Thread(target=self._run_main_subprocess, args=(overrides,), daemon=True)
        thread.start()

    def run_sync(self) -> None:
        self._append_log("[INFO] 동기화 실행 요청")
        self._start_run(force_dry_run=False)

    def run_dry_run(self) -> None:
        self._append_log("[INFO] DRY RUN 실행 요청")
        self._start_run(force_dry_run=True)

    def reset_sync_history(self) -> None:
        try:
            if DATABASE_PATH.exists():
                DATABASE_PATH.unlink()
                self._append_log("[INFO] SQLite 동기화 기록을 삭제했습니다.")
                self.status_var.set("동기화 기록 초기화 완료")
            else:
                self._append_log("[INFO] 삭제할 동기화 기록이 없습니다.")
        except Exception as error:
            messagebox.showerror("초기화 실패", f"동기화 기록 삭제 실패: {error}")

    def open_readme(self) -> None:
        if README_PATH.exists():
            webbrowser.open(README_PATH.as_uri())
        else:
            messagebox.showerror("파일 없음", "README.md 파일을 찾지 못했습니다.")

    def _parse_summary_line(self, line: str) -> None:
        if re.match(r"^\[(INFO|ERROR)\] (수집된 과제 수|신규 등록 대상|업데이트 대상|스킵|실패):", line):
            self.summary_lines.append(line)
            self.summary_var.set(" | ".join(self.summary_lines[-5:]))

    def _poll_output_queue(self) -> None:
        while True:
            try:
                line = self.output_queue.get_nowait()
            except queue.Empty:
                break

            if line == "__PROCESS_DONE__":
                self._set_buttons_enabled(True)
                self.status_var.set("실행 완료")
                self._append_log("[INFO] 실행이 완료되었습니다.")
                continue

            self._append_log(line)
            self._parse_summary_line(line)

        self.root.after(200, self._poll_output_queue)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = SyncAppGUI()
    app.run()
