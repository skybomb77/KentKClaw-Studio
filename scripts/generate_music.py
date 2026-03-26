import numpy as np
from scipy.io.wavfile import write
import argparse
import os
import random

# Configuration
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

def create_beat(duration, style, mood=""):
    total_samples = int(SAMPLE_RATE * duration)
    track = np.zeros(total_samples)
    
    # 基礎參數設定
    bpm = random.randint(80, 120)
    osc_type = 'sine'
    scale = [261.63, 293.66, 311.13, 349.23, 392.00, 415.30, 466.16] # C Minor
    
    # === 質感增強參數 ===
    reverb_amount = 0.3
    bit_crush = False
    
    if "Techno" in style or "Cyberpunk" in style: 
        bpm = random.randint(124, 138)
        osc_type = 'square'
        reverb_amount = 0.15
    elif "Lofi" in style: 
        bpm = random.randint(72, 88)
        osc_type = 'sine'
        reverb_amount = 0.6
        bit_crush = True
    elif "Cinematic" in style or "Epic" in style:
        bpm = random.randint(55, 75)
        osc_type = 'saw'
        reverb_amount = 0.8
    elif "Acoustic" in style:
        bpm = random.randint(95, 115)
        osc_type = 'sine'
        reverb_amount = 0.4

    beat_dur = 60 / bpm
    samples_per_beat = int(SAMPLE_RATE * beat_dur)
    
    # 鼓組生成 (質感改良版)
    for i in range(int(duration / beat_dur)):
        pos = i * samples_per_beat
        if pos >= total_samples: break
        
        # Kick (深層飽和處理)
        if i % 4 == 0 or (i % 8 == 6 and random.random() > 0.5):
            kick_len = int(SAMPLE_RATE * 0.2)
            t = np.linspace(0, 0.2, kick_len)
            freq_env = 120 * np.exp(-40 * t) + 35 
            kick = 0.9 * np.sin(2 * np.pi * freq_env * t) * np.exp(-12 * t)
            # 軟剪裁增加暖度
            kick = np.tanh(kick * 1.5)
            end = min(pos + kick_len, total_samples)
            track[pos:end] += kick[:end-pos]
            
        # Snare (帶有層次感的噪聲)
        if i % 4 == 1 or i % 4 == 3:
            snare_len = int(SAMPLE_RATE * 0.15)
            noise = np.random.normal(0, 0.2, snare_len)
            env = np.exp(-20 * np.linspace(0, 0.15, snare_len))
            # 混入一點 Saw 波增加顆粒感
            t_s = np.linspace(0, 0.15, snare_len)
            body = 0.1 * np.sin(2 * np.pi * 200 * t_s) * env
            snare = (noise * env) + body
            end = min(pos + snare_len, total_samples)
            track[pos:end] += snare[:end-pos]

        # Hi-Hat (動態力度變換)
        for sub in range(2): 
            h_pos = pos + sub * (samples_per_beat // 2)
            if h_pos >= total_samples: break
            h_len = int(SAMPLE_RATE * 0.04)
            velocity = 0.08 if sub == 0 else 0.04 # 強弱拍
            h_noise = np.random.normal(0, velocity, h_len)
            h_env = np.exp(-100 * np.linspace(0, 0.04, h_len))
            hat = h_noise * h_env
            end = min(h_pos + h_len, total_samples)
            track[h_pos:end] += hat[:end-h_pos]
            
    # 旋律與和弦生成 (和聲增強)
    progression = random.choice([
        [0, 3, 4, 0], 
        [0, 4, 5, 3], 
        [5, 2, 0, 4], # 加入 II 級和弦增加專業感
    ])
    
    measure_dur = beat_dur * 4
    for m in range(int(duration / measure_dur) + 1):
        m_pos = m * int(SAMPLE_RATE * measure_dur)
        if m_pos >= total_samples: break
        
        chord_root = scale[progression[m % len(progression)]]
        
        # 豐富的和弦配置 (7和弦感)
        intervals = [1.0, 1.2, 1.5, 1.8] # Root, m3, 5, m7
        for interval in intervals:
            vol = 0.12 if interval < 1.6 else 0.06
            chord_wave = generate_oscillator(chord_root * interval, measure_dur, volume=vol, osc_type=osc_type)
            end = min(m_pos + len(chord_wave), total_samples)
            track[m_pos:end] += chord_wave[:end-m_pos]
            
        # 增加流暢的琶音
        arp_notes = [0, 2, 4, 6]
        for step in range(8):
            note_pos = m_pos + step * (samples_per_beat // 2)
            if note_pos >= total_samples: break
            arp_freq = scale[random.choice(arp_notes)] * 2
            arp_wave = generate_oscillator(arp_freq, beat_dur/2, volume=0.05, osc_type='sine')
            end = min(note_pos + len(arp_wave), total_samples)
            track[note_pos:end] += arp_wave[:end-note_pos]

    # === 後端處理模組 (DSP) ===
    # 1. 簡單的殘響效應 (Reverb) - 模擬空間感
    delay_samples = int(SAMPLE_RATE * 0.1)
    reverb = np.zeros(len(track) + delay_samples)
    reverb[:len(track)] = track
    reverb[delay_samples:] += track * reverb_amount
    track = reverb[:len(track)]

    # 2. Lofi 特效 (Bitcrush/Vinyl Hiss)
    if bit_crush:
        # 降低採樣率與量化
        track = np.round(track * 8) / 8 # 3-bit 質感
        # 加入一點黑膠底噪
        hiss = np.random.normal(0, 0.005, len(track))
        track += hiss

    return track

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", type=str, default="Lofi")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", type=str, required=True)
    args = parser.parse_args()

    print(f"Forging {args.style} track for {args.duration}s with variations...")
    audio = create_beat(args.duration, args.style)
    
    # Normalize
    if np.max(np.abs(audio)) > 0:
        audio = audio / np.max(np.abs(audio))
    
    write(args.output, SAMPLE_RATE, audio.astype(np.float32))
    print("Done.")
