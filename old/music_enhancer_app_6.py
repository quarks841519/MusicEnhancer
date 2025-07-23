import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pydub import AudioSegment
import simpleaudio as sa
import subprocess
import torch
import torchaudio
from audiosr import build_model, super_resolution

class MusicEnhancerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Music Enhancer with Demucs + AudioSR")
        self.root.geometry("450x650")

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

        self.export_btn = tk.Button(root, text="Export Enhanced as MP3/FLAC", command=self.export_audio, state=tk.DISABLED)
        self.export_btn.pack(pady=5)

        self.upscale_btn = tk.Button(root, text="Upscale with AudioSR", command=self.upscale_audio, state=tk.DISABLED)
        self.upscale_btn.pack(pady=5)

        self.play_upscaled_btn = tk.Button(root, text="Play Upscaled", command=self.play_upscaled, state=tk.DISABLED)
        self.play_upscaled_btn.pack(pady=5)
        self.stop_upscaled_btn = tk.Button(root, text="Stop Upscaled", command=self.stop_upscaled, state=tk.DISABLED)
        self.stop_upscaled_btn.pack(pady=5)


        self.progress = ttk.Progressbar(root, mode='indeterminate')
        self.progress.pack(pady=10, fill='x', padx=20)

        self.status = tk.Label(root, text="", fg="green", wraplength=400)
        self.status.pack(pady=10)

        self.original_selected_file = None
        self.processed_input_wav = None
        self.demucs_output_file = None
        self.audiosr_output_file = None

        self.original_play_obj = None
        self.enhanced_play_obj = None
        self.upscaled_play_obj = None

        self.temp_wav_dir = "temp_converted_wavs"
        os.makedirs(self.temp_wav_dir, exist_ok=True)


    def select_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.mp4")])
        if file_path:
            self.original_selected_file = file_path
            self.status.config(text=f"Selected: {os.path.basename(self.original_selected_file)}")
            self.enhance_btn.config(state=tk.NORMAL)
            self.play_original_btn.config(state=tk.NORMAL)
            self.stop_original_btn.config(state=tk.NORMAL)
            self.upscale_btn.config(state=tk.NORMAL)

            self.demucs_output_file = None
            self.audiosr_output_file = None
            self.export_btn.config(state=tk.DISABLED)
            self.play_enhanced_btn.config(state=tk.DISABLED)
            self.stop_enhanced_btn.config(state=tk.DISABLED)
            self.play_upscaled_btn.config(state=tk.DISABLED)
            self.stop_upscaled_btn.config(state=tk.DISABLED)

    def prepare_input_audio(self, source_file_path):
        if source_file_path is None:
            return None
        if source_file_path.lower().endswith(".wav"):
            return source_file_path

        base_name = os.path.basename(source_file_path)
        file_name_without_ext = os.path.splitext(base_name)[0]
        wav_path = os.path.join(self.temp_wav_dir, f"{file_name_without_ext}_temp.wav")

        if os.path.exists(wav_path):
            print(f"Temporary WAV file already exists for '{base_name}'. Using existing file.")
            return wav_path

        self.status.config(text=f"Converting '{base_name}' to WAV...", fg="blue")
        self.progress.start()
        self.root.update()

        try:
            file_format = os.path.splitext(source_file_path)[1][1:]
            audio = AudioSegment.from_file(source_file_path, format=file_format)
            audio.export(wav_path, format="wav")
            print(f"Converted '{base_name}' to WAV: {wav_path}")
            return wav_path
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to convert '{base_name}' to WAV.\nDetails: {e}\nEnsure FFmpeg is installed and in your system's PATH.")
            return None
        finally:
            self.progress.stop()

    def enhance(self):
        if not self.original_selected_file:
            messagebox.showwarning("Enhance", "Please select an audio file first.")
            return

        self.processed_input_wav = self.prepare_input_audio(self.original_selected_file)
        if not self.processed_input_wav:
            self.status.config(text="Enhancement cancelled due to conversion error.", fg="red")
            return

        try:
            self.status.config(text="Enhancing using Demucs...", fg="blue")
            self.progress.start()
            self.root.update()

            command = ["demucs", "-n", "htdemucs", self.processed_input_wav]
            subprocess.run(command, check=True)

            basename = os.path.splitext(os.path.basename(self.processed_input_wav))[0]
            out_dir = os.path.join("separated", "htdemucs", basename)
            recombined_path = os.path.join(out_dir, "recombined.wav")

            if os.path.exists(recombined_path):
                self.demucs_output_file = os.path.abspath("enhanced_output.wav")
                shutil.copyfile(recombined_path, self.demucs_output_file)

                self.status.config(text="Enhanced file saved.", fg="green")
                self.play_enhanced_btn.config(state=tk.NORMAL)
                self.stop_enhanced_btn.config(state=tk.NORMAL)
                self.export_btn.config(state=tk.NORMAL)
                self.upscale_btn.config(state=tk.NORMAL)

                messagebox.showinfo("Done", f"Enhanced audio saved as:\n{self.demucs_output_file}")
            else:
                raise Exception("Demucs recombined output not found. Check Demucs logs for errors.")
        except FileNotFoundError:
            messagebox.showerror("Enhancement Error", "Demucs command not found. Please ensure Demucs is installed and in your system's PATH.")
            self.status.config(text="Enhancement failed: Demucs not found.", fg="red")
        except Exception as e:
            messagebox.showerror("Enhancement Error", str(e))
            self.status.config(text="Enhancement failed.", fg="red")
        finally:
            self.progress.stop()

    def export_audio(self):
        if not self.demucs_output_file:
            messagebox.showwarning("Export", "No enhanced audio to export. Please run enhancement first.")
            return

        export_path = filedialog.asksaveasfilename(defaultextension=".mp3",
                               filetypes=[("MP3", "*.mp3"), ("FLAC", "*.flac")])
        if export_path:
            try:
                audio = AudioSegment.from_wav(self.demucs_output_file)
                ext = os.path.splitext(export_path)[1].lower()
                audio.export(export_path, format="mp3" if ext == ".mp3" else "flac")
                messagebox.showinfo("Exported", f"Exported to:\n{export_path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def play_original(self):
        try:
            if self.original_play_obj:
                self.original_play_obj.stop()
            play_path = self.prepare_input_audio(self.original_selected_file)
            if play_path:
                wave_obj = sa.WaveObject.from_wave_file(play_path)
                self.original_play_obj = wave_obj.play()
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def stop_original(self):
        if self.original_play_obj:
            self.original_play_obj.stop()

    def play_enhanced(self):
        try:
            if self.enhanced_play_obj:
                self.enhanced_play_obj.stop()
            if self.demucs_output_file and os.path.exists(self.demucs_output_file):
                wave_obj = sa.WaveObject.from_wave_file(self.demucs_output_file)
                self.enhanced_play_obj = wave_obj.play()
            else:
                messagebox.showwarning("Playback", "Enhanced audio file not found.")
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def stop_enhanced(self):
        if self.enhanced_play_obj:
            self.enhanced_play_obj.stop()

    def play_upscaled(self):
        try:
            if self.upscaled_play_obj:
                self.upscaled_play_obj.stop()
            if self.audiosr_output_file and os.path.exists(self.audiosr_output_file):
                wave_obj = sa.WaveObject.from_wave_file(self.audiosr_output_file)
                self.upscaled_play_obj = wave_obj.play()
            else:
                messagebox.showwarning("Playback", "Upscaled audio file not found.")
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def stop_upscaled(self):
        if self.upscaled_play_obj:
            self.upscaled_play_obj.stop()

    def upscale_audio(self):
        source_path = self.demucs_output_file if self.demucs_output_file else self.original_selected_file
        if not source_path:
            messagebox.showerror("Upscaling Error", "No audio file selected or enhanced to upscale.")
            return

        processed_source_wav = self.prepare_input_audio(source_path)
        if not processed_source_wav:
            self.status.config(text="Upscaling cancelled due to conversion error.", fg="red")
            return

        try:
            self.status.config(text="Loading AudioSR model...", fg="blue")
            self.progress.start()
            self.root.update()

            model = build_model(model_name="basic")
            print("AudioSR model loaded.")

            self.status.config(text=f"Performing audio super-resolution on '{os.path.basename(processed_source_wav)}'...", fg="blue")
            self.root.update()

            # --- CORRECTED SUPER_RESOLUTION CALL FOR YOUR AUDIOSR VERSION 0.0.7 ---
            # Based on: (latent_diffusion, input_file, seed=42, ddim_steps=200, guidance_scale=3.5, latent_t_per_second=12.8, config=None)
            upscaled = super_resolution(
                model,                      # Corresponds to 'latent_diffusion'
                processed_source_wav,       # Corresponds to 'input_file'
                ddim_steps=50,              # Using default steps, or could be a user setting
                guidance_scale=3.5,         # Using default guidance, or could be a user setting
                latent_t_per_second=12.8    # Adding this parameter with its default value
            )
            # Input waveform loading with torchaudio.load is NOT needed before super_resolution in this API
            # Input waveform conversion to mono is NOT needed before super_resolution in this API
            # 'target_sample_rate' is NOT a parameter for super_resolution in this API

            # Save upscaled output
            base_name_for_output = os.path.basename(source_path)
            name, ext = os.path.splitext(base_name_for_output)
            if self.temp_wav_dir in processed_source_wav:
                self.audiosr_output_file = os.path.join(os.getcwd(), f"{name}_upscaled.wav")
            else:
                self.audiosr_output_file = os.path.join(os.path.dirname(processed_source_wav), f"{name}_upscaled.wav")

            # torchaudio.save will handle the output sample rate to 48000 Hz implicitly
            # if the upscaled waveform is already at that rate, or will resample.
            # The 'super_resolution' function in your version handles internal resampling.
            torchaudio.save(self.audiosr_output_file, upscaled, 48000)

            self.status.config(text="Upscaled audio saved.", fg="green")
            self.play_upscaled_btn.config(state=tk.NORMAL)
            self.stop_upscaled_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Success", f"Saved upscaled audio to:\n{self.audiosr_output_file}")

        except ImportError as e:
            messagebox.showerror("Upscaling Error", f"Missing required libraries for AudioSR. Ensure torch, torchaudio, and audiosr are installed. Details: {e}")
            self.status.config(text="Upscaling failed: Missing libraries.", fg="red")
        except Exception as e:
            messagebox.showerror("Upscaling Error", str(e))
            self.status.config(text="Upscaling failed.", fg="red")
        finally:
            self.progress.stop()

if __name__ == '__main__':
    root = tk.Tk()
    app = MusicEnhancerApp(root)
    root.mainloop()

    if os.path.exists(app.temp_wav_dir):
        print(f"Cleaning up temporary directory: {app.temp_wav_dir}")
        shutil.rmtree(app.temp_wav_dir)