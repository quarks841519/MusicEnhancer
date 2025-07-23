import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar
import os
import subprocess
import shutil
import threading # For running long operations in a separate thread

# Audio processing libraries
from pydub import AudioSegment
from pydub.playback import play as pydub_play # Renamed to avoid conflict with Tkinter play
import torch
import torchaudio
from audiosr import build_model, super_resolution

class AudioProcessorApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Enhancer & Upscaler")
        master.geometry("600x450") # Increased size for better layout
        master.resizable(False, False)

        # --- Variables ---
        self.original_selected_file = None
        self.processed_input_wav = None # WAV file prepared for Demucs/AudioSR
        self.demucs_output_file = None  # Output from Demucs enhancement
        self.audiosr_output_file = None # Final output from AudioSR upscaling
        self.current_playback = None    # To hold the pydub playback object

        # --- UI Elements ---
        self.create_widgets()

        # --- AudioSR Model (Load once) ---
        self.audiosr_model = None
        self._load_audiosr_model_threaded() # Load model in a separate thread

        # --- Temporary Directories ---
        self.temp_dir = "temp_audio_processing"
        os.makedirs(self.temp_dir, exist_ok=True)

    def create_widgets(self):
        # Frame for file selection and basic actions
        file_frame = tk.LabelFrame(self.master, text="File Selection & Actions", padx=10, pady=10)
        file_frame.pack(pady=10, padx=10, fill="x")

        self.select_btn = tk.Button(file_frame, text="Select Audio File", command=self.select_file)
        self.select_btn.pack(side=tk.LEFT, padx=5)

        self.file_label = tk.Label(file_frame, text="No file selected", wraplength=400, justify=tk.LEFT)
        self.file_label.pack(side=tk.LEFT, fill="x", expand=True, padx=5)

        # Frame for processing buttons
        process_frame = tk.LabelFrame(self.master, text="Processing Steps", padx=10, pady=10)
        process_frame.pack(pady=10, padx=10, fill="x")

        self.enhance_btn = tk.Button(process_frame, text="1. Enhance (Demucs)", command=lambda: self._run_in_thread(self.enhance), state=tk.DISABLED)
        self.enhance_btn.pack(side=tk.LEFT, padx=5)

        self.upscale_btn = tk.Button(process_frame, text="2. Upscale (AudioSR)", command=lambda: self._run_in_thread(self.upscale_audio), state=tk.DISABLED)
        self.upscale_btn.pack(side=tk.LEFT, padx=5)

        # Frame for playback controls
        playback_frame = tk.LabelFrame(self.master, text="Playback & Export", padx=10, pady=10)
        playback_frame.pack(pady=10, padx=10, fill="x")

        self.play_original_btn = tk.Button(playback_frame, text="Play Original", command=lambda: self._run_in_thread(self.play_audio, self.original_selected_file), state=tk.DISABLED)
        self.play_original_btn.pack(side=tk.LEFT, padx=5)

        self.play_enhanced_btn = tk.Button(playback_frame, text="Play Enhanced", command=lambda: self._run_in_thread(self.play_audio, self.demucs_output_file), state=tk.DISABLED)
        self.play_enhanced_btn.pack(side=tk.LEFT, padx=5)

        self.play_upscaled_btn = tk.Button(playback_frame, text="Play Upscaled", command=lambda: self._run_in_thread(self.play_audio, self.audiosr_output_file), state=tk.DISABLED)
        self.play_upscaled_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(playback_frame, text="Stop Playback", command=self.stop_audio, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = tk.Button(playback_frame, text="Export Final Audio", command=self.export_audio, state=tk.DISABLED)
        self.export_btn.pack(side=tk.RIGHT, padx=5)

        # Status and Progress
        self.status = tk.Label(self.master, text="Ready.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X, ipady=2)

        self.progress = Progressbar(self.master, orient="horizontal", length=500, mode="indeterminate")
        self.progress.pack(pady=10)

        # Initial button states
        self._set_processing_buttons_state(tk.DISABLED)
        self._set_playback_buttons_state(tk.DISABLED)

    def _run_in_thread(self, func, *args):
        """Helper to run a function in a separate thread to keep GUI responsive."""
        thread = threading.Thread(target=func, args=args)
        thread.daemon = True # Allow the program to exit even if thread is running
        thread.start()

    def _set_processing_buttons_state(self, state):
        self.enhance_btn.config(state=state)
        self.upscale_btn.config(state=state)

    def _set_playback_buttons_state(self, state):
        self.play_original_btn.config(state=state)
        self.play_enhanced_btn.config(state=state)
        self.play_upscaled_btn.config(state=state)
        self.stop_btn.config(state=state)
        self.export_btn.config(state=state)

    def _load_audiosr_model_threaded(self):
        """Loads AudioSR model in a separate thread to prevent GUI freeze."""
        self.status.config(text="Loading AudioSR model (this may take a moment)...", fg="blue")
        self.progress.start()
        def load_model():
            try:
                # Set default device to CPU for all subsequent tensor operations
                torch.set_default_device('cpu') 
                print("DEBUG: PyTorch default device set to CPU.")

                self.audiosr_model = build_model(model_name="basic")
                # Explicitly move the model to CPU (redundant if default is set, but good for clarity)
                self.audiosr_model.to('cpu')
                self.master.after(0, lambda: self.status.config(text="AudioSR model loaded on CPU. Ready.", fg="green"))
            except Exception as e:
                # Fix: Capture 'e' using a default argument
                self.master.after(0, lambda error=e: self.status.config(text=f"Error loading AudioSR model: {error}", fg="red"))
                self.master.after(0, lambda error=e: messagebox.showerror("Error", f"Failed to load AudioSR model. Please check your installation.\nDetails: {error}"))
            finally:
                self.master.after(0, self.progress.stop)
        self._run_in_thread(load_model)


    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.mp3 *.wav *.flac *.m4a *.mp4"), ("All Files", "*.*")]
        )
        if file_path:
            self.original_selected_file = file_path
            self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
            self._set_processing_buttons_state(tk.NORMAL)
            self.play_original_btn.config(state=tk.NORMAL)
            # Reset other states
            self.demucs_output_file = None
            self.audiosr_output_file = None
            self.play_enhanced_btn.config(state=tk.DISABLED)
            self.play_upscaled_btn.config(state=tk.DISABLED)
            self.export_btn.config(state=tk.DISABLED)
            self.status.config(text="File selected. Ready for enhancement.", fg="black")

    def prepare_input_audio(self, input_file_path):
        """
        Converts an audio file (e.g., MP4, MP3) to WAV format in a temporary directory.
        Returns the path to the temporary WAV file.
        """
        if not input_file_path:
            return None

        # Create a unique temporary WAV file name
        base_name = os.path.basename(input_file_path)
        file_name_without_ext = os.path.splitext(base_name)[0]
        wav_path = os.path.join(self.temp_dir, f"{file_name_without_ext}_temp.wav")

        if os.path.exists(wav_path):
            # If a temporary WAV already exists for this file, use it
            print(f"Temporary WAV file already exists: '{wav_path}'. Using existing file.")
            return wav_path

        self.master.after(0, lambda: self.status.config(text=f"Converting '{os.path.basename(input_file_path)}' to WAV...", fg="blue"))
        self.master.after(0, self.progress.start)
        self.master.update_idletasks() # Ensure GUI updates

        try:
            audio = AudioSegment.from_file(input_file_path, format=os.path.splitext(input_file_path)[1][1:])
            audio.export(wav_path, format="wav")
            self.master.after(0, lambda: self.status.config(text=f"Conversion successful to '{os.path.basename(wav_path)}'.", fg="green"))
            return wav_path
        except Exception as e:
            # Fix: Capture 'e' using a default argument
            self.master.after(0, lambda error=e: self.status.config(text=f"Error converting to WAV: {error}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Conversion Error", f"Failed to convert audio to WAV. Please ensure FFmpeg is installed and accessible in your system's PATH.\nDetails: {error}"))
            return None
        finally:
            self.master.after(0, self.progress.stop)


    def enhance(self):
        if not self.original_selected_file:
            self.master.after(0, lambda: messagebox.showwarning("Enhance", "Please select an audio file first."))
            return

        self.master.after(0, lambda: self.status.config(text="Preparing input audio for Demucs...", fg="blue"))
        self.processed_input_wav = self.prepare_input_audio(self.original_selected_file)
        if not self.processed_input_wav:
            self.master.after(0, lambda: self.status.config(text="Enhancement cancelled due to conversion error.", fg="red"))
            return

        try:
            self.master.after(0, lambda: self.status.config(text="Enhancing using Demucs...", fg="blue"))
            self.master.after(0, self.progress.start)
            self.master.update_idletasks() # Force GUI update

            # Demucs will create a 'separated' directory in the current working directory
            # It's better to manage its output location explicitly.
            # Let's create a temporary directory for Demucs output
            demucs_output_base_dir = os.path.join(self.temp_dir, "demucs_output")
            os.makedirs(demucs_output_base_dir, exist_ok=True)

            # Demucs command: -o specifies output directory, -n specifies model
            # The output will be <demucs_output_base_dir>/htdemucs/<input_filename_without_ext>/<stems>.wav
            command = ["demucs", "-n", "htdemucs", "-o", demucs_output_base_dir, self.processed_input_wav]
            print(f"Running Demucs command: {' '.join(command)}")
            
            # Execute Demucs and capture output
            result = subprocess.run(command, check=False, capture_output=True, text=True) # Changed check=True to check=False to capture output even on non-zero exit
            
            print(f"\n--- Demucs STDOUT ---")
            print(result.stdout)
            print(f"--- Demucs STDERR ---")
            print(result.stderr)
            print(f"--- Demucs Exit Code: {result.returncode} ---\n")

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)

            basename = os.path.splitext(os.path.basename(self.processed_input_wav))[0]
            # Path to the directory containing the separated stems
            demucs_stems_dir = os.path.join(demucs_output_base_dir, "htdemucs", basename)
            print(f"Demucs stems directory: {demucs_stems_dir}")

            # Define the path for the recombined output
            recombined_path = os.path.join(demucs_stems_dir, "recombined.wav")
            print(f"Expected recombined path: {recombined_path}")

            if os.path.exists(demucs_stems_dir) and os.listdir(demucs_stems_dir):
                # Manually recombine stems if 'recombined.wav' is not directly produced
                print("Demucs output found. Recombining stems...")
                
                # List of common stems produced by htdemucs
                stems = ["vocals.wav", "drums.wav", "bass.wav", "other.wav"]
                
                combined_audio = None
                for stem_name in stems:
                    stem_path = os.path.join(demucs_stems_dir, stem_name)
                    if os.path.exists(stem_path):
                        print(f"Loading stem: {stem_name}")
                        current_stem = AudioSegment.from_file(stem_path)
                        if combined_audio is None:
                            combined_audio = current_stem
                        else:
                            # Ensure same sample rate before combining
                            if combined_audio.frame_rate != current_stem.frame_rate:
                                print(f"Warning: Resampling {stem_name} from {current_stem.frame_rate}Hz to {combined_audio.frame_rate}Hz for combination.")
                                current_stem = current_stem.set_frame_rate(combined_audio.frame_rate)
                            combined_audio += current_stem
                    else:
                        print(f"Warning: Stem '{stem_name}' not found in '{demucs_stems_dir}'. Skipping.")

                if combined_audio:
                    combined_audio.export(recombined_path, format="wav")
                    print(f"Stems recombined and saved to: {recombined_path}")
                else:
                    raise Exception("No audio stems found or combined after Demucs processing.")

                # Copy the recombined file to a more accessible location for later use
                self.demucs_output_file = os.path.join(self.temp_dir, f"{basename}_enhanced.wav")
                shutil.copyfile(recombined_path, self.demucs_output_file)

                # Clean up Demucs specific output directory
                if os.path.exists(demucs_stems_dir):
                    shutil.rmtree(demucs_stems_dir, ignore_errors=True)
                    print(f"Cleaned up Demucs specific output: {demucs_stems_dir}")

                self.master.after(0, lambda: self.status.config(text="Enhanced file saved.", fg="green"))
                self.master.after(0, lambda: self.play_enhanced_btn.config(state=tk.NORMAL))
                self.master.after(0, lambda: self.stop_btn.config(state=tk.NORMAL)) # Stop button is general
                self.master.after(0, lambda: self.upscale_btn.config(state=tk.NORMAL)) # Now ready for upscale

                self.master.after(0, lambda: messagebox.showinfo("Done", f"Enhanced audio saved temporarily as:\n{os.path.basename(self.demucs_output_file)}"))
            else:
                # If Demucs output directory or its contents are missing
                actual_output_dir_parent = os.path.join(demucs_output_base_dir, "htdemucs")
                dir_contents = "Directory not found."
                if os.path.exists(actual_output_dir_parent):
                    dir_contents = "\n".join(os.listdir(actual_output_dir_parent))
                
                error_msg = (f"Demucs output directory or stems not found. Expected stems in: {demucs_stems_dir}\n"
                             f"Contents of '{actual_output_dir_parent}':\n{dir_contents}\n"
                             "Please check Demucs logs (printed above) for errors.")
                print(f"Error: {error_msg}") # Print to console for debugging
                raise Exception(error_msg) # Raise an exception to be caught by outer try-except
        except FileNotFoundError:
            self.master.after(0, lambda: self.status.config(text="Error: 'demucs' command not found.", fg="red"))
            self.master.after(0, lambda: messagebox.showerror("Demucs Error", "Demucs is not installed or not in your system's PATH.\nPlease install it using 'pip install demucs'."))
        except subprocess.CalledProcessError as e:
            # Fix: Capture 'e' using a default argument
            self.master.after(0, lambda error=e: self.status.config(text=f"Demucs execution failed: {error.returncode}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Demucs Error", f"Demucs command failed with error code {error.returncode}.\nSTDOUT:\n{error.stdout}\nSTDERR:\n{error.stderr}"))
        except Exception as e:
            # Fix: Capture 'e' using a default argument
            self.master.after(0, lambda error=e: self.status.config(text=f"An error occurred during enhancement: {error}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Enhancement Error", f"An unexpected error occurred during enhancement: {error}"))
        finally:
            self.master.after(0, self.progress.stop)

    def upscale_audio(self):
        if not self.original_selected_file: # Ensure an original file is selected before proceeding
            self.master.after(0, lambda: messagebox.showwarning("Upscale", "Please select an audio file first."))
            return

        # If Demucs output is not available, prepare the original input for AudioSR
        input_for_audiosr = self.demucs_output_file
        if not input_for_audiosr:
            self.master.after(0, lambda: self.status.config(text="Preparing original audio for upscaling...", fg="blue"))
            self.processed_input_wav = self.prepare_input_audio(self.original_selected_file)
            input_for_audiosr = self.processed_input_wav
            if not input_for_audiosr:
                self.master.after(0, lambda: self.status.config(text="Upscaling cancelled due to conversion error.", fg="red"))
                return

        if not self.audiosr_model:
            self.master.after(0, lambda: messagebox.showwarning("Upscale", "AudioSR model is still loading or failed to load. Please wait or restart."))
            return

        self.master.after(0, lambda: self.status.config(text="Upscaling using AudioSR...", fg="blue"))
        self.master.after(0, self.progress.start)
        self.master.update_idletasks() # Force GUI update

        try:
            print(f"Loading audio for AudioSR from '{input_for_audiosr}'...")
            print(f"DEBUG: Type of input_for_audiosr: {type(input_for_audiosr)}")
            print(f"DEBUG: Value of input_for_audiosr: {input_for_audiosr}") 
            
            # Explicitly ensure input_for_audiosr is a string path
            if not isinstance(input_for_audiosr, str):
                print(f"DEBUG: Critical: input_for_audiosr is NOT a string. Type: {type(input_for_audiosr)}, Value: {input_for_audiosr}")
                try:
                    input_for_audiosr_str = str(input_for_audiosr)
                    print(f"DEBUG: Attempted conversion to string: {input_for_audiosr_str}")
                except Exception as convert_e:
                    raise TypeError(f"Expected a string file path for torchaudio.load, but received type {type(input_for_audiosr)}. "
                                    f"Conversion to string failed: {convert_e}. Value: {input_for_audiosr}") from convert_e
                input_for_audiosr = input_for_audiosr_str
            
            if not os.path.exists(input_for_audiosr):
                raise FileNotFoundError(f"File not found for torchaudio.load: {input_for_audiosr}")

            waveform, sample_rate = torchaudio.load(input_for_audiosr)
            print(f"Input audio loaded: Sample Rate = {sample_rate} Hz, Channels = {waveform.shape[0]}")

            # Ensure the waveform is mono if the model expects it
            if waveform.shape[0] > 1:
                print("Converting stereo input to mono for AudioSR...")
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Downsample the waveform to a sample rate suitable for AudioSR (e.g., 16000 Hz)
            target_audiosr_input_sample_rate = 16000
            if sample_rate != target_audiosr_input_sample_rate:
                print(f"Resampling audio from {sample_rate} Hz to {target_audiosr_input_sample_rate} Hz for AudioSR input...")
                resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=target_audiosr_input_sample_rate)
                waveform = resampler(waveform)
                sample_rate = target_audiosr_input_sample_rate
                print(f"Audio resampled. New Sample Rate = {sample_rate} Hz.")

            # No need to save to a temporary file here, as super_resolution expects a tensor.
            # The previous "Invalid file: tensor(...)" error was misleading.
            # The current "convolution_overrideable not implemented" is the real issue,
            # which is handled by ensuring all operations are on CPU.

            print("Performing audio super-resolution (this might take a while)...")
            upsampled_waveform = super_resolution(
                self.audiosr_model,
                waveform.to('cpu'), # Ensure the waveform is on CPU
                sample_rate, # Pass the sample rate of the content in the file
                ddim_steps=50,
                guidance_scale=3.5,
            )
            print("Audio super-resolution complete.")

            # Save the upsampled audio
            original_filename_no_ext = os.path.splitext(os.path.basename(self.original_selected_file))[0]
            if self.demucs_output_file:
                self.audiosr_output_file = os.path.join(self.temp_dir, f"{original_filename_no_ext}_enhanced_upscaled.wav")
            else:
                self.audiosr_output_file = os.path.join(self.temp_dir, f"{original_filename_no_ext}_upscaled.wav")

            print(f"Saving upsampled audio to '{self.audiosr_output_file}' (48kHz)...")
            torchaudio.save(self.audiosr_output_file, upsampled_waveform, 48000)

            self.master.after(0, lambda: self.status.config(text="Upscaling complete. File saved.", fg="green"))
            self.master.after(0, lambda: self.play_upscaled_btn.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.export_btn.config(state=tk.NORMAL))
            self.master.after(0, lambda: messagebox.showinfo("Done", f"Upscaled audio saved temporarily as:\n{os.path.basename(self.audiosr_output_file)}"))

        except Exception as e:
            # Fix: Capture 'e' using a default argument
            self.master.after(0, lambda error=e: self.status.config(text=f"An error occurred during upscaling: {error}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Upscaling Error", f"An unexpected error occurred during upscaling: {error}"))
        finally:
            self.master.after(0, self.progress.stop)

    def play_audio(self, file_path):
        if not file_path or not os.path.exists(file_path):
            self.master.after(0, lambda: messagebox.showwarning("Playback", "No audio file to play or file not found."))
            return

        self.stop_audio() # Stop any currently playing audio first

        try:
            self.master.after(0, lambda: self.status.config(text=f"Playing: {os.path.basename(file_path)}...", fg="blue"))
            audio = AudioSegment.from_file(file_path)
            self.current_playback = pydub_play(audio) # Store the playback object
            self.master.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
        except Exception as e:
            # Fix: Capture 'e' using a default argument
            self.master.after(0, lambda error=e: self.status.config(text=f"Error playing audio: {error}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Playback Error", f"Could not play audio. Ensure FFmpeg is installed and the file is valid.\nDetails: {error}"))

    def stop_audio(self):
        if self.current_playback:
            try:
                # pydub's play returns a subprocess.Popen object on some systems
                # We can terminate it if it's still running.
                if hasattr(self.current_playback, 'terminate'):
                    self.current_playback.terminate()
                self.current_playback = None
                self.master.after(0, lambda: self.status.config(text="Playback stopped.", fg="black"))
            except Exception as e:
                # Fix: Capture 'e' using a default argument
                self.master.after(0, lambda error=e: self.status.config(text=f"Error stopping playback: {error}", fg="red"))
        else:
            self.master.after(0, lambda: self.status.config(text="No audio playing.", fg="black"))

    def export_audio(self):
        file_to_export = self.audiosr_output_file if self.audiosr_output_file else self.demucs_output_file

        if not file_to_export or not os.path.exists(file_to_export):
            self.master.after(0, lambda: messagebox.showwarning("Export", "No processed audio to export."))
            return

        initial_filename = os.path.basename(file_to_export)
        # Suggest a default filename based on the last processed file
        default_name = os.path.splitext(initial_filename)[0] + "_final.wav"

        save_path = filedialog.asksaveasfilename(
            title="Save Processed Audio",
            defaultextension=".wav",
            initialfile=default_name,
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if save_path:
            try:
                shutil.copyfile(file_to_export, save_path)
                self.master.after(0, lambda: self.status.config(text=f"Audio exported to: {os.path.basename(save_path)}", fg="green"))
                self.master.after(0, lambda: messagebox.showinfo("Export Done", f"Audio successfully exported to:\n{save_path}"))
            except Exception as e:
                # Fix: Capture 'e' using a default argument
                self.master.after(0, lambda error=e: self.status.config(text=f"Error exporting audio: {error}", fg="red"))
                self.master.after(0, lambda error=e: messagebox.showerror("Export Error", f"Failed to export audio:\n{error}"))

    def on_closing(self):
        """Clean up temporary files and directories on application close."""
        self.stop_audio()
        if os.path.exists(self.temp_dir):
            print(f"Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioProcessorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing) # Handle window close event
    root.mainloop()
