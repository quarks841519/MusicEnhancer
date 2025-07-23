# Audio Super-Resolution GUI

A simple GUI application for performing audio super-resolution using the AudioSR library.

## Features
- Converts various audio formats (MP4, MP3) to WAV for processing.
- Includes an FFmpeg repair step for MP4 files.
- Performs audio super-resolution using the AudioSR model.
- Processes audio in chunks to handle larger files.
- Provides a graphical user interface for easy interaction.

## Dependencies & Acknowledgments

This project heavily relies on and builds upon the excellent work of the following open-source projects:

* **AudioSR Library**: The core audio super-resolution functionality is provided by the `audiosr` library.
    * [https://github.com/DCASE-Task6/AudioSR]
  
* **PyTorch & TorchAudio**: Used for deep learning operations and efficient audio handling.
    * [https://pytorch.org/](https://pytorch.org/)

* **Pydub**: Utilized for robust audio format conversion.
    * [https://github.com/jiaaro/pydub](https://github.com/jiaaro/pydub)

* **FFmpeg**: An essential dependency for audio format conversions and repairs. Please ensure FFmpeg is installed and accessible in your system's PATH.
    * [https://ffmpeg.org/](https://ffmpeg.org/)

* **Tkinter**: The standard Python GUI toolkit used for the application's interface.

## Installation

1.  **Install FFmpeg**:
    Download and install FFmpeg from their official website or use a package manager (e.g., `brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Ubuntu, or download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)).

2.  **Clone the repository**:
    ```bash
    git clone [Your-GitHub-Repo-URL]
    cd [your-repo-name]
    ```

3.  **Create a virtual environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

4.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    (You'll need to create a `requirements.txt` file. See below.)

## Usage

```bash
python audioProcessorSuperResolution4.py

# Music Processing Tools

This repository contains two Python scripts designed to assist with music and audio processing:

1.  **Demucs Music Enhancer (`demucs_enhancer.py`):** Utilizes the Demucs library to separate audio into stems (vocals, drums, bass, other) and then recombines them into an "enhanced" mix.
2.  **FFmpeg MP4 Repair Tool (`ffmpegrepair.py`):** A simple GUI tool to repair MP4 video files using FFmpeg, primarily by adding `faststart` metadata for better streaming/playback.



## Features

### Demucs Music Enhancer
* **Stem Separation:** Automatically separates an input audio/video file into vocals, drums, bass, and other instruments using Demucs.
* **Automatic Recombination:** After separation, it intelligently finds the generated stems and recombines them into a single, enhanced WAV file.
* **Versatile Input:** Supports various audio and video formats that Demucs can handle (MP3, WAV, M4A, MP4, etc.).

### FFmpeg MP4 Repair Tool
* **GUI-based:** Simple graphical interface for selecting input and output files.
* **MP4 Repair:** Uses `ffmpeg` to repair MP4 files by ensuring the `moov` atom (metadata) is at the beginning of the file, which can resolve playback issues or prepare files for streaming.

---

## Dependencies

Both scripts rely on external command-line tools and Python libraries.

### External Tools
* **FFmpeg**: Essential for `ffmpegrepair.py` and for `demucs_enhancer.py`'s `pydub` functionality to handle various audio formats.
    * **Installation:** Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) or use your system's package manager (e.g., `brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Ubuntu). Ensure it's added to your system's PATH.
* **Demucs**: Required for `demucs_enhancer.py`.
    * **Installation:** Follow the instructions on the official Demucs GitHub page, usually installed via `pip`:
        `pip install -U demucs`

### Python Libraries
The Python libraries can be installed via `pip`. It's highly recommended to use a virtual environment.

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate