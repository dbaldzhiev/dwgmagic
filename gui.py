import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import os
import main as core
import config as cfg

def launch():
    app = Application()
    app.mainloop()

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DWGMAGIC")
        self.geometry("600x400")

        self.path_var = tk.StringVar()
        tk.Label(self, text="Project Directory:").pack(pady=5)
        path_frame = tk.Frame(self)
        path_frame.pack(fill='x', padx=10)
        tk.Entry(path_frame, textvariable=self.path_var, width=50).pack(side='left', expand=True, fill='x')
        tk.Button(path_frame, text="Browse", command=self.browse).pack(side='left', padx=5)

        self.log_var = tk.StringVar(value="logs")
        tk.Label(self, text="Log Directory:").pack(pady=5)
        log_frame = tk.Frame(self)
        log_frame.pack(fill='x', padx=10)
        tk.Entry(log_frame, textvariable=self.log_var, width=50).pack(side='left', expand=True, fill='x')
        tk.Button(log_frame, text="Browse", command=self.browse_log).pack(side='left', padx=5)

        self.verbose_var = tk.BooleanVar()
        tk.Checkbutton(self, text="Verbose", variable=self.verbose_var).pack(pady=5)

        self.run_button = tk.Button(self, text="Run", command=self.run)
        self.run_button.pack(pady=10)

        self.output = scrolledtext.ScrolledText(self, height=10, state='disabled')
        self.output.pack(fill='both', expand=True, padx=10, pady=5)

    def browse(self):
        directory = filedialog.askdirectory()
        if directory:
            self.path_var.set(directory)

    def browse_log(self):
        directory = filedialog.askdirectory()
        if directory:
            self.log_var.set(directory)

    def run(self):
        path = self.path_var.get()
        if not path:
            messagebox.showerror("Error", "Please select a directory")
            return
        self.run_button.config(state='disabled')
        self.output.configure(state='normal')
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "Running DWGMAGIC...\n")
        self.output.configure(state='disabled')
        threading.Thread(target=self.worker, args=(path,), daemon=True).start()

    def worker(self, path):
        try:
            core.main(path, self.verbose_var.get(), self.log_var.get())
            log_path = os.path.join(path, self.log_var.get(), 'acclog.log')
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding=cfg.log_encoding, errors='replace') as f:
                    logs = f.read()
            else:
                logs = 'No log file found.'
            self.after(0, lambda: self.show_logs(logs))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror('Error', str(exc)))
            self.after(0, lambda: self.run_button.config(state='normal'))

    def show_logs(self, logs):
        self.output.configure(state='normal')
        self.output.insert(tk.END, logs)
        self.output.see(tk.END)
        self.output.configure(state='disabled')
        self.run_button.config(state='normal')
        messagebox.showinfo('Completed', 'DWGMAGIC completed successfully')
