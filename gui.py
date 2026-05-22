"""Tkinter GUI — QQ 好友生日导出工具"""
import logging
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime

from logger import setup
from pipeline import run_pipeline

logger = logging.getLogger(__name__)


class BirthdayExporterGUI:
    """主 GUI 窗口"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("QQ 好友生日导出工具")
        self.root.geometry("560x480")
        self.root.minsize(480, 360)
        self.root.resizable(True, True)

        self._message_queue = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._cancel_flag = threading.Event()
        self._output_path: Path | None = None
        self._running = False

        self._build_ui()
        self._poll_queue()

    # ── UI 构建 ──

    def _build_ui(self):
        # 主框架
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # 标题
        title = ttk.Label(main, text="QQ 好友生日导出工具", font=("", 14, "bold"))
        title.pack(pady=(0, 10))

        # 状态栏
        status_frame = ttk.LabelFrame(main, text="状态", padding=8)
        status_frame.pack(fill=tk.X, pady=(0, 8))

        self.status_var = tk.StringVar(value="就绪 — 点击「开始导出」启动")
        self.status_label = ttk.Label(
            status_frame, textvariable=self.status_var, font=("", 10)
        )
        self.status_label.pack(anchor=tk.W)

        # 进度条
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=12,
            mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X, pady=(6, 2))

        self.progress_text = tk.StringVar(value="")
        ttk.Label(
            status_frame, textvariable=self.progress_text, font=("", 9)
        ).pack(anchor=tk.E)

        # 日志区
        log_frame = ttk.LabelFrame(main, text="运行日志", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.log_text = tk.Text(
            log_frame,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
        )
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 底部按钮
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X)

        self.start_btn = ttk.Button(
            btn_frame, text="开始导出", command=self._start_export
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.open_btn = ttk.Button(
            btn_frame,
            text="打开文件位置",
            command=self._open_output_folder,
            state=tk.DISABLED,
        )
        self.open_btn.pack(side=tk.LEFT)

        self.cancel_btn = ttk.Button(
            btn_frame,
            text="取消",
            command=self._cancel,
            state=tk.DISABLED,
        )
        self.cancel_btn.pack(side=tk.RIGHT)

        # 版权/版本
        ttk.Label(
            main, text="v0.2 · QQ 邮箱日历数据来源", font=("", 8), foreground="gray"
        ).pack(side=tk.BOTTOM, pady=(8, 0))

    # ── 日志 ──

    def _log(self, message: str):
        """线程安全地追加日志"""
        self._message_queue.put(("log", message))

    def _append_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    # ── 按钮动作 ──

    def _start_export(self):
        if self._running:
            return

        self._running = True
        self._cancel_flag.clear()
        self._set_ui_state("running")
        self._log("开始导出流程...")

        self._worker_thread = threading.Thread(
            target=self._do_export, daemon=True
        )
        self._worker_thread.start()

    def _cancel(self):
        if not self._running:
            return
        self._log("正在取消...")
        self._cancel_flag.set()
        self._set_status("取消中，等待当前操作完成...")

    def _open_output_folder(self):
        if self._output_path and self._output_path.parent.exists():
            import os
            os.startfile(self._output_path.parent)

    # ── UI 状态管理 ──

    def _set_ui_state(self, state: str):
        """切换 UI 状态：idle / running / done"""
        if state == "running":
            self.start_btn.configure(state=tk.DISABLED)
            self.cancel_btn.configure(state=tk.NORMAL)
            self.open_btn.configure(state=tk.DISABLED)
        elif state == "done":
            self.start_btn.configure(state=tk.NORMAL)
            self.cancel_btn.configure(state=tk.DISABLED)
            self.open_btn.configure(state=tk.NORMAL)
        else:  # idle
            self.start_btn.configure(state=tk.NORMAL)
            self.cancel_btn.configure(state=tk.DISABLED)

    def _set_status(self, msg: str):
        self._message_queue.put(("status", msg))

    def _set_progress(self, current: int, total: int):
        self._message_queue.put(("progress", (current, total)))

    # ── 消息轮询（主线程安全）──

    def _poll_queue(self):
        """定时从队列中取出消息并在主线程更新 UI"""
        try:
            while True:
                msg = self._message_queue.get_nowait()
                msg_type = msg[0]

                if msg_type == "log":
                    self._append_log(msg[1])
                elif msg_type == "status":
                    self.status_var.set(msg[1])
                elif msg_type == "progress":
                    current, total = msg[1]
                    self.progress_var.set(current)
                    self.progress_text.set(f"{current}/{total} 月")
                elif msg_type == "done":
                    path, count = msg[1]
                    self._on_done(path, count)
                elif msg_type == "error":
                    self._on_error(msg[1])

                self._message_queue.task_done()
        except queue.Empty:
            pass

        self.root.after(100, self._poll_queue)

    def _on_done(self, path: Path, count: int):
        self._running = False
        self._output_path = path
        self._set_ui_state("done")
        self._set_status(f"导出完成 — {count} 位好友生日")
        self.progress_var.set(12)
        self.progress_text.set("12/12 月")
        self._log(f"✓ 导出成功：{path}")
        self._log(f"✓ 共计 {count} 位好友生日")
        messagebox.showinfo("导出完成", f"已导出 {count} 位好友生日\n文件：{path}")

    def _on_error(self, error_msg: str):
        self._running = False
        self._set_ui_state("done")
        self._set_status(f"错误：{error_msg}")
        self._log(f"✗ 错误：{error_msg}")
        messagebox.showerror("导出失败", error_msg)

    # ── 后台工作线程 ──

    def _do_export(self):
        """后台线程：执行登录 → 爬取 → 导出全流程，委托给 pipeline"""
        run_pipeline(
            on_status=self._set_status,
            on_progress=self._set_progress,
            on_log=self._log,
            on_done=lambda path, count, friends: self._message_queue.put(("done", (path, count))),
            on_error=lambda msg: self._message_queue.put(("error", msg)),
            is_cancelled=self._cancel_flag.is_set,
        )

    # ── 启动 ──

    def run(self):
        self.root.mainloop()


def main():
    setup()
    app = BirthdayExporterGUI()
    app.run()


if __name__ == "__main__":
    main()
