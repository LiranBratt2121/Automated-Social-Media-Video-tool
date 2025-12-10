import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog  # Added filedialog
import threading
import queue
import sys

# Note: We renamed the function in the logic file to process_video
from processing_logic import process_video 

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
        self.root.geometry("750x500") # Slightly wider for the extra button

        self.progress_queue = queue.Queue()

        # --- UI Elements ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input Area
        url_frame = ttk.LabelFrame(main_frame, text="Input Source (Amazon URL or Local Video File)", padding="10")
        url_frame.pack(fill=tk.X, pady=5)
        
        self.input_entry = ttk.Entry(url_frame, width=50)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.insert(0, "")

        # Browse Button
        self.browse_button = ttk.Button(url_frame, text="Browse File", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=(0, 5))

        # Generate Button
        self.generate_button = ttk.Button(url_frame, text="Generate Video", command=self.start_processing)
        self.generate_button.pack(side=tk.LEFT)

        # Progress and Status
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready. Paste a URL or select a file.")
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

    def browse_file(self):
        """Opens a file dialog to select a video file."""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv"), ("All Files", "*.*")]
        )
        if file_path:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, file_path)

    def start_processing(self):
        """Starts the video generation in a separate thread."""
        input_source = self.input_entry.get()
        if not input_source:
            self.status_label.config(text="Please enter a URL or select a file.")
            return

        self.generate_button.config(state=tk.DISABLED)
        self.browse_button.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.log_text.delete('1.0', tk.END)

        # Run the long process in a thread
        self.thread = threading.Thread(target=process_video, args=(input_source, self.update_progress))
        self.thread.start()

    def update_progress(self, value, maximum, message):
        """Puts progress updates onto the queue."""
        self.progress_queue.put((value, maximum, message))

    def check_queue(self):
        """Checks the queue for progress updates."""
        try:
            while True:
                value, maximum, message = self.progress_queue.get_nowait()
                self.progress_bar["maximum"] = maximum
                self.progress_bar["value"] = value
                self.status_label.config(text=message)
                
                # Re-enable buttons if process is complete or failed
                if value == maximum or "Error" in message:
                    self.generate_button.config(state=tk.NORMAL)
                    self.browse_button.config(state=tk.NORMAL)

        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()