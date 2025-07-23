import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pydub import AudioSegment
import simpleaudio as sa
import shutil

class MusicEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Music Enhancer with AudioSR")
        self.root.geometry("480x650")

        self.label = tk.Label(root, text="Select an audio file (.wav, .mp3, .mp4)", font=("Helvetica", 14))
        self.label.pack(pady=10)

        self.select_btn = tk.Button(root, text="Select File", command=self.select_file)
        self.select_btn.pack(pady=5)

        self.enhance_btn = tk.Button(root, text="Enhance (dummy)", state=tk.DISABLED)  # Not connected in this minimal example
        self.enhance_btn.pack(pady=5)

        self.upscale_btn = tk.Button(root, text="Upscale with AudioSR", command=self.upscale_audio, state=tk.DISABLED)
        self.upscale_btn.pack(pady=5)

        self.status = tk.Label(root, text="", fg="green")
        self.status.pack(pady=10)

        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(pady=10, fill='x', padx=20)

        self.input_file = None

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.mp4")])
        if not file_path:
            return
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".wav":
            self.input_file = file_path
        elif ext == ".mp3":
            audio = AudioSegment.from_mp3(file_path)
            wav_path = file_path + ".converted.wav"
            audio.export(wav_path, format="wav")
            self.input_file = wav_path
        elif ext == ".mp4":
            audio = AudioSegment.from_file(file_path, format="mp4")
            wav_path = file_path + ".converted.wav"
            audio.export(wav_path, format="wav")
            self.input_file = wav_path
        else:
            messagebox.showerror("Invalid file", "Unsupported format.")
            return
        self.status.config(text=f"Selected: {os.path.basename(self.input_file)}")
        self.upscale_btn.config(state=tk.NORMAL)

    def upscale_audio(self):
        try:
            import torch
            import torchaudio
            from audiosr import build_model, super_resolution

            source_path = self.input_file
            if not source_path or not os.path.exists(source_path):
                messagebox.showerror("Upscaling Error", "No audio file found.")
                return

            waveform, sr = torchaudio.load(source_path)
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            self.status.config(text="Loading AudioSR...", fg="blue")
            self.progress.start()
            self.root.update()

            model = build_model(model_name="basic")

            self.status.config(text="Upscaling...", fg="blue")
            self.root.update()

            upscaled = super_resolution(
                model,
                waveform,
                guidance_scale=3.5,
                ddim_steps=50
            )

            out_path = os.path.splitext(source_path)[0] + "_upscaled_48khz.wav"
            torchaudio.save(out_path, upscaled, 48000)

            self.status.config(text="Upscaled audio saved.", fg="green")
            messagebox.showinfo("Upscaled", f"Upscaled audio saved at:\n{out_path}")

        except Exception as e:
            messagebox.showerror("Upscaling Failed", str(e))
            self.status.config(text="Upscaling failed.", fg="red")
        finally:
            self.progress.stop()

if __name__ == '__main__':
    root = tk.Tk()
    app = MusicEnhancerApp(root)
    root.mainloop()
