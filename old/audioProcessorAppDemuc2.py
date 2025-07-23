import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import shutil

OUTPUT_DIR = "enhanced_audio"

def run_demucs(input_path, log_widget):
    def log(text):
        log_widget.insert(tk.END, text + '\n')
        log_widget.see(tk.END)

    log_widget.delete(1.0, tk.END)
    log(f"Enhancing: {input_path}")

    try:
        process = subprocess.Popen(
            ["demucs", "-n", "htdemucs", input_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            log(line.strip())

        process.wait()

        filename = os.path.basename(input_path)
        name, _ = os.path.splitext(filename)
        enhanced_path = os.path.join("separated", "htdemucs", name)

        if os.path.exists(enhanced_path):
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            vocals_path = os.path.join(enhanced_path, "vocals.wav")
            enhanced_mp3_path = os.path.join(OUTPUT_DIR, f"{name}_enhanced.mp3")

            # Convert to MP3 using ffmpeg
            if os.path.exists(vocals_path):
                try:
                    subprocess.run([
                        "ffmpeg", "-y", "-i", vocals_path, "-codec:a", "libmp3lame", enhanced_mp3_path
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    log(f"Saved enhanced MP3: {enhanced_mp3_path}")
                except Exception as e:
                    log(f"ffmpeg conversion error: {e}")
            else:
                log("vocals.wav not found in Demucs output.")
        else:
            log("Enhanced output directory not found.")
    except Exception as e:
        log(f"Error: {str(e)}")

def browse_file(entry):
    filepath = filedialog.askopenfilename(
        filetypes=[("Audio/Video Files", "*.mp3 *.wav *.flac *.m4a *.mp4")]
    )
    if filepath:
        entry.delete(0, tk.END)
        entry.insert(0, filepath)

def start_enhancement(entry, log_widget):
    input_path = entry.get()
    if not input_path or not os.path.exists(input_path):
        messagebox.showerror("Error", "Please select a valid file.")
        return

    threading.Thread(target=run_demucs, args=(input_path, log_widget), daemon=True).start()

def main():
    root = tk.Tk()
    root.title("Audio Enhancer (Demucs)")
    root.geometry("650x450")

    tk.Label(root, text="Select Audio/Video File:").pack(pady=5)
    entry = tk.Entry(root, width=70)
    entry.pack(padx=10)
    tk.Button(root, text="Browse", command=lambda: browse_file(entry)).pack(pady=5)

    tk.Button(root, text="Enhance Audio", command=lambda: start_enhancement(entry, log)).pack(pady=10)

    log = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20)
    log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    root.mainloop()

if __name__ == "__main__":
    main()
