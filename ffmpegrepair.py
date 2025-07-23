import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

def repair_video_ffmpeg(input_path, output_path):
    command = ['ffmpeg', '-i', input_path, '-c', 'copy', '-movflags', 'faststart', output_path]
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def select_file_and_repair():
    root = tk.Tk()
    root.withdraw()  # Hide root window

    input_file = filedialog.askopenfilename(
        title='Select input video file',
        filetypes=[('MP4 files', '*.mp4'), ('All files', '*.*')]
    )
    if not input_file:
        messagebox.showinfo('Info', 'No file selected')
        return

    output_file = filedialog.asksaveasfilename(
        title='Save repaired video as',
        defaultextension='.mp4',
        filetypes=[('MP4 files', '*.mp4')]
    )
    if not output_file:
        messagebox.showinfo('Info', 'No output file specified')
        return

    success = repair_video_ffmpeg(input_file, output_file)
    if success:
        messagebox.showinfo('Success', 'Video repaired and saved successfully!')
    else:
        messagebox.showerror('Error', 'Failed to repair the video with ffmpeg.')

# To run the GUI, uncomment below lines
if __name__ == '__main__':
     select_file_and_repair()
