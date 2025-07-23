import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pydub import AudioSegment
import simpleaudio as sa
import subprocess

class MusicEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Music Enhancer with Demucs")
        self.root.geometry("400x500")

        self.label = tk.Label(root, text="Select an audio file (.wav, .mp3, .mp4)", font=("Helvetica", 14))
        self.label.pack(pady=10)

        self.select_btn = tk.Button(root, text="Select File", command=self.select_file)
        self.select_btn.pack(pady=5)

        self.enhance_btn = tk.Button(root, text="Enhance with Demucs", command=self.enhance, state=tk.DISABLED)
        self.enhance_btn.pack(pady=5)

        self.play_original_btn = tk.Button(root, text="Play Original", command=self.play_original, state=tk.DISABLED)
        self.play_original_btn.pack(pady=5)

        self.stop_original_btn = tk.Button(root, text="Stop Original", command=self.stop_original, state=tk.DISABLED)
        self.stop_original_btn.pack(pady=5)

        self.play_enhanced_btn = tk.Button(root, text="Play Enhanced", command=self.play_enhanced, state=tk.DISABLED)
        self.play_enhanced_btn.pack(pady=5)

        self.stop_enhanced_btn = tk.Button(root, text="Stop Enhanced", command=self.stop_enhanced, state=tk.DISABLED)
        self.stop_enhanced_btn.pack(pady=5)

        self.export_btn = tk.Button(root, text="Export as MP3/FLAC", command=self.export_audio, state=tk.DISABLED)
        self.export_btn.pack(pady=5)

        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(pady=10, fill='x', padx=20)

        self.status = tk.Label(root, text="", fg="green")
        self.status.pack(pady=10)

        self.input_file = None
        self.output_file = None
        self.original_play_obj = None
        self.enhanced_play_obj = None

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.mp4")])
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()

            if ext == ".mp3":
                audio = AudioSegment.from_mp3(file_path)
            elif ext == ".mp4":
                audio = AudioSegment.from_file(file_path, format="mp4")
            elif ext == ".wav":
                self.input_file = file_path
                self.update_ui_after_select()
                return
            else:
                messagebox.showerror("Invalid file", "Unsupported format.")
                return

            wav_path = file_path + ".converted.wav"
            audio.export(wav_path, format="wav")
            self.input_file = wav_path
            self.update_ui_after_select()

    def update_ui_after_select(self):
        self.status.config(text=f"Selected: {os.path.basename(self.input_file)}")
        self.enhance_btn.config(state=tk.NORMAL)
        self.play_original_btn.config(state=tk.NORMAL)
        self.stop_original_btn.config(state=tk.NORMAL)

    def enhance(self):
        try:
            self.status.config(text="Enhancing using Demucs...", fg="blue")
            self.progress.start()
            self.root.update()

            command = ["demucs", "-n", "htdemucs", self.input_file]
            subprocess.run(command, check=True)

            # Locate the output recombined.wav file
            basename = os.path.splitext(os.path.basename(self.input_file))[0]
            out_dir = os.path.join("separated", "htdemucs", basename)
            recombined_path = os.path.join(out_dir, "recombined.wav")

            if os.path.exists(recombined_path):
                self.output_file = os.path.abspath("enhanced_output.wav")
                shutil.copyfile(recombined_path, self.output_file)

                self.status.config(text=f"Enhanced file saved.", fg="green")
                self.play_enhanced_btn.config(state=tk.NORMAL)
                self.stop_enhanced_btn.config(state=tk.NORMAL)
                self.export_btn.config(state=tk.NORMAL)
                messagebox.showinfo("Done", f"Enhanced audio saved as:\n{self.output_file}")
            else:
                raise Exception("Recombined output not found.")
        except Exception as e:
            messagebox.showerror("Enhancement Error", str(e))
            self.status.config(text="Enhancement failed", fg="red")
        finally:
            self.progress.stop()

    def export_audio(self):
        if not self.output_file:
            messagebox.showwarning("Export", "No enhanced audio to export.")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".mp3",
                                                   filetypes=[("MP3", "*.mp3"), ("FLAC", "*.flac")])
        if export_path:
            try:
                audio = AudioSegment.from_wav(self.output_file)
                ext = os.path.splitext(export_path)[1].lower()
                audio.export(export_path, format="mp3" if ext == ".mp3" else "flac")
                messagebox.showinfo("Exported", f"Exported successfully to:\n{export_path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def play_original(self):
        try:
            if self.original_play_obj:
                self.original_play_obj.stop()
            wave_obj = sa.WaveObject.from_wave_file(self.input_file)
            self.original_play_obj = wave_obj.play()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_original(self):
        if self.original_play_obj:
            self.original_play_obj.stop()

    def play_enhanced(self):
        try:
            if self.enhanced_play_obj:
                self.enhanced_play_obj.stop()
            wave_obj = sa.WaveObject.from_wave_file(self.output_file)
            self.enhanced_play_obj = wave_obj.play()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_enhanced(self):
        if self.enhanced_play_obj:
            self.enhanced_play_obj.stop()


if __name__ == '__main__':
    root = tk.Tk()
    app = MusicEnhancerApp(root)
    root.mainloop()
