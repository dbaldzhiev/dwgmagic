"""Tkinter-based GUI runner for the DWGMAGIC pipeline."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Callable, Iterable, Mapping, Sequence

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

    STATUS_STYLES: Mapping[str, Mapping[str, str]] = {
        "pending": {"foreground": "#6c757d"},
        "queued": {"foreground": "#0d6efd"},
        "running": {"foreground": "#fd7e14"},
        "completed": {"foreground": "#198754"},
        "failed": {"foreground": "#dc3545"},
    }

    def __init__(
        self,
        *,
        settings_loader: Callable[[Path], Settings],
        environment_builder: Callable[[Settings], Environment],
        runner_factory: Callable[[Settings], AutoCadRunner],
        coordinator_factory: Callable[[AutoCadRunner], AutoCadCoordinator],
        logger_factory_builder: Callable[[Settings], LoggerFactory],
        initial_project: Path | None = None,
    ) -> None:
        self.settings_loader = settings_loader
        self.environment_builder = environment_builder
        self.runner_factory = runner_factory
        self.coordinator_factory = coordinator_factory
        self.logger_factory_builder = logger_factory_builder

        self.current_settings: Settings | None = None
        self.environment: Environment | None = None
        self.runner: AutoCadRunner | None = None
        self.coordinator: AutoCadCoordinator | None = None
        self.logger_factory: LoggerFactory | None = None
        self.pipeline: PipelineRunner | None = None
        self.stages: Sequence[PipelineStage] = ()
        self.stage_names: list[str] = []

        self.event_queue: "queue.Queue[ProgressEvent]" = queue.Queue()

        self.log_handler = QueueLogHandler(self.event_queue)
        self.log_handler.setLevel(logging.DEBUG)
        self.log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        self.listener = QueueProgressListener(self.event_queue)

        self.root = tk.Tk()
        self.root.title("DWGMAGIC Pipeline Monitor")
        self.root.geometry("1280x860")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.project_var = tk.StringVar(value="No project selected")
        self.completed_stages = 0
        self.job_total = 0
        self.job_completed = 0
        self.job_states: dict[str, dict[str, str | int | None]] = {}
        self.job_logs: dict[str, list[str]] = {}
        self.task_info: dict[str, dict[str, str | int | None]] = {}
        self.task_parents: dict[str, str] = {}
        self._current_task_selection: str | None = None
        self.context: ProjectContext | None = None
        self._running = False

        self._build_layout()
        self._reset_stage_table()
        self._reset_task_tree()
        self.root.after(100, self._process_events)

        if initial_project:
            try:
                self._load_project(initial_project)
            except Exception as exc:  # pragma: no cover - surfaced via GUI
                messagebox.showerror("Project Load Failed", str(exc))

    def _new_context(self) -> ProjectContext:
        if not self.current_settings or not self.environment:
            raise RuntimeError("Project configuration has not been loaded")
        config = ProjectConfig(settings=self.current_settings, stages=self.stage_names)
        return ProjectContext(config=config, environment=self.environment)

    # UI construction -----------------------------------------------------
    def _build_layout(self) -> None:
        header = ttk.Label(self.root, text="DWGMAGIC Pipeline", font=("Segoe UI", 20, "bold"))
        header.pack(pady=(12, 4))

        project_frame = ttk.Frame(self.root)
        project_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        ttk.Label(project_frame, text="Project:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(project_frame, textvariable=self.project_var, font=("Segoe UI", 11)).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Button(project_frame, text="Open Project…", command=self._choose_project).pack(
            side=tk.RIGHT
        )

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=12)
        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 12)).pack(
            side=tk.LEFT, padx=8
        )

        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=tk.X, padx=12, pady=(6, 8))
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=1,
            mode="determinate",
        )
        self.progress_bar.pack(fill=tk.X)

        table_frame = ttk.LabelFrame(self.root, text="Stages")
        table_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        stage_container = ttk.Frame(table_frame)
        stage_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        stage_container.columnconfigure(0, weight=1)
        stage_container.rowconfigure(0, weight=1)

        stage_scroll_y = ttk.Scrollbar(stage_container, orient=tk.VERTICAL)
        stage_scroll_y.grid(row=0, column=1, sticky=tk.NS)

        self.stage_table = ttk.Treeview(
            stage_container,
            columns=("stage", "status"),
            show="headings",
            height=5,
            yscrollcommand=stage_scroll_y.set,
        )
        self.stage_table.heading("stage", text="Stage")
        self.stage_table.heading("status", text="Status")
        self.stage_table.column("stage", width=220, anchor=tk.W)
        self.stage_table.column("status", width=160, anchor=tk.W)
        self.stage_table.grid(row=0, column=0, sticky=tk.NSEW)
        stage_scroll_y.configure(command=self.stage_table.yview)

        paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        left_container = ttk.Frame(paned)
        right_container = ttk.Frame(paned)
        paned.add(left_container, weight=2)
        paned.add(right_container, weight=3)

        tasks_frame = ttk.LabelFrame(left_container, text="AutoCAD Tasks")
        tasks_frame.pack(fill=tk.BOTH, expand=True, padx=(0, 6), pady=0)

        summary_frame = ttk.Frame(tasks_frame)
        summary_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        self.job_summary_var = tk.StringVar(value="Waiting for project selection")
        ttk.Label(summary_frame, textvariable=self.job_summary_var, font=("Segoe UI", 11)).pack(
            side=tk.LEFT
        )

        self.job_progress_var = tk.DoubleVar(value=0.0)
        self.job_progress = ttk.Progressbar(
            tasks_frame,
            variable=self.job_progress_var,
            maximum=1,
            mode="determinate",
        )
        self.job_progress.pack(fill=tk.X, padx=8, pady=(0, 6))

        tree_container = ttk.Frame(tasks_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)

        tree_scroll_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL)
        tree_scroll_y.grid(row=0, column=1, sticky=tk.NS)
        tree_scroll_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL)
        tree_scroll_x.grid(row=1, column=0, sticky=tk.EW)

        self.task_tree = ttk.Treeview(
            tree_container,
            columns=("status", "code"),
            show="tree headings",
            selectmode="browse",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
        )
        self.task_tree.heading("#0", text="Task")
        self.task_tree.heading("status", text="Status")
        self.task_tree.heading("code", text="Return Code")
        self.task_tree.column("#0", minwidth=220, stretch=True)
        self.task_tree.column("status", width=140, anchor=tk.W)
        self.task_tree.column("code", width=110, anchor=tk.CENTER)
        self.task_tree.grid(row=0, column=0, sticky=tk.NSEW)
        tree_scroll_y.configure(command=self.task_tree.yview)
        tree_scroll_x.configure(command=self.task_tree.xview)
        self.task_tree.bind("<<TreeviewSelect>>", self._on_task_selected)

        right_inner = ttk.Frame(right_container)
        right_inner.pack(fill=tk.BOTH, expand=True)

        detail_frame = ttk.LabelFrame(right_inner, text="Task Details")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 6))

        detail_top = ttk.Frame(detail_frame)
        detail_top.pack(fill=tk.X, padx=8, pady=(8, 4))
        ttk.Label(detail_top, text="Name:", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.detail_name_var = tk.StringVar(value="—")
        ttk.Label(detail_top, textvariable=self.detail_name_var, font=("Segoe UI", 11)).grid(
            row=0, column=1, sticky=tk.W, padx=(6, 0)
        )
        ttk.Label(detail_top, text="Status:", font=("Segoe UI", 11, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.detail_status_var = tk.StringVar(value="—")
        ttk.Label(detail_top, textvariable=self.detail_status_var, font=("Segoe UI", 11)).grid(
            row=1, column=1, sticky=tk.W, padx=(6, 0), pady=(4, 0)
        )
        ttk.Label(detail_top, text="Return Code:", font=("Segoe UI", 11, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.detail_code_var = tk.StringVar(value="—")
        ttk.Label(detail_top, textvariable=self.detail_code_var, font=("Segoe UI", 11)).grid(
            row=2, column=1, sticky=tk.W, padx=(6, 0), pady=(4, 0)
        )
        ttk.Label(detail_top, text="Script:", font=("Segoe UI", 11, "bold")).grid(
            row=3, column=0, sticky=tk.W, pady=(4, 0)
        )
        self.detail_script_var = tk.StringVar(value="—")
        ttk.Label(detail_top, textvariable=self.detail_script_var, font=("Segoe UI", 11)).grid(
            row=3, column=1, sticky=tk.W, padx=(6, 0), pady=(4, 0)
        )
        detail_top.columnconfigure(1, weight=1)

        self.task_log = ScrolledText(detail_frame, state=tk.DISABLED, wrap=tk.WORD, height=12)
        self.task_log.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        log_frame = ttk.LabelFrame(right_inner, text="Activity Log")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=(6, 0), pady=(0, 10))
        self.log_widget = ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.log_widget.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=12, pady=(0, 12))
        self.run_button = ttk.Button(button_frame, text="Run Pipeline", command=self._start_pipeline)
        self.run_button.pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Close", command=self._on_close).pack(side=tk.RIGHT)

        self._configure_status_tags(self.stage_table)
        self._configure_status_tags(self.task_tree)

    def _reset_stage_table(self) -> None:
        for row in self.stage_table.get_children():
            self.stage_table.delete(row)
        if not self.stage_names:
            self.progress_bar.configure(maximum=1)
        else:
            self.progress_bar.configure(maximum=len(self.stage_names))
        for name in self.stage_names:
            self.stage_table.insert(
                "",
                tk.END,
                iid=name,
                values=(self._display_name(name), "Pending"),
                tags=(self._status_tag("pending"),),
            )
        self.progress_var.set(0.0)
        self.completed_stages = 0

    def _display_name(self, stage_name: str) -> str:
        return stage_name.replace("_", " ").title()

    def _reset_task_tree(self) -> None:
        if hasattr(self, "task_tree"):
            for row in self.task_tree.get_children():
                self.task_tree.delete(row)
        self.task_info.clear()
        self.job_states.clear()
        self.job_logs.clear()
        self.task_parents = {"merge": ""}
        self.job_total = 0
        self.job_completed = 0
        if hasattr(self, "job_progress"):
            self.job_progress.configure(maximum=1)
            self.job_progress_var.set(0.0)
        if hasattr(self, "job_summary_var"):
            self.job_summary_var.set("Waiting for project selection")
        # Ensure merge root exists for visual hierarchy
        self.task_tree.insert(
            "",
            tk.END,
            iid="merge",
            text="Merge",
            values=("Pending", ""),
            tags=(self._status_tag("pending"),),
        )
        self.task_tree.item("merge", open=True)
        self.task_info["merge"] = {
            "name": "merge",
            "title": "Merge",
            "status": "pending",
            "code": None,
            "script": None,
        }
        self.job_logs["merge"] = []
        self.task_tree.selection_set("merge")
        self._current_task_selection = "merge"
        self._refresh_task_details("merge")
        self._refresh_task_log("merge")
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
                tags=(self._status_tag("pending"),),
            )

    def _configure_status_tags(self, widget: ttk.Treeview) -> None:
        for key, style in self.STATUS_STYLES.items():
            widget.tag_configure(self._status_tag(key), **style)

    def _status_tag(self, status: str) -> str:
        return f"status:{status}"

    def _set_stage_status(self, name: str, status: str) -> None:
        normalised = status.lower()
        display = status.capitalize()
        self.stage_table.item(
            name,
            values=(self._display_name(name), display),
            tags=(self._status_tag(normalised),),
        )

    def _ensure_task_node(
        self,
        job_name: str,
        *,
        parent: str | None = None,
        title: str | None = None,
    ) -> None:
        if parent is None:
            parent = self.task_parents.get(job_name, "merge")
        else:
            self.task_parents[job_name] = parent
        if not title:
            existing = self.task_info.get(job_name)
            title = existing.get("title") if existing else job_name
        if not self.task_tree.exists(parent):
            parent = "merge"
        if not self.task_tree.exists(job_name):
            self.task_tree.insert(
                parent,
                tk.END,
                iid=job_name,
                text=title,
                values=("Pending", ""),
                tags=(self._status_tag("pending"),),
            )
        info = self.task_info.setdefault(
            job_name,
            {"name": job_name, "title": title, "status": "pending", "code": None, "script": None},
        )
        info["title"] = title
        self.job_logs.setdefault(job_name, [])

    def _set_task_status(
        self,
        job_name: str,
        status: str,
        *,
        code: int | None = None,
        script: str | None = None,
    ) -> None:
        if job_name not in self.task_info:
            # Default to merge hierarchy if unknown
            self._ensure_task_node(job_name, parent="merge", title=job_name)
        info = self.task_info[job_name]
        info["status"] = status.lower()
        if code is not None:
            info["code"] = code
        if script is not None:
            info["script"] = script
        display_status = status.capitalize()
        code_display = "" if info.get("code") is None else str(info.get("code"))
        self.task_tree.item(
            job_name,
            values=(display_status, code_display),
            tags=(self._status_tag(info["status"]),),
        )
        if job_name == self._current_task_selection:
            self._refresh_task_details(job_name)

    def _append_task_log(self, job_name: str, message: str) -> None:
        logs = self.job_logs.setdefault(job_name, [])
        logs.append(message)
        if job_name == self._current_task_selection:
            self._refresh_task_log(job_name)

    def _populate_task_tree(self, sheets: Iterable[Mapping[str, object]]) -> None:
        for sheet in sheets:
            sheet_name = str(sheet.get("sheetName") or sheet.get("name") or "Unnamed Sheet")
            sheet_id = f"sheet:{sheet_name}"
            self._ensure_task_node(sheet_id, parent="merge", title=f"Sheet: {sheet_name}")
            self.task_tree.item(sheet_id, open=True)
            views = sheet.get("viewsOnSheet") or sheet.get("views") or []
            for view in views:
                if isinstance(view, Mapping):
                    view_name = str(view.get("name") or view.get("viewName") or "View")
                else:
                    view_name = str(view)
                view_id = f"view:{view_name}"
                self._ensure_task_node(view_id, parent=sheet_id, title=f"View: {view_name}")
        self.task_tree.item("merge", open=True)

    def _handle_stage_data(self, stage_name: str, data: Mapping[str, object]) -> None:
        if stage_name == "generate_scripts":
            sheets = data.get("sheets") or data.get("structured_sheets")
            if isinstance(sheets, Iterable):
                self._populate_task_tree(sheets)  # type: ignore[arg-type]

    def _choose_project(self) -> None:
        if self._running:
            messagebox.showwarning(
                "Pipeline Running",
                "Please wait for the current pipeline run to finish before changing projects.",
            )
            return
        path_str = filedialog.askdirectory(title="Select DWGMAGIC Project")
        if not path_str:
            return
        try:
            self._load_project(Path(path_str).resolve())
        except Exception as exc:  # pragma: no cover - surfaced via GUI
            messagebox.showerror("Project Load Failed", str(exc))

    def _load_project(self, project_root: Path) -> None:
        if not project_root.exists():
            raise FileNotFoundError(project_root)

        settings = self.settings_loader(project_root)
        environment = self.environment_builder(settings)
        logger_factory = self.logger_factory_builder(settings).with_handlers(self.log_handler)
        runner = self.runner_factory(settings)
        coordinator = self.coordinator_factory(runner)

        self.current_settings = settings
        self.environment = environment
        self.logger_factory = logger_factory
        self.runner = runner
        self.coordinator = coordinator
        self.context = None

        self.stages = build_default_stages(environment, logger_factory, runner, coordinator)
        self.stage_names = [stage.name for stage in self.stages]
        self.pipeline = PipelineRunner.from_iterable(self.stages)

        self.project_var.set(str(project_root))
        self.status_var.set("Ready")
        self._reset_stage_table()
        self._reset_task_tree()
        self.job_summary_var.set("Waiting to queue jobs")
        self._append_log(f"Loaded project at {project_root}")

    def _on_task_selected(self, _event) -> None:
        selection = self.task_tree.selection()
        if not selection:
            return
        job_name = selection[0]
        self._current_task_selection = job_name
        self._refresh_task_details(job_name)

    def _refresh_task_details(self, job_name: str) -> None:
        info = self.task_info.get(job_name)
        if not info:
            self.detail_name_var.set("—")
            self.detail_status_var.set("—")
            self.detail_code_var.set("—")
            self.detail_script_var.set("—")
            self._refresh_task_log(job_name)
            return
        self.detail_name_var.set(info.get("title") or job_name)
        status = info.get("status", "pending").capitalize()
        self.detail_status_var.set(status)
        code = info.get("code")
        self.detail_code_var.set("—" if code is None else str(code))
        script = info.get("script")
        self.detail_script_var.set(script or "—")
        self._refresh_task_log(job_name)

    def _refresh_task_log(self, job_name: str) -> None:
        self.task_log.configure(state=tk.NORMAL)
        self.task_log.delete("1.0", tk.END)
        for line in self.job_logs.get(job_name, []):
            self.task_log.insert(tk.END, line + "\n")
        self.task_log.configure(state=tk.DISABLED)

    # Event handling ------------------------------------------------------
    def _start_pipeline(self) -> None:
        if self._running:
            return
        if not self.pipeline or not self.current_settings or not self.environment:
            messagebox.showinfo(
                "Select Project",
                "Please open a project folder before running the pipeline.",
            )
            return
        self._running = True
        self.run_button.config(state=tk.DISABLED)
        self.status_var.set("Preparing pipeline...")
        self._reset_stage_table()
        self._reset_task_tree()
        self.job_summary_var.set("Waiting to queue jobs")
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
            self._set_stage_status(name, "running")
            self.status_var.set(f"Running stage {self._display_name(name)}")
        elif kind == "stage_completed":
            name = payload["name"]
            self._ensure_stage_row(name)
            succeeded = payload.get("succeeded")
            status_text = "completed" if succeeded else "failed"
            self.completed_stages += 1
            self._set_stage_status(name, status_text)
            self.progress_var.set(self.completed_stages)
            if succeeded and payload.get("data"):
                self._handle_stage_data(name, payload["data"])
            if not succeeded and payload.get("details"):
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
            self.job_states[job_name] = {"status": "Queued", "code": None}
            self.job_total += 1
            self._ensure_task_node(job_name)
            self._set_task_status(job_name, "queued", script=script_display)
            self._append_task_log(job_name, f"Queued (script: {script_display})")
            self._update_job_summary()
            self._append_log(f"Queued job {job_name} (script: {script_display})")
        elif kind == "job_started":
            job_name = payload["name"]
            self.job_states[job_name] = {"status": "Running", "code": None}
            self._ensure_task_node(job_name)
            self._set_task_status(job_name, "running")
            self._append_task_log(job_name, "Running…")
            self._append_log(f"Running job {job_name}")
        elif kind == "job_completed":
            job_name = payload["name"]
            succeeded = payload.get("succeeded")
            status_key = "completed" if succeeded else "failed"
            return_code = payload.get("returncode")
            self.job_states[job_name] = {
                "status": "Completed" if succeeded else "Failed",
                "code": return_code,
            }
            self._set_task_status(job_name, status_key, code=return_code)
            self.job_completed = min(self.job_total, self.job_completed + 1)
            self._update_job_summary()
            message = (
                f"Job {job_name} {'succeeded' if succeeded else 'failed'} with code {return_code}"
            )
            self._append_task_log(job_name, message)
            self._append_log(message, error=not succeeded)
            stdout = (payload.get("stdout") or "").strip()
            stderr = (payload.get("stderr") or "").strip()
            if stdout:
                self._append_task_log(job_name, stdout)
                self._append_log(stdout)
            if stderr:
                self._append_task_log(job_name, stderr)
                self._append_log(stderr, error=not succeeded)
        elif kind == "job_failed":
            job_name = payload["name"]
            error_message = payload.get("error", "")
            self.job_states[job_name] = {"status": "Failed", "code": None}
            self._set_task_status(job_name, "failed")
            self.job_completed = min(self.job_total, self.job_completed + 1)
            self._update_job_summary()
            self._append_task_log(job_name, f"Failed: {error_message}")
            self._append_log(f"Job {job_name} failed: {error_message}", error=True)
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
    settings_loader: Callable[[Path], Settings],
    environment_builder: Callable[[Settings], Environment],
    runner_factory: Callable[[Settings], AutoCadRunner],
    coordinator_factory: Callable[[AutoCadRunner], AutoCadCoordinator],
    logger_factory_builder: Callable[[Settings], LoggerFactory],
    initial_project: Path | None = None,
) -> None:
    """Entry point used by the CLI to launch the GUI."""

    app = GuiApplication(
        settings_loader=settings_loader,
        environment_builder=environment_builder,
        runner_factory=runner_factory,
        coordinator_factory=coordinator_factory,
        logger_factory_builder=logger_factory_builder,
        initial_project=initial_project,
    )
    app.run()


__all__ = ["run_gui", "GuiApplication"]
