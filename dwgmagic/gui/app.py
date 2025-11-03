"""Tkinter-based GUI runner for the DWGMAGIC pipeline."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Sequence

from jinja2 import Environment

from dwgmagic.core.context import ProjectConfig, ProjectContext
from dwgmagic.core.pipeline import PipelineRunner, PipelineStage
from dwgmagic.core.stages import build_default_stages
from dwgmagic.integrations.autocad import AutoCadCoordinator, AutoCadRunner
from dwgmagic.logger import LoggerFactory
from dwgmagic.settings import Settings
from dwgmagic.ui.progress import ProgressEvent, QueueProgressListener


class QueueLogHandler(logging.Handler):
    """Logging handler that forwards formatted records to the GUI queue."""

    def __init__(self, event_queue: "queue.Queue[ProgressEvent]") -> None:
        super().__init__()
        self.event_queue = event_queue

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - exercised via GUI
        try:
            message = self.format(record)
        except Exception:  # pragma: no cover - defensive
            message = record.getMessage()
        self.event_queue.put(
            ProgressEvent(
                "log",
                {
                    "name": record.name,
                    "level": record.levelname,
                    "message": message,
                },
            )
        )


class GuiApplication:
    """Encapsulates the Tkinter user interface and pipeline orchestration."""

    def __init__(
        self,
        *,
        settings: Settings,
        environment: Environment,
        runner: AutoCadRunner,
        coordinator: AutoCadCoordinator,
        base_logger_factory: LoggerFactory,
    ) -> None:
        self.settings = settings
        self.environment = environment
        self.runner = runner
        self.coordinator = coordinator
        self.event_queue: "queue.Queue[ProgressEvent]" = queue.Queue()

        self.log_handler = QueueLogHandler(self.event_queue)
        self.log_handler.setLevel(logging.DEBUG)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.logger_factory = base_logger_factory.with_handlers(self.log_handler)

        self.stages: Sequence[PipelineStage] = build_default_stages(
            environment, self.logger_factory, runner, coordinator
        )
        self.stage_names = [stage.name for stage in self.stages]
        self.pipeline = PipelineRunner.from_iterable(self.stages)

        self.context = self._new_context()
        self.listener = QueueProgressListener(self.event_queue)

        self.root = tk.Tk()
        self.root.title("DWGMAGIC Pipeline Monitor")
        self.root.geometry("900x600")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.completed_stages = 0
        self.job_total = 0
        self.job_completed = 0
        self.job_states: dict[str, dict[str, str | int | None]] = {}
        self._running = False

        self._build_layout()
        self._reset_stage_table()
        self._reset_job_table()
        self.root.after(100, self._process_events)

    def _new_context(self) -> ProjectContext:
        config = ProjectConfig(settings=self.settings, stages=self.stage_names)
        return ProjectContext(config=config, environment=self.environment)

    # UI construction -----------------------------------------------------
    def _build_layout(self) -> None:
        header = ttk.Label(self.root, text="DWGMAGIC Pipeline", font=("Segoe UI", 18, "bold"))
        header.pack(pady=10)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10)
        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=8)

        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=max(len(self.stage_names), 1),
            mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X)

        table_frame = ttk.LabelFrame(self.root, text="Stages")
        table_frame.pack(fill=tk.X, padx=10, pady=10)
        self.stage_table = ttk.Treeview(
            table_frame,
            columns=("stage", "status"),
            show="headings",
            height=5,
        )
        self.stage_table.heading("stage", text="Stage")
        self.stage_table.heading("status", text="Status")
        self.stage_table.column("stage", width=200)
        self.stage_table.column("status", width=150)
        self.stage_table.pack(fill=tk.X, padx=5, pady=5)

        jobs_frame = ttk.LabelFrame(self.root, text="AutoCAD Jobs")
        jobs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        summary_frame = ttk.Frame(jobs_frame)
        summary_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.job_summary_var = tk.StringVar(value="Waiting to queue jobs")
        ttk.Label(
            summary_frame,
            textvariable=self.job_summary_var,
            font=("Segoe UI", 11),
        ).pack(side=tk.LEFT)

        self.job_progress_var = tk.DoubleVar(value=0.0)
        self.job_progress = ttk.Progressbar(
            jobs_frame,
            variable=self.job_progress_var,
            maximum=1,
            mode="determinate",
        )
        self.job_progress.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.job_table = ttk.Treeview(
            jobs_frame,
            columns=("job", "script", "status", "code"),
            show="headings",
            height=8,
        )
        self.job_table.heading("job", text="Job")
        self.job_table.heading("script", text="Script")
        self.job_table.heading("status", text="Status")
        self.job_table.heading("code", text="Return Code")
        self.job_table.column("job", width=180)
        self.job_table.column("script", width=280)
        self.job_table.column("status", width=140)
        self.job_table.column("code", width=110)
        self.job_table.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        log_frame = ttk.LabelFrame(self.root, text="Activity")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_widget = ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.log_widget.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.run_button = ttk.Button(button_frame, text="Run Pipeline", command=self._start_pipeline)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Close", command=self._on_close).pack(side=tk.RIGHT)

    def _reset_stage_table(self) -> None:
        for row in self.stage_table.get_children():
            self.stage_table.delete(row)
        for name in self.stage_names:
            self.stage_table.insert("", tk.END, iid=name, values=(self._display_name(name), "Pending"))
        self.progress_var.set(0.0)
        self.completed_stages = 0

    def _display_name(self, stage_name: str) -> str:
        return stage_name.replace("_", " ").title()

    def _reset_job_table(self) -> None:
        if hasattr(self, "job_table"):
            for row in self.job_table.get_children():
                self.job_table.delete(row)
        self.job_total = 0
        self.job_completed = 0
        self.job_states.clear()
        if hasattr(self, "job_progress"):
            self.job_progress.configure(maximum=1)
            self.job_progress_var.set(0.0)
        if hasattr(self, "job_summary_var"):
            self.job_summary_var.set("Waiting to queue jobs")
        self._update_job_summary()

    def _update_job_summary(self) -> None:
        if not hasattr(self, "job_progress"):
            return
        if self.job_total:
            summary = f"Jobs completed: {self.job_completed}/{self.job_total}"
        else:
            summary = "Waiting to queue jobs"
        self.job_summary_var.set(summary)
        self.job_progress.configure(maximum=max(self.job_total, 1))
        self.job_progress_var.set(float(self.job_completed))

    def _ensure_stage_row(self, name: str) -> None:
        if not self.stage_table.exists(name):
            self.stage_table.insert(
                "",
                tk.END,
                iid=name,
                values=(self._display_name(name), "Pending"),
            )

    # Event handling ------------------------------------------------------
    def _start_pipeline(self) -> None:
        if self._running:
            return
        self._running = True
        self.run_button.config(state=tk.DISABLED)
        self.status_var.set("Preparing pipeline...")
        self._reset_stage_table()
        self._reset_job_table()
        self._append_log("Starting pipeline run...")

        self.context = self._new_context()
        self.context.set("autocad_listener", self.listener)

        thread = threading.Thread(target=self._run_pipeline_thread, daemon=True)
        thread.start()

    def _run_pipeline_thread(self) -> None:
        try:
            self.pipeline.run(self.context, listener=self.listener)
        except Exception as exc:  # pragma: no cover - surfaced via GUI
            self.event_queue.put(ProgressEvent("pipeline_error", {"error": str(exc)}))
        finally:
            self.event_queue.put(ProgressEvent("pipeline_thread_complete", {}))

    def _process_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def _handle_event(self, event: ProgressEvent) -> None:
        kind = event.kind
        payload = event.payload
        if kind == "stage_started":
            name = payload["name"]
            self._ensure_stage_row(name)
            self.stage_table.item(name, values=(self._display_name(name), "Running"))
            self.status_var.set(f"Running stage {self._display_name(name)}")
        elif kind == "stage_completed":
            name = payload["name"]
            self._ensure_stage_row(name)
            status_text = "Completed" if payload.get("succeeded") else "Failed"
            self.completed_stages += 1
            self.stage_table.item(name, values=(self._display_name(name), status_text))
            self.progress_var.set(self.completed_stages)
            if not payload.get("succeeded") and payload.get("details"):
                self._append_log(f"Stage {name} failed: {payload['details']}", error=True)
        elif kind == "pipeline_completed":
            succeeded = all(item.get("succeeded", False) for item in payload.get("results", []))
            if succeeded:
                self.status_var.set("Pipeline completed successfully")
                self._append_log("Pipeline completed successfully")
            else:
                self.status_var.set("Pipeline completed with errors")
                self._append_log("Pipeline completed with errors", error=True)
            self.progress_var.set(float(len(self.stage_names)))
        elif kind == "pipeline_error":
            self.status_var.set("Pipeline crashed")
            self._append_log(f"Pipeline crashed: {payload['error']}", error=True)
        elif kind == "pipeline_thread_complete":
            self._running = False
            self.run_button.config(state=tk.NORMAL)
        elif kind == "job_queued":
            job_name = payload["name"]
            script_path = payload.get("script") or ""
            script_display = Path(script_path).name if script_path else "—"
            if not self.job_table.exists(job_name):
                self.job_table.insert(
                    "",
                    tk.END,
                    iid=job_name,
                    values=(job_name, script_display, "Queued", ""),
                )
            else:
                self.job_table.item(
                    job_name,
                    values=(job_name, script_display, "Queued", ""),
                )
            self.job_states[job_name] = {"status": "Queued", "code": None}
            self.job_total += 1
            self._update_job_summary()
            self._append_log(
                f"Queued job {job_name} (script: {script_display})"
            )
        elif kind == "job_started":
            job_name = payload["name"]
            if not self.job_table.exists(job_name):
                self.job_table.insert(
                    "",
                    tk.END,
                    iid=job_name,
                    values=(job_name, "—", "Running", ""),
                )
            else:
                values = list(self.job_table.item(job_name, "values"))
                if len(values) < 4:
                    values = [job_name, "—", "Running", ""]
                else:
                    values[2] = "Running"
                self.job_table.item(job_name, values=tuple(values))
            self.job_states[job_name] = {"status": "Running", "code": None}
            self._append_log(f"Running job {job_name}")
        elif kind == "job_completed":
            status = "succeeded" if payload.get("succeeded") else "failed"
            job_name = payload["name"]
            return_code = payload.get("returncode")
            if self.job_table.exists(job_name):
                values = list(self.job_table.item(job_name, "values"))
                if len(values) < 4:
                    values = [job_name, "—", "", ""]
                values[2] = "Completed" if payload.get("succeeded") else "Failed"
                values[3] = str(return_code) if return_code is not None else ""
                self.job_table.item(job_name, values=tuple(values))
                script_display = values[1]
            else:
                script_display = "—"
                self.job_table.insert(
                    "",
                    tk.END,
                    iid=job_name,
                    values=(job_name, script_display, "Completed", str(return_code or "")),
                )
            self.job_states[job_name] = {
                "status": "Completed" if payload.get("succeeded") else "Failed",
                "code": return_code,
            }
            self.job_completed = min(self.job_total, self.job_completed + 1)
            self._update_job_summary()
            self._append_log(
                f"Job {job_name} {status} with code {return_code} (script: {script_display})"
            )
            stdout = (payload.get("stdout") or "").strip()
            stderr = (payload.get("stderr") or "").strip()
            if stdout:
                self._append_log(stdout)
            if stderr:
                self._append_log(stderr, error=not payload.get("succeeded"))
        elif kind == "job_failed":
            job_name = payload["name"]
            error_message = payload.get("error", "")
            if not self.job_table.exists(job_name):
                self.job_table.insert(
                    "",
                    tk.END,
                    iid=job_name,
                    values=(job_name, "—", "Failed", ""),
                )
            else:
                values = list(self.job_table.item(job_name, "values"))
                if len(values) < 4:
                    values = [job_name, "—", "Failed", ""]
                else:
                    values[2] = "Failed"
                self.job_table.item(job_name, values=tuple(values))
            self.job_states[job_name] = {"status": "Failed", "code": None}
            self.job_completed = min(self.job_total, self.job_completed + 1)
            self._update_job_summary()
            self._append_log(
                f"Job {job_name} failed: {error_message}",
                error=True,
            )
        elif kind == "log":
            level = payload.get("level", "INFO")
            message = payload.get("message", "")
            tag = level.upper()
            self._append_log(f"[{tag}] {message}", error=level.upper() in {"ERROR", "CRITICAL"})

    def _append_log(self, message: str, *, error: bool = False) -> None:
        self.log_widget.configure(state=tk.NORMAL)
        colour = "red" if error else "black"
        self.log_widget.insert(tk.END, message + "\n", colour)
        self.log_widget.tag_configure(colour, foreground=colour)
        self.log_widget.see(tk.END)
        self.log_widget.configure(state=tk.DISABLED)

    def _on_close(self) -> None:
        self.root.quit()

    def run(self) -> None:
        self.root.mainloop()


def run_gui(
    *,
    settings: Settings,
    environment: Environment,
    runner: AutoCadRunner,
    coordinator: AutoCadCoordinator,
    base_logger_factory: LoggerFactory,
) -> None:
    """Entry point used by the CLI to launch the GUI."""

    app = GuiApplication(
        settings=settings,
        environment=environment,
        runner=runner,
        coordinator=coordinator,
        base_logger_factory=base_logger_factory,
    )
    app.run()


__all__ = ["run_gui", "GuiApplication"]
