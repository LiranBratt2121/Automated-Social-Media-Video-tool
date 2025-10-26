import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import sys

from processing_logic import process_video_from_url

class StdoutRedirector:
    """A helper class to redirect stdout to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Tool")
        self.root.geometry("700x500")

        self.progress_queue = queue.Queue()

        # --- UI Elements ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # URL Input
        url_frame = ttk.LabelFrame(main_frame, text="Amazon Product Video URL", padding="10")
        url_frame.pack(fill=tk.X, pady=5)
        
        self.url_entry = ttk.Entry(url_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.url_entry.insert(0, "")

        self.generate_button = ttk.Button(url_frame, text="Generate Video", command=self.start_processing)
        self.generate_button.pack(side=tk.LEFT)

        # Progress and Status
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready. Paste a URL and click Generate.")
        self.status_label.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=100, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Log Output
        log_frame = ttk.LabelFrame(main_frame, text="Logs", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Redirect stdout to the log widget
        sys.stdout = StdoutRedirector(self.log_text)

        self.root.after(100, self.check_queue)

    def start_processing(self):
        """Starts the video generation in a separate thread to keep the GUI responsive."""
        url = self.url_entry.get()
        if not url:
            self.status_label.config(text="Please enter a URL.")
            return

        self.generate_button.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.log_text.delete('1.0', tk.END)

        # Run the long process in a thread
        self.thread = threading.Thread(target=process_video_from_url, args=(url, self.update_progress))
        self.thread.start()

    def update_progress(self, value, maximum, message):
        """Puts progress updates onto the queue to be handled by the main GUI thread."""
        self.progress_queue.put((value, maximum, message))

    def check_queue(self):
        """Checks the queue for progress updates and updates the GUI."""
        try:
            while True:
                value, maximum, message = self.progress_queue.get_nowait()
                self.progress_bar["maximum"] = maximum
                self.progress_bar["value"] = value
                self.status_label.config(text=message)
                
                # Re-enable button if process is complete or failed
                if value == maximum or "Error" in message:
                    self.generate_button.config(state=tk.NORMAL)

        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()