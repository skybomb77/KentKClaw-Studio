#!/usr/bin/env python3
"""ToneForge v2 — Professional DSP Music Generator
High-quality procedural audio using advanced synthesis techniques.
"""
import numpy as np
from scipy.io.wavfile import write as write_wav
from scipy.signal import butter, lfilter, resample
import argparse, os, random, math

SAMPLE_RATE = 44100

# ─── Oscillators ───
def sine(freq, dur, sr=SAMPLE_RATE):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return np.sin(2 * np.pi * freq * t)

def saw(freq, dur, sr=SAMPLE_RATE):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return 2.0 * (t * freq - np.floor(0.5 + t * freq))

def square(freq, dur, sr=SAMPLE_RATE):
    return np.sign(sine(freq, dur, sr))

def triangle(freq, dur, sr=SAMPLE_RATE):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return 2.0 * np.abs(2.0 * (t * freq - np.floor(t * freq + 0.5))) - 1.0

def noise(dur, sr=SAMPLE_RATE):
    return np.random.uniform(-1, 1, int(sr * dur))

def supersaw(freq, dur, detune=0.005, voices=7, sr=SAMPLE_RATE):
    """Rich detuned saw wave stack"""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    wave = np.zeros_like(t)
    for i in range(voices):
        d = 1.0 + detune * (i - voices // 2) / voices
        wave += np.sin(2 * np.pi * freq * d * t)
    return wave / voices

# ─── Envelope ───
def adsr(length, attack=0.01, decay=0.1, sustain=0.7, release=0.1, sr=SAMPLE_RATE):
    total = int(sr * length)
    a = int(sr * attack)
    d = int(sr * decay)
    r = int(sr * release)
    s = max(0, total - a - d - r)
    
    env = np.concatenate([
        np.linspace(0, 1, max(a, 1)),
        np.linspace(1, sustain, max(d, 1)),
        np.full(max(s, 1), sustain),
        np.linspace(sustain, 0, max(r, 1))
    ])
    return env[:total]

# ─── Effects ───
def lowpass(signal, cutoff=3000, sr=SAMPLE_RATE, order=4):
    nyq = sr / 2
    if cutoff >= nyq:
        return signal
    b, a = butter(order, min(cutoff, nyq - 1) / nyq, btype='low')
    return lfilter(b, a, signal)

def highpass(signal, cutoff=80, sr=SAMPLE_RATE, order=2):
    nyq = sr / 2
    b, a = butter(order, cutoff / nyq, btype='high')
    return lfilter(b, a, signal)

def reverb(signal, delays=None, decays=None, sr=SAMPLE_RATE):
    """Multi-tap reverb"""
    if delays is None:
        delays = [0.029, 0.037, 0.041, 0.053, 0.067, 0.079]
    if decays is None:
        decays = [0.4, 0.3, 0.25, 0.2, 0.15, 0.1]
    
    output = signal.copy()
    for delay, decay in zip(delays, decays):
        d = int(sr * delay)
        if d < len(signal):
            padded = np.zeros(len(signal) + d)
            padded[d:d+len(signal)] += signal * decay
            if len(output) < len(padded):
                output = np.pad(output, (0, len(padded) - len(output)))
            output[:len(padded)] += padded[:len(output)]
    return output

def stereo_delay(signal, delay_time=0.3, feedback=0.3, mix=0.2, sr=SAMPLE_RATE):
    """Stereo ping-pong delay"""
    d = int(sr * delay_time)
    output = signal.copy()
    for i in range(1, 6):
        pos = d * i
        if pos >= len(output):
            break
        gain = feedback ** i * mix
        end = min(pos + len(signal), len(output))
        output[pos:end] += signal[:end-pos] * gain
    return output

def soft_clip(signal, drive=1.5):
    """Warm tube-like saturation"""
    return np.tanh(signal * drive) / drive

def chorus(signal, rate=1.5, depth=0.002, mix=0.3, sr=SAMPLE_RATE):
    """Simple chorus effect"""
    t = np.arange(len(signal)) / sr
    mod = depth * np.sin(2 * np.pi * rate * t)
    mod_samples = (mod * sr).astype(int)
    output = signal.copy()
    for i in range(len(signal)):
        j = i - int(mod_samples[i] * 100)
        if 0 <= j < len(signal):
            output[i] = signal[i] * (1 - mix) + signal[j] * mix
    return output

# ─── Generators ───
def gen_kick(bpm, sr=SAMPLE_RATE):
    dur = 60 / bpm
    t = np.linspace(0, 0.5, int(sr * 0.5))
    freq = 150 * np.exp(-30 * t) + 30
    kick = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    env = np.exp(-8 * t)
    kick = kick * env
    kick = soft_clip(kick * 1.2, 2.0)
    kick = lowpass(kick, 4000)
    return kick

def gen_snare(sr=SAMPLE_RATE):
    t = np.linspace(0, 0.2, int(sr * 0.2))
    noise_part = noise(0.2) * np.exp(-25 * t) * 0.5
    tone_part = 0.3 * np.sin(2 * np.pi * 200 * t) * np.exp(-15 * t)
    snare = noise_part + tone_part
    snare = highpass(snare, 200)
    snare = soft_clip(snare, 1.5)
    return snare

def gen_hihat(open_hat=False, sr=SAMPLE_RATE):
    dur = 0.15 if open_hat else 0.05
    t = np.linspace(0, dur, int(sr * dur))
    hat = noise(dur) * np.exp(-50 * t if not open_hat else -15 * t) * 0.15
    hat = highpass(hat, 6000)
    hat = lowpass(hat, 12000)
    return hat

def gen_bass(freq, dur, sr=SAMPLE_RATE):
    """Sub bass with warmth"""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    # Fundamental + sub harmonic
    bass = 0.6 * np.sin(2 * np.pi * freq * t)
    bass += 0.3 * np.sin(2 * np.pi * freq * 0.5 * t)
    bass += 0.1 * saw(freq, dur) * np.exp(-3 * t)
    env = adsr(dur, 0.005, 0.1, 0.8, 0.05)
    bass = bass * env
    bass = lowpass(bass, 800)
    bass = soft_clip(bass, 1.3)
    return bass

def gen_pad(freq, dur, wave_func=sine, sr=SAMPLE_RATE):
    """Lush pad sound"""
    # Detuned layers
    wave = supersaw(freq, dur, detune=0.003, voices=5)
    wave += supersaw(freq * 2, dur, detune=0.002, voices=3) * 0.3
    env = adsr(dur, 0.3, 0.2, 0.6, 0.5)
    wave = wave * env * 0.15
    wave = lowpass(wave, 4000)
    wave = chorus(wave, rate=0.8, depth=0.001, mix=0.2)
    return wave

def gen_pluck(freq, dur, sr=SAMPLE_RATE):
    """Plucked string sound"""
    wave = supersaw(freq, dur, detune=0.008, voices=3)
    env = adsr(dur, 0.002, 0.15, 0.2, 0.1)
    wave = wave * env * 0.2
    wave = lowpass(wave, 3000)
    return wave

# ─── Scales ───
SCALES = {
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'major': [0, 2, 4, 5, 7, 9, 11],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
}

def get_freq(root, semitones, octave=0):
    return root * (2 ** ((semitones + octave * 12) / 12))

# ─── Song Structure ───
def generate_track(style, duration, mood="", sr=SAMPLE_RATE):
    total_samples = int(sr * duration)
    master = np.zeros(total_samples)
    
    # Style configs
    configs = {
        'Lofi Hip Hop': {'bpm': random.randint(72, 85), 'root': 220, 'scale': 'pentatonic_minor', 'kick_pattern': 'simple'},
        'Techno': {'bpm': random.randint(128, 138), 'root': 55, 'scale': 'minor', 'kick_pattern': 'four_on_floor'},
        'Cyberpunk': {'bpm': random.randint(120, 135), 'root': 110, 'scale': 'minor', 'kick_pattern': 'four_on_floor'},
        'Cinematic': {'bpm': random.randint(60, 75), 'root': 130.81, 'scale': 'minor', 'kick_pattern': 'sparse'},
        'Epic': {'bpm': random.randint(60, 80), 'root': 130.81, 'scale': 'minor', 'kick_pattern': 'sparse'},
        'Acoustic': {'bpm': random.randint(90, 110), 'root': 196, 'scale': 'major', 'kick_pattern': 'simple'},
        'Ambient': {'bpm': random.randint(60, 80), 'root': 174.61, 'scale': 'dorian', 'kick_pattern': 'none'},
    }
    
    cfg = configs.get(style, configs['Lofi Hip Hop'])
    bpm = cfg['bpm']
    beat_dur = 60 / bpm
    root = cfg['root']
    scale = SCALES[cfg['scale']]
    
    print(f"  BPM: {bpm}, Root: {root:.1f}Hz, Scale: {cfg['scale']}")
    
    # ── Drums ──
    if cfg['kick_pattern'] != 'none':
        for i in range(int(duration / beat_dur)):
            pos = int(i * beat_dur * sr)
            if pos >= total_samples:
                break
            
            # Kick
            if cfg['kick_pattern'] == 'four_on_floor' or (i % 4 == 0):
                k = gen_kick(bpm)
                end = min(pos + len(k), total_samples)
                master[pos:end] += k[:end-pos] * 0.7
            
            # Snare
            if cfg['kick_pattern'] != 'sparse' and (i % 4 == 2):
                s = gen_snare()
                end = min(pos + len(s), total_samples)
                master[pos:end] += s[:end-pos] * 0.5
            
            # Hihat
            if cfg['kick_pattern'] != 'sparse':
                for sub in range(2):
                    h_pos = pos + int(sub * beat_dur * sr / 2)
                    if h_pos >= total_samples:
                        break
                    h = gen_hihat(open_hat=(i % 8 == 7 and sub == 1))
                    end = min(h_pos + len(h), total_samples)
                    master[h_pos:end] += h[:end-h_pos] * (0.4 if sub == 0 else 0.25)
    
    # ── Bass ──
    for i in range(int(duration / (beat_dur * 2))):
        pos = int(i * beat_dur * 2 * sr)
        if pos >= total_samples:
            break
        note = scale[i % len(scale)]
        freq = get_freq(root, note, -1)
        b = gen_bass(freq, beat_dur * 1.8)
        end = min(pos + len(b), total_samples)
        master[pos:end] += b[:end-pos] * 0.5
    
    # ── Chords / Pads ──
    progression = random.choice([[0, 3, 4, 0], [0, 4, 5, 3], [5, 2, 0, 4]])
    measure_dur = beat_dur * 4
    
    for i in range(int(duration / measure_dur) + 1):
        pos = int(i * measure_dur * sr)
        if pos >= total_samples:
            break
        root_note = scale[progression[i % len(progression)] % len(scale)]
        # Chord: root, 3rd, 5th
        for interval in [0, 2, 4]:
            note = scale[(progression[i % len(progression)] + interval) % len(scale)]
            freq = get_freq(root, note, 0)
            p = gen_pad(freq, measure_dur * 0.95)
            end = min(pos + len(p), total_samples)
            master[pos:end] += p[:end-pos]
    
    # ── Melody (sparse plucks) ──
    if style not in ['Ambient', 'Cinematic']:
        arp_scale = scale + [s + 12 for s in scale]
        for i in range(int(duration / (beat_dur / 2))):
            if random.random() > 0.4:
                continue
            pos = int(i * beat_dur / 2 * sr)
            if pos >= total_samples:
                break
            note = random.choice(arp_scale)
            freq = get_freq(root, note, 1)
            pl = gen_pluck(freq, beat_dur * 0.4)
            end = min(pos + len(pl), total_samples)
            master[pos:end] += pl[:end-pos] * 0.3
    
    # ── Master Effects ──
    print("  Applying master effects...")
    master = reverb(master)
    master = stereo_delay(master, delay_time=beat_dur * 0.75, feedback=0.2, mix=0.15)
    master = lowpass(master, 16000)
    master = highpass(master, 30)
    master = soft_clip(master, 0.8)
    
    # Normalize
    peak = np.max(np.abs(master))
    if peak > 0:
        master = master / peak * 0.9
    
    return master

# ─── Main ───
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ToneForge v2 — Professional DSP Music Generator")
    parser.add_argument("--style", default="Lofi Hip Hop")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="")
    args = parser.parse_args()
    
    print(f"🎵 ToneForge v2 — {args.style} | {args.duration}s")
    audio = generate_track(args.style, args.duration, args.mood)
    
    # Save as high quality WAV
    write_wav(args.output, SAMPLE_RATE, audio.astype(np.float32))
    
    # Also try to save as MP3 if ffmpeg is available
    mp3_path = args.output.replace('.wav', '.mp3')
    try:
        import subprocess
        subprocess.run([
            'ffmpeg', '-y', '-i', args.output,
            '-b:a', '320k', '-ar', '44100',
            mp3_path
        ], capture_output=True, check=True)
        print(f"✅ WAV: {args.output}")
        print(f"✅ MP3: {mp3_path}")
    except:
        print(f"✅ WAV: {args.output}")
    
    print(f"Done. Peak level: {np.max(np.abs(audio)):.3f}")
