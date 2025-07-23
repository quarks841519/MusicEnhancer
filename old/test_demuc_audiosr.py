import torch
import torchaudio
from audiosr import build_model, super_resolution
import os
from pydub import AudioSegment
# REMOVE THIS LINE: from pydub.utils import get_resource_path
# REMOVE THIS LINE: import subprocess # No longer explicitly needed here for pydub's core function

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
        # Pydub can usually infer format, but explicitly stating for MP4 is good.
        # The [1:] slice is to remove the leading dot from the extension (e.g., ".mp4" -> "mp4")
        audio = AudioSegment.from_file(input_file_path, format=os.path.splitext(input_file_path)[1][1:])
        audio.export(wav_path, format="wav")
        print(f"Conversion successful. Temporary WAV saved to: '{wav_path}'")
        return wav_path
    except Exception as e:
        print(f"Error during conversion of '{input_file_path}' to WAV: {e}")
        print("Please ensure FFmpeg is installed and accessible in your system's PATH.")
        return None

def test_audiosr_super_resolution(input_audio_path, output_audio_dir="audiosr_output"):
    """
    Tests the AudioSR super_resolution function with a given input audio file.
    Automatically converts non-WAV files to WAV.

    Args:
        input_audio_path (str): Path to the low-resolution input audio file (can be MP4, MP3, WAV).
        output_audio_dir (str): Directory to save the upscaled audio file.
    """
    if not os.path.exists(input_audio_path):
        print(f"Error: Input audio file not found at '{input_audio_path}'")
        print("Please provide a valid path to an audio file.")
        return

    # Convert to WAV if necessary
    processed_input_path = input_audio_path
    if not input_audio_path.lower().endswith(".wav"):
        processed_input_path = convert_to_wav(input_audio_path)
        if processed_input_path is None:
            print("Failed to prepare input audio. Exiting.")
            return

    os.makedirs(output_audio_dir, exist_ok=True)

    try:
        print(f"Loading AudioSR model (basic)...")
        model = build_model(model_name="basic")
        print("AudioSR model loaded.")

        print(f"Loading input audio from '{processed_input_path}'...")
        waveform, sample_rate = torchaudio.load(processed_input_path)
        print(f"Input audio loaded: Sample Rate = {sample_rate} Hz, Channels = {waveform.shape[0]}, Duration (s) = {waveform.shape[1] / sample_rate:.2f}")

        # Ensure the waveform is mono if the model expects it
        if waveform.shape[0] > 1:
            print("Converting stereo input to mono...")
            waveform = torch.mean(waveform, dim=0, keepdim=True)
            print(f"Converted to mono: Channels = {waveform.shape[0]}")

        print("Performing audio super-resolution (this might take a while)...")
        upsampled_waveform = super_resolution(
            model,
            waveform,
            sample_rate,
            target_sample_rate=48000,
            ddim_steps=50,
            guidance_scale=3.5,
        )
        print("Audio super-resolution complete.")

        # Save the upsampled audio
        original_filename = os.path.basename(input_audio_path)
        name, _ = os.path.splitext(original_filename) # Use original filename for naming output
        output_audio_path = os.path.join(output_audio_dir, f"{name}_upscaled.wav")

        print(f"Saving upsampled audio to '{output_audio_path}' (48kHz)...")
        torchaudio.save(output_audio_path, upsampled_waveform, 48000)
        print(f"Upsampled audio saved successfully to {output_audio_path}")

    except ImportError as e:
        print(f"Error: Required library not found. Please ensure torch, torchaudio, audiosr, and pydub are installed.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during super-resolution: {e}")

if __name__ == "__main__":
    # --- IMPORTANT: Configure these paths ---
    # 1. Path to your low-resolution input audio file (e.g., a .wav, .mp3, or .mp4)
    #    Make sure this file exists and is accessible.
    #    AudioSR is designed for input bandwidths of 2 kHz to 16 kHz.
    #    e.g., an audio file recorded at 16kHz or lower.
    test_file = "/Users/vimalmani/Music/Music/test.mp4" # <--- Update this to your actual MP4 path

    # 2. Directory where the upscaled output will be saved
    output_directory = "/Users/vimalmani/Music/Music/my_upscaled_audio_tests/"
    # --- End configuration ---

    print("Starting AudioSR test program.")
    test_audiosr_super_resolution(test_file, output_directory)
    print("AudioSR test program finished.")

    #    e.g., an audio file recorded at 16kHz or lower.
    #test_file = "/Users/vimalmani/Music/Music/test.mp4" # <--- Update this to your actual MP4 path

    # 2. Directory where the upscaled output will be saved
    #output_directory = "/Users/vimalmani/Music/Music/my_upscaled_audio_tests"
    # --- End configuration ---

   