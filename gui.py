import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import sys
import os

class DownloaderGUI:
    def __init__(self, master):
        self.master = master
        master.title("Spotify Playlist Downloader")

        self.url_label = ttk.Label(master, text="Playlist URL:")
        self.url_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.url_entry = ttk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=5)

        self.limit_label = ttk.Label(master, text="Limit (optional):")
        self.limit_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.limit_entry = ttk.Entry(master, width=10)
        self.limit_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.start_button = ttk.Button(master, text="Start Download", command=self.start_download)
        self.start_button.grid(row=1, column=2, sticky="e", padx=5, pady=5)

        self.output = scrolledtext.ScrolledText(master, width=80, height=20, state="disabled")
        self.output.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

        master.grid_columnconfigure(1, weight=1)
        master.grid_rowconfigure(2, weight=1)

        self.process = None

    def append_output(self, text):
        self.output.configure(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state="disabled")

    def run_downloader(self, url, limit):
        cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "playlist_downloader.py"), url]
        if limit:
            cmd.extend(["--limit", str(limit)])
        self.append_output(f"Running: {' '.join(cmd)}\n")
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in self.process.stdout:
                self.append_output(line)
            self.process.wait()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.start_button.config(state="normal")
            self.append_output("Download finished.\n")
            self.process = None

    def start_download(self):
        url = self.url_entry.get().strip()
        limit = self.limit_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter a playlist URL")
            return
        self.start_button.config(state="disabled")
        thread = threading.Thread(target=self.run_downloader, args=(url, limit))
        thread.start()


def main():
    root = tk.Tk()
    app = DownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
