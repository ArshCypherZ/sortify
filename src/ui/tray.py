import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import subprocess
import sys
import queue
from pathlib import Path
from src.config.settings import settings, save_settings
from src.utils.logger import logger
from src.i18n.strings import Strings

# Try importing notification, but don't crash if missing
try:
    from plyer import notification
except ImportError:
    notification = None

class ProgressDialog(tk.Toplevel):
    """Progress bar dialog for Atlas scanning."""
    def __init__(self, parent, title="Initializing..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x120")
        self.transient(parent)
        self.resizable(False, False)
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 120) // 2
        self.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(self, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        self.label = ttk.Label(frame, text="Scanning folders...", font=("Arial", 10))
        self.label.pack(fill=tk.X)
        
        self.progress = ttk.Progressbar(frame, length=350, mode='determinate')
        self.progress.pack(pady=10, fill=tk.X)
        
        self.status = ttk.Label(frame, text="", font=("Arial", 9))
        self.status.pack(fill=tk.X)
        
        # Prevent closing
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
    def update_progress(self, current: int, total: int, message: str):
        """Update progress bar. Call from main thread."""
        if total > 0:
            self.progress['value'] = (current / total) * 100
        self.status.config(text=message)
        self.update_idletasks()
        
    def close(self):
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sortify Settings")
        self.geometry("600x400")
        self.parent = parent
        
        self.watch_dirs = list(settings.WATCH_DIRECTORIES)
        self.model_type = tk.StringVar(value=settings.MODEL_TYPE)

        self._create_widgets()
        
    def _create_widgets(self):
        tabs = ttk.Notebook(self)
        tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Folders
        frame_folders = ttk.Frame(tabs)
        tabs.add(frame_folders, text="Watch Folders")
        
        # Listbox
        self.lst_folders = tk.Listbox(frame_folders)
        self.lst_folders.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for p in self.watch_dirs:
            self.lst_folders.insert(tk.END, str(p))
            
        # Buttons
        btn_frame = ttk.Frame(frame_folders)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Add Folder", command=self._add_folder).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Remove Selected", command=self._remove_folder).pack(side=tk.LEFT, padx=5)

        # Tab 2: Model Settings
        frame_ai = ttk.Frame(tabs)
        tabs.add(frame_ai, text="Model Configuration")
        
        ttk.Label(frame_ai, text="Model Provider:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        ttk.Radiobutton(frame_ai, text="Local Models", variable=self.model_type, value="local").pack(anchor=tk.W, padx=20)
        
        # Save Button Area
        frame_actions = ttk.Frame(self)
        frame_actions.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(frame_actions, text="Save & Restart", command=self._save).pack(side=tk.RIGHT)
        ttk.Button(frame_actions, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _add_folder(self):
        path = filedialog.askdirectory()
        if path:
            if path not in [str(p) for p in self.watch_dirs]:
                self.watch_dirs.append(Path(path))
                self.lst_folders.insert(tk.END, path)

    def _remove_folder(self):
        selection = self.lst_folders.curselection()
        if selection:
            idx = selection[0]
            self.lst_folders.delete(idx)
            del self.watch_dirs[idx]

    def _save(self):
        new_conf = {
            "WATCH_DIRECTORIES": [str(p) for p in self.watch_dirs],
            "MODEL_TYPE": self.model_type.get()
        }
        
        save_settings(new_conf)
        messagebox.showinfo("Settings Saved", "Configuration saved.\nPlease restart Sortify for changes to take effect.")
        self.destroy()

class SortifyUI:
    def __init__(self, processor, stop_callback, headless: bool = False):
        self.processor = processor
        self.stop_callback = stop_callback
        self.headless = headless
        self.root = None
        self.paused = False
        self.log_queue = queue.Queue()

    def _on_open_logs(self):
        log_file = settings.LOG_FILE
        if log_file.exists():
            subprocess.call(["xdg-open", str(log_file)])

    def _on_open_folder(self):
        folder = settings.WATCH_DIRECTORIES[0]
        if folder.exists():
             subprocess.call(["xdg-open", str(folder)])

    def _on_settings(self):
        SettingsDialog(self.root)

    def _toggle_pause(self):
        self.paused = not self.paused
        if self.processor:
             if self.paused:
                 self.processor.pause()
                 self.btn_pause.config(text=Strings.MENU_RESUME.value)
                 self.lbl_status.config(text="Status: PAUSED", foreground="red")
             else:
                 logger.info("Setting button text to Pause")
                 self.processor.resume()
                 self.btn_pause.config(text=Strings.MENU_PAUSE.value)
                 self.lbl_status.config(text="Status: RUNNING", foreground="green")

    def _on_exit(self):
        if self.root:
            self.root.destroy()
        self.stop_callback()

    def notify(self, title: str, message: str):
        # 1. Send to system notification if available
        if notification:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name=settings.APP_NAME,
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Notification error: {e}")
        
        # 2. Add to local log window (via queue to be thread safe)
        if not self.headless:
            self.log_queue.put(f"[{title}] {message}")

    def _update_ui(self):
        """Polls queue for UI updates on main thread."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.txt_log.configure(state='normal')
                self.txt_log.insert(tk.END, msg + "\n")
                self.txt_log.see(tk.END)
                self.txt_log.configure(state='disabled')
                self.log_queue.task_done()
        except queue.Empty:
            pass
        
        # Schedule next update
        if self.root:
            self.root.after(500, self._update_ui)

    def run(self):
        if self.headless:
            logger.info("Running in headless mode (CLI only).")
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self._on_exit()
            return

        # Setup Main Window
        self.root = tk.Tk()
        self.root.title(f"{settings.APP_NAME} Control Panel")
        self.root.geometry("600x400")
        
        # Main Frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status Section
        self.lbl_status = ttk.Label(main_frame, text="Status: RUNNING", foreground="green", font=("Arial", 12, "bold"))
        self.lbl_status.pack(pady=(0, 10))

        # Controls Section
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.btn_pause = ttk.Button(btn_frame, text=Strings.MENU_PAUSE.value, command=self._toggle_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=5)
        
        btn_logs = ttk.Button(btn_frame, text=Strings.MENU_OPEN_LOGS.value, command=self._on_open_logs)
        btn_logs.pack(side=tk.LEFT, padx=5)
        
        btn_folder = ttk.Button(btn_frame, text=Strings.MENU_OPEN_FOLDER.value, command=self._on_open_folder)
        btn_folder.pack(side=tk.LEFT, padx=5)
        
        # Settings Button
        btn_settings = ttk.Button(btn_frame, text="Settings", command=self._on_settings)
        btn_settings.pack(side=tk.RIGHT, padx=5)

        # Activity Log Section
        lbl_log = ttk.Label(main_frame, text="Recent Activity:", font=("Arial", 10))
        lbl_log.pack(anchor=tk.W, pady=(10, 5))
        
        self.txt_log = scrolledtext.ScrolledText(main_frame, height=8, state='disabled', font=("Consolas", 9))
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Initial fake log
        self.log_queue.put("Sortify started. Waiting for files...")
        context_count = len(settings.CATEGORY_MAP)
        self.log_queue.put(f"Context Awareness: {context_count} active category mappings.")

        # Start Polling
        self.root.after(500, self._update_ui)
        
        # Handle Window Close
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)
        
        # Start Loop
        self.root.mainloop()
