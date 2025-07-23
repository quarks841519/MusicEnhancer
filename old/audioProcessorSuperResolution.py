import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import torch
import torchaudio
from audiosr import build_model, super_resolution
from pydub import AudioSegment
import math # Added for chunking calculations

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
    if not input_audio_path.lower().endswith(".wav"):
        log(f"Input is not WAV. Converting '{input_audio_path}' to WAV...")
        processed_input_path = convert_to_wav(input_audio_path)
        if processed_input_path is None:
            log("Failed to prepare input audio. Exiting.")
            if completion_callback:
                completion_callback(False)
            return

    os.makedirs(output_audio_dir, exist_ok=True)

    try:
        log(f"Loading AudioSR model (basic)...")
        model = build_model(model_name="basic")
        log("AudioSR model loaded.")

        # Load the full audio initially to get its properties for chunking
        # The super_resolution function will then process chunks from temporary files
        log(f"Loading full input audio for chunking from '{processed_input_path}'...")
        full_waveform, full_sample_rate = torchaudio.load(processed_input_path)
        log(f"Full audio loaded: Sample Rate = {full_sample_rate} Hz, Channels = {full_waveform.shape[0]}, Duration (s) = {full_waveform.shape[1] / full_sample_rate:.2f}")

        # Convert to mono if necessary for chunking, as AudioSR might expect mono input
        if full_waveform.shape[0] > 1:
            log("Converting full stereo input to mono for chunking...")
            full_waveform = torch.mean(full_waveform, dim=0, keepdim=True)
            log(f"Converted to mono: Channels = {full_waveform.shape[0]}")

        # Define chunk duration (e.g., 10 seconds to balance performance and memory)
        # The AudioSR warning suggested 5.12s for best performance, 10.24s as max.
        # Using 10.0s for a balance of chunk count and memory.
        chunk_duration_seconds = 10.0
        chunk_length_samples = int(chunk_duration_seconds * full_sample_rate)

        total_samples = full_waveform.shape[1]
        num_chunks = math.ceil(total_samples / chunk_length_samples)
        upsampled_chunks = []
        
        # Create a temporary directory for audio chunks
        temp_chunk_dir = os.path.join("temp_wavs", "chunks")
        os.makedirs(temp_chunk_dir, exist_ok=True)

        log(f"Performing audio super-resolution in {num_chunks} chunks of ~{chunk_duration_seconds:.2f} seconds...")

        for i in range(num_chunks):
            start_sample = i * chunk_length_samples
            end_sample = min((i + 1) * chunk_length_samples, total_samples)
            
            current_chunk_waveform = full_waveform[:, start_sample:end_sample]
            
            chunk_filename = f"chunk_{i:03d}.wav"
            temp_chunk_path = os.path.join(temp_chunk_dir, chunk_filename)

            log(f"Processing chunk {i+1}/{num_chunks} (samples {start_sample}-{end_sample})...")
            
            # Save the current chunk to a temporary WAV file
            torchaudio.save(temp_chunk_path, current_chunk_waveform, full_sample_rate)

            # Call super_resolution with the path to the temporary chunk file
            upsampled_chunk = super_resolution(
                model,
                temp_chunk_path, # Pass the file path here
                ddim_steps=50,
                guidance_scale=3.5,
            )
            upsampled_chunks.append(upsampled_chunk)
            
            # Clean up the temporary chunk file immediately after processing
            try:
                os.remove(temp_chunk_path)
            except Exception as e:
                log(f"Error cleaning up temporary chunk file {temp_chunk_path}: {e}")
        
        # Clean up the temporary chunk directory if empty
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
        output_audio_path = os.path.join(output_audio_dir, f"{name}_upscaled.wav")

        # The AudioSR model typically outputs at 48kHz, so save with that sample rate.
        log(f"Saving final upsampled audio to '{output_audio_path}' (48kHz)...")
        torchaudio.save(output_audio_path, final_upsampled_waveform, 48000)
        log(f"Upsampled audio saved successfully to {output_audio_path}")
        if completion_callback:
            completion_callback(True)

    except ImportError as e:
        log(f"Error: Required library not found. Please ensure torch, torchaudio, audiosr, and pydub are installed.")
        log(f"Details: {e}")
        if completion_callback:
            completion_callback(False)
    except Exception as e:
        log(f"An unexpected error occurred during super-resolution: {e}")
        if completion_callback:
            completion_callback(False)
    finally:
        # Clean up temporary WAV if created (the initial conversion from mp4/mp3)
        if processed_input_path != input_audio_path and os.path.exists(processed_input_path):
            try:
                os.remove(processed_input_path)
                log(f"Cleaned up temporary WAV file: {processed_input_path}")
            except Exception as e:
                log(f"Error cleaning up temporary WAV file {processed_input_path}: {e}")


class AudioSR_GUI:
    def __init__(self, master):
        self.master = master
        master.title("Audio Super-Resolution")

        self.input_file_path = tk.StringVar()
        self.output_dir_path = tk.StringVar()

        # Input File Selection
        tk.Label(master, text="Input Audio File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(master, textvariable=self.input_file_path, width=60, state='readonly').grid(row=0, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse...", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=5)

        # Output Directory Selection
        tk.Label(master, text="Output Directory:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        tk.Entry(master, textvariable=self.output_dir_path, width=60, state='readonly').grid(row=1, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse...", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)

        # Default output directory
        self.output_dir_path.set(os.path.join(os.path.expanduser("~"), "AudioSR_Upscaled"))

        # Start Button
        self.start_button = tk.Button(master, text="Start Super-Resolution", command=self.start_super_resolution, height=2, bg="green", fg="white")
        self.start_button.grid(row=2, column=0, columnspan=3, pady=10)

        # Log Area
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
        self.log_text.see(tk.END) # Auto-scroll to the end
        self.log_text.config(state='disabled')
        self.master.update_idletasks() # Update the GUI immediately

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
        self.log_text.delete(1.0, tk.END) # Clear previous logs
        self.log_text.config(state='disabled')
        self.log_message("Starting AudioSR process...")
        self.start_button.config(state='disabled', text="Processing...")

        # Run the super-resolution in a separate thread
        self.sr_thread = threading.Thread(
            target=test_audiosr_super_resolution,
            args=(input_path, output_dir, self.log_message, self.on_super_resolution_complete)
        )
        self.sr_thread.start()

    def on_super_resolution_complete(self, success):
        # Schedule the GUI updates to run on the main Tkinter thread
        self.master.after(0, lambda: self.start_button.config(state='normal', text="Start Super-Resolution"))
        if success:
            self.master.after(0, lambda: messagebox.showinfo("Success", "Audio super-resolution completed successfully!"))
        else:
            self.master.after(0, lambda: messagebox.showerror("Error", "Audio super-resolution failed. Check the log for details."))


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioSR_GUI(root)
    root.mainloop()
