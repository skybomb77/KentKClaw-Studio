# YouTube Auto-Generator
# Config
TARGET_DAILY_SINGLES = 10
TARGET_COMPILATION_SIZE = 20
STYLE_CHANGE_SIZE = 50

STYLES = [
    "Neon Nostalgia (Cyberpunk Lofi)",
    "Rainy Cafe (Jazz Lofi)",
    "Forest Dreams (Nature Lofi)",
    "Space Drift (Ambient Lofi)"
]

def get_current_style(total_count):
    index = (total_count // STYLE_CHANGE_SIZE) % len(STYLES)
    return STYLES[index]
BASE_DIR = "KentKClaw-Studio/audio_output/music"
VIDEO_DIR = "KentKClaw-Studio/audio_output/video"
TRACKER_FILE = "KentKClaw-Studio/production/tracker/status.md"

import os
import random
import shutil

import os
import random
import subprocess
import time

def generate_video(filename, title):
    print(f"[{time.strftime('%H:%M:%S')}] Processing {filename}...")
    
    # 1. Generate Music (Pure Ambient)
    # We call a modified generate_neon.py that accepts a seed/filename
    # For now, let's assume generate_neon.py is updated to take args or we just cp the script
    # Simulating generation by calling the script (it currently outputs fixed filename, needs tweaking)
    # Let's just rename the output for now
    subprocess.run(["python3", "KentKClaw-Studio/scripts/generate_neon.py"], check=True)
    
    # Move and rename the wave
    raw_wav = "KentKClaw-Studio/audio_output/neon_nostalgia_pure.wav"
    target_wav = f"KentKClaw-Studio/audio_output/music/{filename}.wav"
    subprocess.run(["mv", raw_wav, target_wav], check=True)
    
    # 2. Generate Cover (ImageMagick)
    cover_jpg = f"KentKClaw-Studio/audio_output/video/{filename}.jpg"
    cmd_cover = [
        "magick", "-size", "1920x1080", "xc:#000022",
        "-fill", "transparent", "-stroke", "#FF00FF", "-strokewidth", "2",
        "-draw", "rectangle 400,200 1520,880",
        "-font", "/System/Library/Fonts/Supplemental/Arial.ttf",
        "-fill", "#00FFFF", "-stroke", "none", "-pointsize", "100", "-gravity", "center", "-annotate", "+0-60", title,
        "-fill", "#FF00FF", "-pointsize", "40", "-gravity", "center", "-annotate", "+0+80", "Kent & KClaw Studio",
        "-fill", "#FFFFFF", "-pointsize", "20", "-gravity", "south", "-annotate", "+0+40", "Lofi Chill Beats",
        "-blur", "0x1", "-level", "0%,100%,1.2",
        cover_jpg
    ]
    subprocess.run(cmd_cover, check=True)
    
    # 3. Render Visualizer Video (FFmpeg)
    output_mp4 = f"KentKClaw-Studio/audio_output/video/{filename}.mp4"
    cmd_ffmpeg = [
        "ffmpeg", "-y", "-i", cover_jpg, "-i", target_wav,
        "-filter_complex", "[1:a]showwaves=s=1280x200:mode=line:colors=Cyan[v];[0:v][v]overlay=x=(W-w)/2:y=H-h-100[outv]",
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-shortest",
        output_mp4
    ]
    # Suppress output for cleaner logs
    subprocess.run(cmd_ffmpeg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    
    print(f"[{time.strftime('%H:%M:%S')}] Generated: {output_mp4}")
    return output_mp4

# Logic for daily run
print("🚀 Starting Daily Production: Neon Nostalgia Phase")

# Generate 6 more videos to reach 10 (we have some, but let's make fresh consistent ones)
for i in range(1, 7):
    title = f"Neon Nostalgia Vol.{i}"
    filename = f"neon_nostalgia_vol_{i}"
    generate_video(filename, title)
    
print("✅ Daily Batch Complete.")
