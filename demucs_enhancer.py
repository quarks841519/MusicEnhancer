import argparse
import os
import subprocess
import sys
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

def run_demucs(input_file, output_dir):
    """Run Demucs separation."""
    command = ['demucs', input_file, '-o', output_dir]
    print(f"[INFO] Running Demucs: {' '.join(command)}")
    
    result = subprocess.run(command, capture_output=True)
    
    if result.returncode != 0:
        print("[ERROR] Demucs failed:")
        print(result.stderr.decode())
        sys.exit(result.returncode)
    else:
        print("[INFO] Demucs separation complete.")

def combine_stems(song_path, output_dir):
    """Auto-detect stem folder and combine into a single audio file."""
    print(f"[DEBUG] Input file: {song_path}")
    print(f"[DEBUG] Output directory: {output_dir}")
    
    # Extract base filename (e.g., MelleMelle_repaired)
    track_name = os.path.splitext(os.path.basename(song_path))[0]
    print(f"[DEBUG] Expecting track name folder: {track_name}")

    # Find available model folders in the output directory
    model_dirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    print(f"[DEBUG] Found model folders: {model_dirs}")

    stems_path = None
    for model_dir in model_dirs:
        candidate_path = os.path.join(output_dir, model_dir, track_name)
        print(f"[DEBUG] Checking for folder: {candidate_path}")
        if os.path.exists(candidate_path):
            stems_path = candidate_path
            print(f"[INFO] Found stems folder: {stems_path}")
            break

    if stems_path is None:
        print(f"[ERROR] Couldn't find stems folder for track '{track_name}' in any model folder.")
        sys.exit(1)

    # Load and mix stems
    try:
        vocals = AudioSegment.from_file(os.path.join(stems_path, "vocals.wav"))
        drums  = AudioSegment.from_file(os.path.join(stems_path, "drums.wav"))
        bass   = AudioSegment.from_file(os.path.join(stems_path, "bass.wav"))
        other  = AudioSegment.from_file(os.path.join(stems_path, "other.wav"))
    except FileNotFoundError as e:
        print(f"[ERROR] Missing stem file: {e.filename}")
        sys.exit(1)
    except CouldntDecodeError:
        print("[ERROR] Couldn't decode stem. Make sure ffmpeg is installed and in PATH.")
        sys.exit(1)

    print("[INFO] Overlaying stems to create enhanced mix...")
    enhanced = vocals.overlay(drums).overlay(bass).overlay(other)

    output_file = os.path.join(stems_path, "combined_enhanced.wav")
    print(f"[INFO] Saving enhanced output to: {output_file}")
    enhanced.export(output_file, format="wav")
    print("[✅] Combined enhanced audio saved successfully!")

def main():
    parser = argparse.ArgumentParser(description="🎧 Demucs Music Enhancer: Separate and Recombine music stems")
    parser.add_argument("input", help="Input audio/video file (mp3, wav, m4a, mp4, etc.)")
    parser.add_argument("-o", "--output", default="separated_output", help="Output folder for stems and final mix")

    args = parser.parse_args()

    print("[INFO] Starting Demucs Music Enhancer...")
    run_demucs(args.input, args.output)
    combine_stems(args.input, args.output)

if __name__ == "__main__":
    main()
