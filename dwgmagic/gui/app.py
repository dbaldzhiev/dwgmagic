"""CustomTkinter-based GUI runner for the DWGMAGIC pipeline with DnD and Preflight checks."""
from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Iterable, Mapping, Sequence, Any

import customtkinter as ctk
# TkinterDnD usage: we need to wrap the root window.
# ctk.CTk inherits from tk.Tk. We can try to use TkinterDnD.DnDWrapper 
# but TkinterDnD usually expects to initialize the Tk instance itself.
# A common workaround is using `TkinterDnD.Tk` instead of `ctk.CTk` 
# but that loses ctk styling on the root.
# However, newer customtkinter versions might coexist or we use the library 'tkinterdnd2'.
from tkinterdnd2 import TkinterDnD, DND_FILES

from jinja2 import Environment

from dwgmagic.core.context import ProjectConfig, ProjectContext
from dwgmagic.core.pipeline import PipelineRunner, PipelineStage
from dwgmagic.core.stages import build_default_stages
from dwgmagic.integrations.autocad import AutoCadCoordinator, AutoCadRunner
from dwgmagic.logger import LoggerFactory
from dwgmagic.settings import Settings
from dwgmagic.ui.progress import ProgressEvent, QueueProgressListener
from dwgmagic.trusted_folder import TrustedFolderChecker

# Configure CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class QueueLogHandler(logging.Handler):
    """Logging handler that forwards formatted records to the GUI queue."""

    def __init__(self, event_queue: "queue.Queue[ProgressEvent]") -> None:
        super().__init__()
        self.event_queue = event_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
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


class CtkTkinterDnD(ctk.CTk, TkinterDnD.DnDWrapper):
    """CustomTkinter root window with Drag & Drop support."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


class GuiApplication(CtkTkinterDnD):
    """Encapsulates the CustomTkinter user interface and pipeline orchestration."""

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
        super().__init__()

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

        # Preflight status
        self.preflight_autocad = tk.StringVar(value="Last Check: Pending")
        self.preflight_trusted = tk.StringVar(value="Last Check: Pending")
        self.preflight_autocad_color = tk.StringVar(value="gray")
        self.preflight_trusted_color = tk.StringVar(value="gray")

        # UI Setup
        self.title("DWGMAGIC Pipeline Monitor")
        self.geometry("1400x900")
        self.minsize(1000, 700)

        # Configure grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # State Variables
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
        self.after(100, self._process_events)
        self.after(500, self._run_preflight_checks)

        # Enable Drop on the window
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self._on_drop)

        if initial_project:
            try:
                self._load_project(initial_project)
            except Exception as exc: 
                messagebox.showerror("Project Load Failed", str(exc))

    def _new_context(self) -> ProjectContext:
        if not self.current_settings or not self.environment:
            raise RuntimeError("Project configuration has not been loaded")
        config = ProjectConfig(settings=self.current_settings, stages=self.stage_names)
        return ProjectContext(config=config, environment=self.environment)

    # UI construction -----------------------------------------------------
    def _build_layout(self) -> None:
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="DWGMAGIC", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Project Controls
        self.sidebar_label_1 = ctk.CTkLabel(
            self.sidebar_frame, text="Project Control", anchor="w", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.sidebar_label_1.grid(row=1, column=0, padx=20, pady=(10, 0))

        self.open_proj_btn = ctk.CTkButton(
            self.sidebar_frame, text="Open Project", command=self._choose_project
        )
        self.open_proj_btn.grid(row=2, column=0, padx=20, pady=10)
        # Hint for DnD
        ctk.CTkLabel(self.sidebar_frame, text="(or drop folder here)", font=ctk.CTkFont(size=10), text_color="gray").grid(row=3, column=0)

        self.project_display_label = ctk.CTkLabel(
            self.sidebar_frame,
            textvariable=self.project_var,
            font=ctk.CTkFont(size=12, slant="italic"),
            wraplength=200,
            text_color="gray70"
        )
        self.project_display_label.grid(row=4, column=0, padx=20, pady=(0, 20))

        self.run_button = ctk.CTkButton(
            self.sidebar_frame,
            text="Run Pipeline",
            command=self._start_pipeline,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.run_button.grid(row=5, column=0, padx=20, pady=10)
        self.run_button.configure(state="disabled")

        # Preflight Checks Section
        ctk.CTkLabel(
            self.sidebar_frame, text="Preflight Checks", anchor="w", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=6, column=0, padx=20, pady=(20, 10))

        self.check_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.check_frame.grid(row=7, column=0, padx=20, pady=0, sticky="ew")
        
        # AutoCAD Check
        ctk.CTkLabel(self.check_frame, text="AutoCAD:", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.lbl_acad_status = ctk.CTkLabel(self.check_frame, textvariable=self.preflight_autocad, font=("Segoe UI", 11))
        self.lbl_acad_status.pack(anchor="w", padx=(10, 0))
        
        # Trusted Check
        ctk.CTkLabel(self.check_frame, text="Trusted Path:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 0))
        self.lbl_trust_status = ctk.CTkLabel(self.check_frame, textvariable=self.preflight_trusted, font=("Segoe UI", 11))
        self.lbl_trust_status.pack(anchor="w", padx=(10, 0))

        # Spacer
        self.sidebar_spacer = ctk.CTkLabel(self.sidebar_frame, text="")
        self.sidebar_spacer.grid(row=8, column=0)

        # Appearance Mode
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=9, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["System", "Light", "Dark"],
            command=self._change_appearance_mode_event,
        )
        self.appearance_mode_optionemenu.grid(row=10, column=0, padx=20, pady=(10, 20))


        # --- Main Area ---
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_rowconfigure(2, weight=1) # Tabview expands
        self.main_content.grid_columnconfigure(0, weight=1)

        # 1. Header & Status
        self.status_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.status_label_header = ctk.CTkLabel(
            self.status_frame, text="Status:", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.status_label_header.pack(side="left", padx=(0, 10))
        
        self.status_label_val = ctk.CTkLabel(
            self.status_frame, textvariable=self.status_var, font=ctk.CTkFont(size=16)
        )
        self.status_label_val.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=20)
        self.progress_bar.set(0)

        # 2. Stages (Always Visible)
        ctk.CTkLabel(self.main_content, text="Pipeline Stages", font=ctk.CTkFont(size=14, weight="bold")).grid(row=1, column=0, sticky="w", pady=(0, 5))
        
        # Use a Frame to contain the Treeview to control size
        self.stages_container = ctk.CTkFrame(self.main_content, height=150)
        self.stages_container.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.stages_container.pack_propagate(False) # Respect height

        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure(
            "Treeview",
            background="#333333",
            foreground="white",
            fieldbackground="#333333",
            borderwidth=0,
            rowheight=25
        )
        self.style.map("Treeview", background=[("selected", "#1f538d")])
        self.style.configure(
            "Treeview.Heading", background="#555555", foreground="white", relief="flat"
        )

        self.stage_tree = ttk.Treeview(
            self.stages_container,
            columns=("stage", "status"),
            show="headings",
        )
        self.stage_tree.heading("stage", text="Stage Name")
        self.stage_tree.heading("status", text="Result")
        self.stage_tree.column("stage", width=400, anchor="w")
        self.stage_tree.column("status", width=200, anchor="w")
        
        stage_scroll_y = ctk.CTkScrollbar(self.stages_container, command=self.stage_tree.yview)
        self.stage_tree.configure(yscrollcommand=stage_scroll_y.set)
        stage_scroll_y.pack(side="right", fill="y")
        self.stage_tree.pack(side="left", fill="both", expand=True)


        # 3. Tabview (Tasks & Logs)
        self.tabview = ctk.CTkTabview(self.main_content)
        self.tabview.grid(row=3, column=0, sticky="nsew")
        self.tabview.add("Tasks")
        self.tabview.add("Logs")
        
        # -- Tasks Tab --
        self.tabview.tab("Tasks").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Tasks").grid_rowconfigure(0, weight=1)
        
        self.tasks_paned = tk.PanedWindow(self.tabview.tab("Tasks"), orient=tk.HORIZONTAL, sashwidth=4, bg="#2b2b2b")
        self.tasks_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left: Task Tree
        self.tree_frame = ctk.CTkFrame(self.tasks_paned)
        self.tasks_paned.add(self.tree_frame)
        self.tree_frame.pack_propagate(False)
        
        self.task_tree = ttk.Treeview(
            self.tree_frame,
            columns=("status", "code"),
            show="tree headings",
            selectmode="browse",
        )
        self.task_tree.heading("#0", text="Task")
        self.task_tree.heading("status", text="Status")
        self.task_tree.heading("code", text="Return Code")
        self.task_tree.column("#0", minwidth=300, stretch=True)
        self.task_tree.column("status", width=100, anchor="w")
        self.task_tree.column("code", width=80, anchor="center")
        
        self.tree_scroll_y = ctk.CTkScrollbar(self.tree_frame, command=self.task_tree.yview)
        self.tree_scroll_x = ctk.CTkScrollbar(self.tree_frame, orientation="horizontal", command=self.task_tree.xview)
        self.task_tree.configure(yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set)
        
        self.tree_scroll_y.pack(side="right", fill="y")
        self.tree_scroll_x.pack(side="bottom", fill="x")
        self.task_tree.pack(fill="both", expand=True)
        
        self.task_tree.bind("<<TreeviewSelect>>", self._on_task_selected)

        # Right: Task Details
        self.details_frame = ctk.CTkFrame(self.tasks_paned)
        self.tasks_paned.add(self.details_frame)
        
        # Details Header
        self.details_header = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        self.details_header.pack(fill="x", padx=10, pady=10)
        
        # Name
        self.lbl_det_name = ctk.CTkLabel(self.details_header, text="Task:", font=("Segoe UI", 12, "bold"))
        self.lbl_det_name.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.detail_name_var = tk.StringVar(value="-")
        ctk.CTkLabel(self.details_header, textvariable=self.detail_name_var).grid(row=0, column=1, sticky="w")
        
        # Status
        self.lbl_det_status = ctk.CTkLabel(self.details_header, text="Status:", font=("Segoe UI", 12, "bold"))
        self.lbl_det_status.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.detail_status_var = tk.StringVar(value="-")
        ctk.CTkLabel(self.details_header, textvariable=self.detail_status_var).grid(row=1, column=1, sticky="w")
        
        # Code
        self.lbl_det_code = ctk.CTkLabel(self.details_header, text="Exit Code:", font=("Segoe UI", 12, "bold"))
        self.lbl_det_code.grid(row=2, column=0, sticky="w", padx=(0, 10))
        self.detail_code_var = tk.StringVar(value="-")
        ctk.CTkLabel(self.details_header, textvariable=self.detail_code_var).grid(row=2, column=1, sticky="w")
        
        # Output Log for Task
        ctk.CTkLabel(self.details_frame, text="Task Output Log:", anchor="w").pack(fill="x", padx=10)
        self.task_log = ctk.CTkTextbox(self.details_frame, wrap="word")
        self.task_log.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        self.task_log.configure(state="disabled")

        # -- Logs Tab --
        self.tabview.tab("Logs").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Logs").grid_rowconfigure(0, weight=1)
        self.log_widget = ctk.CTkTextbox(self.tabview.tab("Logs"), wrap="word", font=("Consolas", 12))
        self.log_widget.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_widget.configure(state="disabled")
        
        self._configure_status_tags(self.stage_tree)
        self._configure_status_tags(self.task_tree)

    def _change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)


    def _run_preflight_checks(self):
        """Runs preflight checks in a background thread."""
        def _check():
            # 1. Check AutoCAD
            try:
                # We need a temporary Runner. We don't have settings loaded necessarily,
                # but we can try to find AutoCAD with default logic or just check PATH/Registry if settings not loaded.
                # However, AutoCadRunner needs Settings.
                # Let's try to load settings from a dummy path or just search common paths manually?
                # Actually, main.py passes a runner_factory that needs settings.
                # We can try to use a default settings object if we can create one without a project.
                # But Settings usually requires a project path.
                # Alternative: Just check for typical executables.
                
                # If we have a project loaded, we use its settings. If not, we can't reliably know WHERE to look 
                # strictly, but we can try to just check environment variable or PATH.
                
                # For now, let's just say "Pending Project Load" if no project is loaded, 
                # OR we try to run 'accoreconsole' from PATH.
                
                import shutil
                if shutil.which("accoreconsole.exe"):
                    self.event_queue.put(ProgressEvent("preflight", {"check": "autocad", "status": "Found in PATH", "ok": True}))
                else:
                     self.event_queue.put(ProgressEvent("preflight", {"check": "autocad", "status": "Not in PATH", "ok": False}))
            except Exception as e:
                self.event_queue.put(ProgressEvent("preflight", {"check": "autocad", "status": f"Error: {e}", "ok": False}))

            # 2. Trusted Path
            # This requires a project to be loaded to know which script to run.
            # So we will update this when project loads.
            self.event_queue.put(ProgressEvent("preflight", {"check": "trusted", "status": "Requires Project", "ok": False}))

        threading.Thread(target=_check, daemon=True).start()

    def _run_project_checks(self, settings: Settings):
        """Runs checks that depend on the project settings."""
        def _check():
            # 1. Re-check AutoCAD with settings
            try:
                runner = self.runner_factory(settings)
                try:
                    exe = runner.discover()
                    self.event_queue.put(ProgressEvent("preflight", {"check": "autocad", "status": f"Found: {exe.name}", "ok": True}))
                except Exception:
                     self.event_queue.put(ProgressEvent("preflight", {"check": "autocad", "status": "Not Found", "ok": False}))
                     return

                # 2. Trusted Path
                checker = TrustedFolderChecker(runner)
                try:
                    # We need a logger.
                    # We can use a dummy logger or the app's logger logic.
                    # The logger factory needs settings.
                    # We can use a simple print logger for this check or create a temporary one.
                    # But the check() method expects a standard python logger object mainly.
                    import logging
                    dummy = logging.getLogger("Preflight")
                    checker.check(settings, dummy)
                    self.event_queue.put(ProgressEvent("preflight", {"check": "trusted", "status": "OK", "ok": True}))
                except Exception as e:
                    self.event_queue.put(ProgressEvent("preflight", {"check": "trusted", "status": f"Failed: {e}", "ok": False}))

            except Exception as e:
                self.event_queue.put(ProgressEvent("preflight", {"check": "autocad", "status": f"Error: {e}", "ok": False}))

        threading.Thread(target=_check, daemon=True).start()

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if not paths:
            return
        # Take the first path
        path_str = paths[0]
        path = Path(path_str)
        if path.is_dir():
            try:
                self._load_project(path.resolve())
            except Exception as exc:
                messagebox.showerror("Project Load Failed", str(exc))
        else:
             messagebox.showinfo("Drop Folder", "Please drop a project folder, not a file.")

    def _reset_stage_table(self) -> None:
        for row in self.stage_tree.get_children():
            self.stage_tree.delete(row)
        if not self.stage_names:
            self.progress_bar.set(0)
        for name in self.stage_names:
            self.stage_tree.insert(
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

    def _ensure_stage_row(self, name: str) -> None:
        if not self.stage_tree.exists(name):
            self.stage_tree.insert(
                "",
                tk.END,
                iid=name,
                values=(self._display_name(name), "Pending"),
                tags=(self._status_tag("pending"),),
            )

    def _configure_status_tags(self, widget: ttk.Treeview) -> None:
        for key, color in [("pending", "gray"), ("running", "orange"), ("completed", "green"), ("failed", "red")]:
             widget.tag_configure(self._status_tag(key), foreground=color)

    def _status_tag(self, status: str) -> str:
        return f"status:{status}"

    def _set_stage_status(self, name: str, status: str) -> None:
        normalised = status.lower()
        display = status.capitalize()
        self.stage_tree.item(
            name,
            values=(self._display_name(name), display),
            tags=(self._status_tag(normalised),),
        )
        # Ensure visible
        self.stage_tree.see(name)

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
        self._append_log(f"Loaded project at {project_root}")
        self.run_button.configure(state="normal")
        
        # Trigger project-specific checks
        self.preflight_autocad.set("Checking...")
        self.preflight_trusted.set("Checking...")
        self.lbl_acad_status.configure(text_color="white")
        self.lbl_trust_status.configure(text_color="white")
        self._run_project_checks(settings)

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
            self._refresh_task_log(job_name)
            return
        self.detail_name_var.set(info.get("title") or job_name)
        status = info.get("status", "pending").capitalize()
        self.detail_status_var.set(status)
        code = info.get("code")
        self.detail_code_var.set("—" if code is None else str(code))
        self._refresh_task_log(job_name)

    def _refresh_task_log(self, job_name: str) -> None:
        self.task_log.configure(state="normal")
        self.task_log.delete("1.0", tk.END)
        for line in self.job_logs.get(job_name, []):
            self.task_log.insert(tk.END, line + "\n")
        self.task_log.configure(state="disabled")

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
        self.run_button.configure(state="disabled")
        self.status_var.set("Preparing pipeline...")
        self._reset_stage_table()
        self._reset_task_tree()
        self._append_log("Starting pipeline run...")

        self.context = self._new_context()
        self.context.set("autocad_listener", self.listener)
        
        # Ensure Tasks is selected
        self.tabview.set("Tasks")

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
        self.after(100, self._process_events)

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
            
            # Update global progress
            total_stages = len(self.stage_names)
            if total_stages > 0:
                self.progress_bar.set(self.completed_stages / total_stages)
                
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
            self.progress_bar.set(1.0)
            self.run_button.configure(state="normal")
        elif kind == "pipeline_error":
            self.status_var.set("Pipeline crashed")
            self._append_log(f"Pipeline crashed: {payload['error']}", error=True)
            self.run_button.configure(state="normal")
        elif kind == "pipeline_thread_complete":
            self._running = False
            self.run_button.configure(state="normal")
        elif kind == "job_queued":
            job_name = payload["name"]
            script_path = payload.get("script") or ""
            script_display = Path(script_path).name if script_path else "—"
            self.job_states[job_name] = {"status": "Queued", "code": None}
            self.job_total += 1
            self._ensure_task_node(job_name)
            self._set_task_status(job_name, "queued", script=script_display)
            self._append_task_log(job_name, f"Queued (script: {script_display})")
            # self._update_job_summary()
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
            # self._update_job_summary()
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
            # self._update_job_summary()
            self._append_task_log(job_name, f"Failed: {error_message}")
            self._append_log(f"Job {job_name} failed: {error_message}", error=True)
        elif kind == "log":
            level = payload.get("level", "INFO")
            message = payload.get("message", "")
            tag = level.upper()
            error = level.upper() in {"ERROR", "CRITICAL"}
            self._append_log(f"[{tag}] {message}", error=error)
        
        elif kind == "preflight":
             check = payload["check"]
             status = payload["status"]
             ok = payload["ok"]
             color = "green" if ok else "red"
             if check == "autocad":
                 self.preflight_autocad.set(status)
                 self.lbl_acad_status.configure(text_color=color)
             elif check == "trusted":
                 self.preflight_trusted.set(status)
                 self.lbl_trust_status.configure(text_color=color)

    def _append_log(self, message: str, *, error: bool = False) -> None:
        self.log_widget.configure(state="normal")
        self.log_widget.insert(tk.END, message + "\n")
        self.log_widget.see(tk.END)
        self.log_widget.configure(state="disabled")

    def run(self) -> None:
        self.mainloop()


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
