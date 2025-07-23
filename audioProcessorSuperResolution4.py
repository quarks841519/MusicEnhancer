# audioProcessorSuperResolution4.py
#
# This script provides a GUI for audio super-resolution.
# It leverages the 'audiosr' library for the core super-resolution
# functionality and depends on other open-source libraries like
# torchaudio, pydub, and external FFmpeg for audio processing.
#
# Author: quarks841519
# Date: July 23, 2025
#
# Original AudioSR Library: [Link to AudioSR GitHub/Docs]
# PyTorch: https://pytorch.org/
# Pydub: https://github.com/jiaaro/pydub
# FFmpeg: https://ffmpeg.org/
#
#----------------------------------------------------------------------


import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import torch
import torchaudio
from audiosr import build_model, super_resolution
from pydub import AudioSegment
import math
import numpy as np # Import numpy

# trying to export as flac

def convert_to_wav(input_file_path, output_dir="temp_wavs"):
    """
    Converts an audio file (e.g., MP4, MP3) to WAV format.
    Creates a temporary WAV file in output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(input_file_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    wav_path = os.path.join(output_dir, f"{file_name_without_ext}.wav")

    if os.path.exists(wav_path):
        print(f"Temporary WAV file already exists: '{wav_path}'. Using existing file.")
        return wav_path

    print(f"Converting '{input_file_path}' to WAV format for processing...")
    try:
        audio = AudioSegment.from_file(input_file_path, format=os.path.splitext(input_file_path)[1][1:])
        audio.export(wav_path, format="wav")
        print(f"Conversion successful. Temporary WAV saved to: '{wav_path}'")
        return wav_path
    except Exception as e:
        print(f"Error during conversion of '{input_file_path}' to WAV: {e}")
        print("Please ensure FFmpeg is installed and accessible in your system's PATH.")
        return None

def test_audiosr_super_resolution(input_audio_path, output_audio_dir, log_callback=None, completion_callback=None):
    """
    Tests the AudioSR super_resolution function with a given input audio file.
    Includes an optional FFmpeg repair step for MP4 files.
    Automatically converts non-WAV files to WAV.
    Includes callbacks for logging and completion.
    """
    def log(message):
        if log_callback:
            log_callback(message)
        print(message)

    if not os.path.exists(input_audio_path):
        log(f"Error: Input audio file not found at '{input_audio_path}'")
        log("Please provide a valid path to an audio file.")
        if completion_callback:
            completion_callback(False)
        return

    processed_input_path = input_audio_path
    temp_wav_created = False
    temp_repaired_mp4_created = False # Track if a repaired MP4 was created

    # --- NEW: FFmpeg repair step for MP4 files ---
    if input_audio_path.lower().endswith(".mp4"):
        log(f"Input is MP4. Attempting to repair with FFmpeg: '{input_audio_path}'...")
        original_filename_no_ext = os.path.splitext(os.path.basename(input_audio_path))[0]
        repaired_mp4_path = os.path.join("temp_wavs", f"{original_filename_no_ext}_repaired.mp4") # Using temp_wavs for consistency

        try:
            # Check if repaired file already exists to avoid reprocessing
            if os.path.exists(repaired_mp4_path):
                log(f"Repaired MP4 file already exists: '{repaired_mp4_path}'. Using existing file.")
                processed_input_path = repaired_mp4_path
                temp_repaired_mp4_created = True # Treat it as created for cleanup purposes
            else:
                # ffmpeg -i input.mp4 -c copy -movflags faststart output_repaired.mp4
                command = [
                    "ffmpeg",
                    "-i", input_audio_path,
                    "-c", "copy",
                    "-movflags", "faststart",
                    repaired_mp4_path
                ]
                log(f"Executing FFmpeg command: {' '.join(command)}")
                
                # Run FFmpeg as a subprocess
                process = subprocess.run(command, capture_output=True, text=True)

                if process.returncode == 0:
                    log(f"FFmpeg repair successful. Repaired file: '{repaired_mp4_path}'")
                    processed_input_path = repaired_mp4_path
                    temp_repaired_mp4_created = True
                else:
                    log(f"FFmpeg repair failed for '{input_audio_path}'. Error:\n{process.stderr}")
                    log("Proceeding with original MP4, but issues might persist.")
                    # If repair fails, processed_input_path remains the original input_audio_path
        except FileNotFoundError:
            log("Error: FFmpeg command not found. Please ensure FFmpeg is installed and accessible in your system's PATH.")
            log("Proceeding without FFmpeg repair.")
        except Exception as e:
            log(f"An unexpected error occurred during FFmpeg repair: {e}")
            log("Proceeding without FFmpeg repair.")
    # --- END NEW FFmpeg repair step ---


    if not processed_input_path.lower().endswith(".wav"):
        log(f"Input is not WAV. Converting '{processed_input_path}' to WAV...")
        temp_wav_path = convert_to_wav(processed_input_path) # Use processed_input_path here
        if temp_wav_path is None:
            log("Failed to prepare input audio. Exiting.")
            if completion_callback:
                completion_callback(False)
            return
        processed_input_path = temp_wav_path
        temp_wav_created = True

    os.makedirs(output_audio_dir, exist_ok=True)

    try:
        log(f"Loading AudioSR model (basic)...")
        model = build_model(model_name="basic")
        log("AudioSR model loaded.")

        # Move model to device (MPS if available)
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        log(f"Using device: {device}")
        model.to(device)

        # Load the full audio initially to get its properties for chunking
        log(f"Loading full input audio for chunking from '{processed_input_path}'...")
        full_waveform, full_sample_rate = torchaudio.load(processed_input_path)
        log(f"Full audio loaded: Sample Rate = {full_sample_rate} Hz, Channels = {full_waveform.shape[0]}, Duration (s) = {full_waveform.shape[1] / full_sample_rate:.2f}")

        if full_waveform.shape[0] > 1:
            log("Converting full stereo input to mono for chunking...")
            full_waveform = torch.mean(full_waveform, dim=0, keepdim=True)
            log(f"Converted to mono: Channels = {full_waveform.shape[0]}")
        
        chunk_duration_seconds = 10.0
        chunk_length_samples = int(chunk_duration_seconds * full_sample_rate)

        total_samples = full_waveform.shape[1]
        num_chunks = math.ceil(total_samples / chunk_length_samples)
        upsampled_chunks = []
        
        temp_chunk_dir = os.path.join("temp_wavs", "chunks")
        os.makedirs(temp_chunk_dir, exist_ok=True)

        log(f"Performing audio super-resolution in {num_chunks} chunks of ~{chunk_duration_seconds:.2f} seconds...")

        for i in range(num_chunks):
            start_sample = i * chunk_length_samples
            end_sample = min((i + 1) * chunk_length_samples, total_samples)
            
            # Extract the chunk from the full waveform (still on CPU initially)
            current_chunk_waveform = full_waveform[:, start_sample:end_sample]
            
            chunk_filename = f"chunk_{i:03d}.wav"
            temp_chunk_path = os.path.join(temp_chunk_dir, chunk_filename)

            log(f"Processing chunk {i+1}/{num_chunks} (samples {start_sample}-{end_sample})...")
            
            # Save the current chunk to a temporary WAV file for super_resolution to load
            # Ensure it's on CPU before saving
            torchaudio.save(temp_chunk_path, current_chunk_waveform.cpu(), full_sample_rate)

            # Call super_resolution with the path to the temporary chunk file
            upsampled_chunk = super_resolution(
                model,
                temp_chunk_path, # Pass the file path here as input_file
                ddim_steps=50,
                guidance_scale=3.5,
            )
            
            # Handle if upsampled_chunk is a numpy.ndarray AND ensure 2D tensor
            if isinstance(upsampled_chunk, np.ndarray):
                upsampled_chunk = torch.from_numpy(upsampled_chunk)
            
            # Ensure it's on CPU and float32, and squeeze any extra dimensions
            upsampled_chunk = upsampled_chunk.cpu().to(torch.float32)
            
            # Squeeze extra dimensions to ensure it's (channels, samples)
            if upsampled_chunk.ndim > 2:
                upsampled_chunk = upsampled_chunk.squeeze(0) # Squeeze the batch dimension if it exists
            
            # Also ensure it's 2D (channels, samples). If it's 1D (samples), make it (1, samples)
            if upsampled_chunk.ndim == 1:
                upsampled_chunk = upsampled_chunk.unsqueeze(0) # Add channel dimension for mono
            
            upsampled_chunks.append(upsampled_chunk)
            
            try:
                os.remove(temp_chunk_path)
            except Exception as e:
                log(f"Error cleaning up temporary chunk file {temp_chunk_path}: {e}")
        
        try:
            if not os.listdir(temp_chunk_dir):
                os.rmdir(temp_chunk_dir)
        except Exception as e:
            log(f"Error cleaning up temporary chunk directory {temp_chunk_dir}: {e}")


        log("All chunks processed. Concatenating upsampled audio...")
        # Concatenate all upsampled chunks along the last dimension (time)
        final_upsampled_waveform = torch.cat(upsampled_chunks, dim=-1)

        original_filename = os.path.basename(input_audio_path)
        name, _ = os.path.splitext(original_filename)
        output_audio_path = os.path.join(output_audio_dir, f"{name}_upscaled.flac")

        log(f"Saving final upsampled audio to '{output_audio_path}' (48kHz)...")
        torchaudio.save(output_audio_path, final_upsampled_waveform.cpu(), 48000, format="flac")
        log(f"Upsampled audio saved successfully to {output_audio_path}")
        if completion_callback:
            completion_callback(True)

    except ImportError as e:
        log(f"Error: Required library not found. Please ensure torch, torchaudio, audiosr, pydub, and subprocess are installed/available.")
        log(f"Details: {e}")
        import traceback
        log(traceback.format_exc())
        if completion_callback:
            completion_callback(False)
    except Exception as e:
        log(f"An unexpected error occurred during super-resolution: {e}")
        import traceback
        log(traceback.format_exc())
        if completion_callback:
            completion_callback(False)
    finally:
        # Cleanup temporary WAV file created during conversion (if any)
        if temp_wav_created and os.path.exists(processed_input_path):
            try:
                os.remove(processed_input_path)
                log(f"Cleaned up temporary WAV file: {processed_input_path}")
            except Exception as e:
                log(f"Error cleaning up temporary WAV file {processed_input_path}: {e}")
        # --- NEW: Cleanup temporary repaired MP4 file (if any) ---
        if temp_repaired_mp4_created and os.path.exists(repaired_mp4_path):
            try:
                os.remove(repaired_mp4_path)
                log(f"Cleaned up temporary repaired MP4 file: {repaired_mp4_path}")
            except Exception as e:
                log(f"Error cleaning up temporary repaired MP4 file {repaired_mp4_path}: {e}")
        # --- END NEW cleanup ---



class AudioSR_GUI:
    def __init__(self, master):
        self.master = master
        master.title("Audio Super-Resolution")

        self.input_file_path = tk.StringVar()
        self.output_dir_path = tk.StringVar()

        tk.Label(master, text="Input Audio File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(master, textvariable=self.input_file_path, width=60, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse...", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=5)

        tk.Label(master, text="Output Directory:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(master, textvariable=self.output_dir_path, width=60, state='readonly').grid(row=1, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse...", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)

        self.output_dir_path.set(os.path.join(os.path.expanduser("~"), "AudioSR_Upscaled"))

        self.start_button = tk.Button(master, text="Start Super-Resolution", command=self.start_super_resolution, height=2, bg="green", fg="white")
        
        self.start_button.grid(row=2, column=0, columnspan=3, pady=10)

        tk.Label(master, text="Processing Log:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.log_text = tk.Text(master, height=15, width=80, state='disabled')
        self.log_text.grid(row=4, column=0, columnspan=3, padx=5, pady=5)
        self.log_text_scroll = tk.Scrollbar(master, command=self.log_text.yview)
        self.log_text_scroll.grid(row=4, column=3, sticky='ns', padx=0, pady=5)
        self.log_text['yscrollcommand'] = self.log_text_scroll.set


    def browse_input_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Input Audio File",
            filetypes=[("Audio Files", "*.wav *.mp3 *.mp4"), ("All Files", "*.*")]
        )
        if file_path:
            self.input_file_path.set(file_path)
            self.log_message(f"Selected input file: {file_path}")

    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_dir_path.set(dir_path)
            self.log_message(f"Selected output directory: {dir_path}")

    def log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.master.update_idletasks()

    def start_super_resolution(self):
        input_path = self.input_file_path.get()
        output_dir = self.output_dir_path.get()

        if not input_path:
            messagebox.showwarning("Input Missing", "Please select an input audio file.")
            return
        if not output_dir:
            messagebox.showwarning("Output Missing", "Please select an output directory.")
            return

        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log_message("Starting AudioSR process...")
        self.start_button.config(state='disabled', text="Processing...")

        self.sr_thread = threading.Thread(
            target=test_audiosr_super_resolution,
            args=(input_path, output_dir, self.log_message, self.on_super_resolution_complete)
        )
        self.sr_thread.start()

    def on_super_resolution_complete(self, success):
        self.master.after(0, lambda: self.start_button.config(state='normal', text="Start Super-Resolution"))
        if success:
            self.master.after(0, lambda: messagebox.showinfo("Success", "Audio super-resolution completed successfully!"))
        else:
            self.master.after(0, lambda: messagebox.showerror("Error", "Audio super-resolution failed. Check the log for details."))


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioSR_GUI(root)
    root.mainloop()