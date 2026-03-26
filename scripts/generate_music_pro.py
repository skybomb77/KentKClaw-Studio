import torch
import argparse
import os
import random
import numpy as np
from scipy.io.wavfile import write

# --- Original DSP Engine as Fallback ---
SAMPLE_RATE = 44100
def generate_oscillator(freq, duration, volume=0.5, osc_type='sine'):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    if osc_type == 'sine':
        wave = volume * np.sin(2 * np.pi * freq * t)
    elif osc_type == 'square':
        wave = volume * np.sign(np.sin(2 * np.pi * freq * t))
    elif osc_type == 'saw':
        wave = volume * (2 * (t * freq - np.floor(0.5 + t * freq)))
    else:
        wave = volume * np.sin(2 * np.pi * freq * t)
        
    envelope = np.concatenate([
        np.linspace(0, 1, int(SAMPLE_RATE * 0.02)),
        np.ones(int(SAMPLE_RATE * (duration - 0.04))),
        np.linspace(1, 0, int(SAMPLE_RATE * 0.02))
    ])
    if len(envelope) < len(wave):
        envelope = np.pad(envelope, (0, len(wave) - len(envelope)), 'constant')
    return wave * envelope[:len(wave)]

def create_dsp_beat(duration, style, mood=""):
    total_samples = int(SAMPLE_RATE * duration)
    track = np.zeros(total_samples)
    bpm = random.randint(80, 120)
    osc_type = 'sine'
    scale = [261.63, 293.66, 311.13, 349.23, 392.00, 415.30, 466.16]
    reverb_amount = 0.3
    bit_crush = False
    
    if "Techno" in style or "Cyberpunk" in style: 
        bpm = random.randint(124, 138); osc_type = 'square'; reverb_amount = 0.15
    elif "Lofi" in style: 
        bpm = random.randint(72, 88); osc_type = 'sine'; reverb_amount = 0.6; bit_crush = True
    elif "Cinematic" in style or "Epic" in style:
        bpm = random.randint(55, 75); osc_type = 'saw'; reverb_amount = 0.8
    elif "Acoustic" in style:
        bpm = random.randint(95, 115); osc_type = 'sine'; reverb_amount = 0.4

    beat_dur = 60 / bpm
    samples_per_beat = int(SAMPLE_RATE * beat_dur)
    
    for i in range(int(duration / beat_dur)):
        pos = i * samples_per_beat
        if pos >= total_samples: break
        if i % 4 == 0 or (i % 8 == 6 and random.random() > 0.5):
            kick_len = int(SAMPLE_RATE * 0.2); t = np.linspace(0, 0.2, kick_len)
            freq_env = 120 * np.exp(-40 * t) + 35; kick = np.tanh(0.9 * np.sin(2 * np.pi * freq_env * t) * np.exp(-12 * t) * 1.5)
            end = min(pos + kick_len, total_samples); track[pos:end] += kick[:end-pos]
        if i % 4 == 1 or i % 4 == 3:
            snare_len = int(SAMPLE_RATE * 0.15); noise = np.random.normal(0, 0.2, snare_len); env = np.exp(-20 * np.linspace(0, 0.15, snare_len))
            t_s = np.linspace(0, 0.15, snare_len); body = 0.1 * np.sin(2 * np.pi * 200 * t_s) * env
            end = min(pos + snare_len, total_samples); track[pos:end] += (noise * env + body)[:end-pos]
        for sub in range(2): 
            h_pos = pos + sub * (samples_per_beat // 2); h_len = int(SAMPLE_RATE * 0.04); velocity = 0.08 if sub == 0 else 0.04
            hat = np.random.normal(0, velocity, h_len) * np.exp(-100 * np.linspace(0, 0.04, h_len))
            if h_pos < total_samples: end = min(h_pos + h_len, total_samples); track[h_pos:end] += hat[:end-h_pos]
            
    progression = random.choice([[0, 3, 4, 0], [0, 4, 5, 3], [5, 2, 0, 4]])
    measure_dur = beat_dur * 4
    for m in range(int(duration / measure_dur) + 1):
        m_pos = m * int(SAMPLE_RATE * measure_dur)
        if m_pos >= total_samples: break
        chord_root = scale[progression[m % len(progression)]]
        for interval in [1.0, 1.2, 1.5, 1.8]:
            vol = 0.12 if interval < 1.6 else 0.06
            chord_wave = generate_oscillator(chord_root * interval, measure_dur, volume=vol, osc_type=osc_type)
            end = min(m_pos + len(chord_wave), total_samples); track[m_pos:end] += chord_wave[:end-m_pos]
        for step in range(8):
            note_pos = m_pos + step * (samples_per_beat // 2)
            if note_pos >= total_samples: break
            note_wave = generate_oscillator(scale[random.choice([0, 2, 4, 6])] * 2, beat_dur/2, volume=0.05, osc_type='sine')
            end = min(note_pos + len(note_wave), total_samples); track[note_pos:end] += note_wave[:end-note_pos]

    delay_samples = int(SAMPLE_RATE * 0.1); reverb = np.zeros(len(track) + delay_samples)
    reverb[:len(track)] = track; reverb[delay_samples:] += track * reverb_amount; track = reverb[:len(track)]
    if bit_crush: track = np.round(track * 8) / 8 + np.random.normal(0, 0.005, len(track))
    return track

def forge_professional_music(style, mood, duration, output_path):
    # Dynamic import to avoid crash if torchaudio/ffmpeg fails
    try:
        import torchaudio
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write
    except Exception as e:
        raise ImportError(f"Dependencies failed to load: {e}")
    
    print(f"--- Pro Forge Starting: {style} ({duration}s) ---")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    model = MusicGen.get_pretrained('facebook/musicgen-small')
    model.set_generation_params(duration=duration)
    descriptions = [f"{style}, {mood}, high fidelity, professional studio mix, masterpiece, 44.1kHz"]
    
    wav = model.generate(descriptions)
    base_path = os.path.splitext(output_path)[0]
    audio_write(base_path, wav[0].cpu(), model.sample_rate, strategy="loudness")
    print(f"--- Pro Forge Complete: {output_path} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", type=str, default="Lofi Hip Hop")
    parser.add_argument("--mood", type=str, default="chill vibes")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    try:
        forge_professional_music(args.style, args.mood, args.duration, args.output)
    except Exception as e:
        print(f"Pro Engine Error: {e}")
        print("Falling back to High-Fidelity DSP Engine...")
        audio = create_dsp_beat(args.duration, args.style)
        if np.max(np.abs(audio)) > 0: audio = audio / np.max(np.abs(audio))
        write(args.output, SAMPLE_RATE, audio.astype(np.float32))
        print(f"DSP Forge Complete: {args.output}")
