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

class AudioProcessorApp:
    def __init__(self, master):
        self.master = master
        master.title("Audio Enhancer") # Changed title
        master.geometry("600x400") # Adjusted size
        master.resizable(False, False)

        # --- Variables ---
        self.original_selected_file = None
        self.processed_input_wav = None # WAV file prepared for Demucs
        self.demucs_output_file = None  # Output from Demucs enhancement
        self.current_playback = None    # To hold the pydub playback object

        # --- UI Elements ---
        self.create_widgets()

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

        self.enhance_btn = tk.Button(process_frame, text="Enhance (Demucs)", command=lambda: self._run_in_thread(self.enhance), state=tk.DISABLED)
        self.enhance_btn.pack(side=tk.LEFT, padx=5)

        # Frame for playback controls
        playback_frame = tk.LabelFrame(self.master, text="Playback & Export", padx=10, pady=10)
        playback_frame.pack(pady=10, padx=10, fill="x")

        self.play_original_btn = tk.Button(playback_frame, text="Play Original", command=lambda: self._run_in_thread(self.play_audio, self.original_selected_file), state=tk.DISABLED)
        self.play_original_btn.pack(side=tk.LEFT, padx=5)

        self.play_enhanced_btn = tk.Button(playback_frame, text="Play Enhanced", command=lambda: self._run_in_thread(self.play_audio, self.demucs_output_file), state=tk.DISABLED)
        self.play_enhanced_btn.pack(side=tk.LEFT, padx=5)

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

    def _set_playback_buttons_state(self, state):
        self.play_original_btn.config(state=state)
        self.play_enhanced_btn.config(state=state)
        self.stop_btn.config(state=state)
        self.export_btn.config(state=state)

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
            self.play_enhanced_btn.config(state=tk.DISABLED)
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

            demucs_output_base_dir = os.path.join(self.temp_dir, "demucs_output")
            os.makedirs(demucs_output_base_dir, exist_ok=True)

            command = ["demucs", "-n", "htdemucs", "-o", demucs_output_base_dir, self.processed_input_wav]
            print(f"Running Demucs command: {' '.join(command)}")
            
            result = subprocess.run(command, check=False, capture_output=True, text=True) 
            
            print(f"\n--- Demucs STDOUT ---")
            print(result.stdout)
            print(f"--- Demucs STDERR ---")
            print(result.stderr)
            print(f"--- Demucs Exit Code: {result.returncode} ---\n")

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command, output=result.stdout, stderr=result.stderr)

            basename = os.path.splitext(os.path.basename(self.processed_input_wav))[0]
            demucs_stems_dir = os.path.join(demucs_output_base_dir, "htdemucs", basename)
            print(f"Demucs stems directory: {demucs_stems_dir}")

            recombined_path = os.path.join(demucs_stems_dir, "recombined.wav")
            print(f"Expected recombined path: {recombined_path}")

            if os.path.exists(demucs_stems_dir) and os.listdir(demucs_stems_dir):
                print("Demucs output found. Recombining stems...")
                
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

                self.demucs_output_file = os.path.join(self.temp_dir, f"{basename}_enhanced.wav")
                shutil.copyfile(recombined_path, self.demucs_output_file)

                if os.path.exists(demucs_stems_dir):
                    shutil.rmtree(demucs_stems_dir, ignore_errors=True)
                    print(f"Cleaned up Demucs specific output: {demucs_stems_dir}")

                self.master.after(0, lambda: self.status.config(text="Enhanced file saved.", fg="green"))
                self.master.after(0, lambda: self.play_enhanced_btn.config(state=tk.NORMAL))
                self.master.after(0, lambda: self.stop_btn.config(state=tk.NORMAL)) # Stop button is general
                self.master.after(0, lambda: self.export_btn.config(state=tk.NORMAL)) # Enable export after enhancement

                self.master.after(0, lambda: messagebox.showinfo("Done", f"Enhanced audio saved temporarily as:\n{os.path.basename(self.demucs_output_file)}"))
            else:
                actual_output_dir_parent = os.path.join(demucs_output_base_dir, "htdemucs")
                dir_contents = "Directory not found."
                if os.path.exists(actual_output_dir_parent):
                    dir_contents = "\n".join(os.listdir(actual_output_dir_parent))
                
                error_msg = (f"Demucs output directory or stems not found. Expected stems in: {demucs_stems_dir}\n"
                             f"Contents of '{actual_output_dir_parent}':\n{dir_contents}\n"
                             "Please check Demucs logs (printed above) for errors.")
                print(f"Error: {error_msg}")
                raise Exception(error_msg)
        except FileNotFoundError:
            self.master.after(0, lambda: self.status.config(text="Error: 'demucs' command not found.", fg="red"))
            self.master.after(0, lambda: messagebox.showerror("Demucs Error", "Demucs is not installed or not in your system's PATH.\nPlease install it using 'pip install demucs'."))
        except subprocess.CalledProcessError as e:
            self.master.after(0, lambda error=e: self.status.config(text=f"Demucs execution failed: {error.returncode}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Demucs Error", f"Demucs command failed with error code {error.returncode}.\nSTDOUT:\n{error.stdout}\nSTDERR:\n{error.stderr}"))
        except Exception as e:
            self.master.after(0, lambda error=e: self.status.config(text=f"An error occurred during enhancement: {error}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Enhancement Error", f"An unexpected error occurred during enhancement: {error}"))
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
            self.master.after(0, lambda error=e: self.status.config(text=f"Error playing audio: {error}", fg="red"))
            self.master.after(0, lambda error=e: messagebox.showerror("Playback Error", f"Could not play audio. Ensure FFmpeg is installed and the file is valid.\nDetails: {error}"))

    def stop_audio(self):
        if self.current_playback:
            try:
                if hasattr(self.current_playback, 'terminate'):
                    self.current_playback.terminate()
                self.current_playback = None
                self.master.after(0, lambda: self.status.config(text="Playback stopped.", fg="black"))
            except Exception as e:
                self.master.after(0, lambda error=e: self.status.config(text=f"Error stopping playback: {error}", fg="red"))
        else:
            self.master.after(0, lambda: self.status.config(text="No audio playing.", fg="black"))

    def export_audio(self):
        file_to_export = self.demucs_output_file # Only demucs output available

        if not file_to_export or not os.path.exists(file_to_export):
            self.master.after(0, lambda: messagebox.showwarning("Export", "No processed audio to export."))
            return

        initial_filename = os.path.basename(file_to_export)
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