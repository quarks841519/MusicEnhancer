import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pydub import AudioSegment
from voicefixer import VoiceFixer
import subprocess
import onnxruntime
import soundfile as sf
import numpy as np
import scipy.signal
import simpleaudio as sa

# --- AudioSR Upsampling Function ---
def upsample_audiosr(input_wav):
    output_path = input_wav.replace(".wav", "_upsampled.wav")

    audio, sr = sf.read(input_wav)
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)

    resampled_audio = scipy.signal.resample_poly(audio, 16000, sr)
    session = onnxruntime.InferenceSession("models/audiosr/audiosr-medium.onnx", providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    input_audio = resampled_audio[:16000 * 10]
    input_audio = input_audio.astype(np.float32)[np.newaxis, np.newaxis, :]

    output_audio = session.run([output_name], {input_name: input_audio})[0][0, 0]
    sf.write(output_path, output_audio, 48000)
    return output_path

# --- Setup GUI ---
class MusicEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Music Enhancer")
        self.root.geometry("400x480")

        self.label = tk.Label(root, text="Select a music file (.wav or .mp3)", font=("Helvetica", 14))
        self.label.pack(pady=10)

        self.select_btn = tk.Button(root, text="Select File", command=self.select_file)
        self.select_btn.pack(pady=5)

        self.enhance_btn = tk.Button(root, text="Enhance with VoiceFixer", command=self.enhance, state=tk.DISABLED)
        self.enhance_btn.pack(pady=5)

        self.sr_btn = tk.Button(root, text="Upsample to 48kHz", command=self.upsample, state=tk.DISABLED)
        self.sr_btn.pack(pady=5)

        self.play_original_btn = tk.Button(root, text="Play Original", command=self.play_original, state=tk.DISABLED)
        self.play_original_btn.pack(pady=5)

        self.play_enhanced_btn = tk.Button(root, text="Play Enhanced", command=self.play_enhanced, state=tk.DISABLED)
        self.play_enhanced_btn.pack(pady=5)

        self.export_btn = tk.Button(root, text="Export as FLAC/MP3", command=self.export_audio, state=tk.DISABLED)
        self.export_btn.pack(pady=5)

        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(pady=10, fill='x', padx=20)

        self.status = tk.Label(root, text="", fg="green")
        self.status.pack(pady=10)

        self.input_file = None
        self.output_file = None

    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.mp4")])
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()

            if ext == ".mp3":
                audio = AudioSegment.from_mp3(file_path)
                wav_path = file_path.replace(".mp3", ".wav")
                audio.export(wav_path, format="wav")
                self.input_file = wav_path

            elif ext == ".mp4":
                try:
                    audio = AudioSegment.from_file(file_path, format="mp4")
                    wav_path = file_path.replace(".mp4", ".wav")
                    audio.export(wav_path, format="wav")
                    self.input_file = wav_path
                except Exception as e:
                    messagebox.showerror("MP4 Error", f"Failed to extract audio from MP4:\n{e}")
                    return

            else:  # Assuming it's .wav
                self.input_file = file_path

            self.status.config(text=f"Selected: {os.path.basename(self.input_file)}")
            self.enhance_btn.config(state=tk.NORMAL)
            self.sr_btn.config(state=tk.NORMAL)
            self.play_original_btn.config(state=tk.NORMAL)



    def enhance(self):
        try:
            self.status.config(text="Enhancing... Please wait...", fg="blue")
            self.progress.start()
            self.root.update()

            vf = VoiceFixer()
            self.output_file = self.input_file.replace(".wav", "_enhanced.wav")
            vf.restore(input=self.input_file, output=self.output_file, cuda=False)

            self.progress.stop()
            self.status.config(text=f"Saved: {os.path.basename(self.output_file)}", fg="green")
            messagebox.showinfo("Done", f"Enhanced audio saved as:\n{self.output_file}")
            self.play_enhanced_btn.config(state=tk.NORMAL)
            self.export_btn.config(state=tk.NORMAL)
        except Exception as e:
            self.progress.stop()
            self.status.config(text="Error during enhancement", fg="red")
            messagebox.showerror("Error", str(e))

    def upsample(self):
        try:
            self.status.config(text="Upsampling... Please wait...", fg="blue")
            self.progress.start()
            self.root.update()

            output_sr = upsample_audiosr(self.input_file)

            self.progress.stop()
            self.status.config(text=f"Saved: {os.path.basename(output_sr)}", fg="green")
            messagebox.showinfo("Done", f"Upsampled file saved as:\n{output_sr}")
        except Exception as e:
            self.progress.stop()
            self.status.config(text="Error during upsampling", fg="red")
            messagebox.showerror("Error", str(e))

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
                if ext == ".mp3":
                    audio.export(export_path, format="mp3")
                else:
                    audio.export(export_path, format="flac")
                messagebox.showinfo("Exported", f"Exported successfully to:\n{export_path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def play_original(self):
        try:
            wave_obj = sa.WaveObject.from_wave_file(self.input_file)
            wave_obj.play()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def play_enhanced(self):
        try:
            if self.output_file:
                wave_obj = sa.WaveObject.from_wave_file(self.output_file)
                wave_obj.play()
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == '__main__':
    root = tk.Tk()
    app = MusicEnhancerApp(root)
    root.mainloop()
