#!/usr/bin/env python3
"""ToneForge v4 — Vocal-Enhanced DSP Music Generator
- Formant synthesis vocals (ooh, aah, humming)
- Vinyl crackle & tape wobble for Lofi
- Sidechain compression
- Enhanced stereo field
- All v3 features retained
"""
import numpy as np
from scipy.io.wavfile import write as write_wav
from scipy.signal import butter, lfilter, hilbert, resample
import argparse, os, random, math

SAMPLE_RATE = 44100

# ─── Oscillators ───
def sine(f, d, sr=SAMPLE_RATE):
    t = np.linspace(0, d, int(sr*d), endpoint=False)
    return np.sin(2*np.pi*f*t)

def saw(f, d, sr=SAMPLE_RATE):
    t = np.linspace(0, d, int(sr*d), endpoint=False)
    return 2.0*(t*f - np.floor(0.5+t*f))

def supersaw(f, d, detune=0.005, voices=7, sr=SAMPLE_RATE):
    t = np.linspace(0, d, int(sr*d), endpoint=False)
    w = np.zeros_like(t)
    for i in range(voices):
        df = 1.0 + detune*(i-voices//2)/voices
        w += np.sin(2*np.pi*f*df*t)
    return w/voices

def noise(d, sr=SAMPLE_RATE):
    return np.random.uniform(-1, 1, int(sr*d))

# ─── Envelope ───
def adsr(n, a=0.01, dc=0.1, s=0.7, r=0.1, sr=SAMPLE_RATE):
    total = int(sr*n) if isinstance(n, float) else n
    ai = int(sr*a); di = int(sr*dc); ri = int(sr*r)
    si = max(0, total-ai-di-ri)
    env = np.concatenate([
        np.linspace(0, 1, max(ai,1)),
        np.linspace(1, s, max(di,1)),
        np.full(max(si,1), s),
        np.linspace(s, 0, max(ri,1))
    ])
    return env[:total]

# ─── Effects ───
def lowpass(sig, cut=3000, sr=SAMPLE_RATE, order=4):
    nyq = sr/2
    if cut >= nyq: return sig
    b,a = butter(order, min(cut, nyq-1)/nyq, 'low')
    return lfilter(b, a, sig)

def highpass(sig, cut=80, sr=SAMPLE_RATE, order=2):
    nyq = sr/2
    b,a = butter(order, cut/nyq, 'high')
    return lfilter(b, a, sig)

def bandpass(sig, low, high, sr=SAMPLE_RATE, order=3):
    nyq = sr/2
    b,a = butter(order, [low/nyq, min(high, nyq-1)/nyq], 'band')
    return lfilter(b, a, sig)

def compressor(sig, threshold=0.5, ratio=4.0, attack=0.003, release=0.1, sr=SAMPLE_RATE):
    env = np.abs(sig)
    at = int(sr*attack); rt = int(sr*release)
    smooth = np.zeros_like(env)
    smooth[0] = env[0]
    for i in range(1, len(env)):
        if env[i] > smooth[i-1]:
            smooth[i] = smooth[i-1] + (env[i]-smooth[i-1])/max(at, 1)
        else:
            smooth[i] = smooth[i-1] + (env[i]-smooth[i-1])/max(rt, 1)
    gain = np.ones_like(smooth)
    mask = smooth > threshold
    gain[mask] = threshold + (smooth[mask]-threshold)/ratio
    gain[mask] /= smooth[mask]+1e-8
    return sig * gain

def sidechain_compress(sig, trigger, threshold=0.3, ratio=8.0, release=0.15, sr=SAMPLE_RATE):
    """Duck sig when trigger is loud (classic Lofi sidechain)"""
    env = np.abs(trigger)
    rt = int(sr*release)
    smooth = np.zeros_like(env)
    smooth[0] = env[0]
    for i in range(1, len(env)):
        alpha = 1.0/rt if env[i] < smooth[i-1] else 1.0
        smooth[i] = smooth[i-1] + (env[i]-smooth[i-1])*alpha
    # Invert: louder trigger = more ducking
    duck = np.ones_like(smooth)
    mask = smooth > threshold
    duck[mask] = 1.0 - (smooth[mask]-threshold)*ratio
    duck = np.clip(duck, 0.15, 1.0)
    # Smooth the duck curve
    duck = lowpass(duck, 15, sr)
    return sig * duck[:len(sig)]

def limiter(sig, ceiling=0.95):
    peak = np.max(np.abs(sig))
    if peak > ceiling:
        sig = sig * (ceiling/peak)
    return np.clip(sig, -ceiling, ceiling)

def stereo_widen(sig, width=1.3):
    delayed = np.zeros_like(sig)
    d = int(0.002 * SAMPLE_RATE)
    delayed[d:] = sig[:-d] * 0.15
    return sig + delayed

def phaser(sig, rate=0.5, depth=0.7, sr=SAMPLE_RATE):
    t = np.arange(len(sig))/sr
    mod = np.sin(2*np.pi*rate*t)
    delay_s = ((mod+1)/2 * 0.005 * sr).astype(int)
    out = sig.copy()
    for i in range(len(sig)):
        j = i - delay_s[i]
        if 0 <= j < len(sig):
            out[i] = sig[i] + sig[j]*depth*0.5
    return out

def reverb(sig, delays=None, decays=None, sr=SAMPLE_RATE):
    if delays is None:
        delays = [0.023, 0.031, 0.037, 0.047, 0.059, 0.073, 0.089, 0.107]
    if decays is None:
        decays = [0.5, 0.42, 0.35, 0.28, 0.22, 0.16, 0.12, 0.08]
    out = sig.copy()
    for dl, dc in zip(delays, decays):
        d = int(sr*dl)
        if d < len(sig):
            pad_arr = np.zeros(len(sig)+d)
            pad_arr[d:d+len(sig)] += sig*dc
            if len(out) < len(pad_arr):
                out = np.pad(out, (0, len(pad_arr)-len(out)))
            out[:len(pad_arr)] += pad_arr[:len(out)]
    return out

def delay(sig, dt=0.3, fb=0.3, mix=0.2, sr=SAMPLE_RATE):
    d = int(sr*dt)
    out = sig.copy()
    for i in range(1, 8):
        pos = d*i
        if pos >= len(out): break
        gain = fb**i * mix
        end = min(pos+len(sig), len(out))
        out[pos:end] += sig[:end-pos]*gain
    return out

def soft_clip(sig, drive=1.5):
    return np.tanh(sig*drive)/drive

def tape_wobble(sig, rate=0.2, depth=0.001, sr=SAMPLE_RATE):
    """Simulate tape speed variation (Lofi warble) — gentle version"""
    t = np.arange(len(sig))/sr
    mod = np.sin(2*np.pi*rate*t) * depth * sr
    indices = np.arange(len(sig), dtype=np.float64) + mod
    indices = np.clip(indices, 0, len(sig)-1)
    # Use linear interpolation instead of nearest-neighbor to avoid aliasing
    lo = np.floor(indices).astype(int)
    hi = np.minimum(lo + 1, len(sig) - 1)
    frac = indices - lo
    return sig[lo] * (1 - frac) + sig[hi] * frac

def tape_saturate(sig, drive=1.3):
    """Warm tape saturation"""
    return np.tanh(sig*drive) * (1.0 + 0.1*np.sin(np.abs(sig)*np.pi))

# ─── Formant Synthesis (Vocals) ───
VOWELS = {
    'ah': [(800, 80, 1.0), (1200, 100, 0.5), (2500, 120, 0.2)],   # "ah"
    'oh': [(600, 70, 1.0), (900, 90, 0.5), (2200, 110, 0.15)],    # "oh"
    'ee': [(300, 60, 1.0), (2300, 90, 0.6), (2900, 100, 0.2)],    # "ee"
    'oo': [(350, 60, 1.0), (900, 80, 0.3), (2400, 100, 0.1)],     # "oo"
    'mm': [(280, 50, 1.0), (900, 70, 0.2), (2200, 90, 0.05)],     # humming "m"
}

def formant_vocal(freq, dur, vowel='ah', vibrato=0.03, breath=0.02, sr=SAMPLE_RATE):
    """Synthesize vocal-like sound using formant filtering — richer version"""
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    
    # Glottal pulse — warmer with more harmonics
    pulse = saw(freq, dur, sr) * 0.5
    pulse += np.sin(2*np.pi*freq*2*t) * 0.35
    pulse += np.sin(2*np.pi*freq*3*t) * 0.2
    pulse += np.sin(2*np.pi*freq*4*t) * 0.12
    pulse += np.sin(2*np.pi*freq*5*t) * 0.06
    
    # Vibrato — slower, wider for expressiveness
    vib = np.sin(2*np.pi*5.0*t) * vibrato * freq
    vib += np.sin(2*np.pi*2.7*t) * vibrato * 0.4 * freq  # dual vibrato
    vib_signal = np.sin(2*np.pi*(freq+vib)*t) * 0.35
    pulse += vib_signal
    
    # Apply formant filters
    forms = VOWELS.get(vowel, VOWELS['ah'])
    vocal = np.zeros_like(pulse)
    for center, bw, gain in forms:
        filtered = bandpass(pulse, max(center-bw, 50), min(center+bw, sr//2-1), sr)
        vocal += filtered * gain
    
    # Add breathiness — smoother
    breath_noise = noise(dur, sr) * breath
    breath_noise = highpass(breath_noise, 3500, sr)
    breath_noise = lowpass(breath_noise, 7000, sr)
    breath_noise = lowpass(breath_noise, 7000, sr)  # double filter for softness
    vocal += breath_noise * adsr(dur, 0.05, 0.1, 0.6, 0.15, sr)
    
    # Envelope — longer attack for smoothness
    e = adsr(dur, 0.12, 0.15, 0.7, 0.25, sr)
    vocal *= e
    
    return soft_clip(vocal, 1.2) * 0.35

def vocal_pad(freq, dur, vowel='oo', voices=5, detune=0.003, sr=SAMPLE_RATE):
    """Layered vocal pad — richer choir-like with harmony"""
    pad = np.zeros(int(sr*dur))
    # Main voice
    for i in range(voices):
        df = 1.0 + detune*(i-voices//2)/voices
        v = formant_vocal(freq*df, dur, vowel, sr=sr)
        pad[:len(v)] += v
    # Harmony: +5th (perfect fifth above)
    fifth = freq * 1.5
    for i in range(3):
        df = 1.0 + detune*(i-1)/3
        v = formant_vocal(fifth*df, dur, vowel, sr=sr) * 0.35
        pad[:len(v)] += v
    pad /= (voices + 3 * 0.35)
    
    # Lush reverb
    pad = reverb(pad, delays=[0.035, 0.055, 0.08, 0.12, 0.18], decays=[0.45, 0.35, 0.25, 0.15, 0.08])
    return lowpass(pad, 4000, sr)

def vocal_ooh_aah(freq, dur, phrase='ooh', sr=SAMPLE_RATE):
    """Ooh/Aah vocal phrase with vowel morphing"""
    n_samples = int(sr*dur)
    result = np.zeros(n_samples)
    
    if phrase == 'ooh':
        vowels = ['oo', 'oh', 'ah', 'oh', 'oo']
    else:  # aah
        vowels = ['ah', 'ee', 'ah', 'oh', 'ah']
    
    seg_dur = dur / len(vowels)
    for i, vow in enumerate(vowels):
        start = int(i * seg_dur * sr)
        v = formant_vocal(freq, seg_dur, vow, sr=sr)
        end = min(start + len(v), n_samples)
        result[start:end] += v[:end-start]
    
    return result

# ─── Lofi Textures ───
def vinyl_crackle(dur, density=0.15, sr=SAMPLE_RATE):
    """Vinyl record crackle and pop — subtle version"""
    n = int(sr*dur)
    crackle = np.zeros(n)
    
    # Random pops — much softer
    n_pops = int(dur * density * 40)
    for _ in range(n_pops):
        pos = random.randint(0, n-1)
        pop_len = random.randint(5, 30)
        amp = random.uniform(0.003, 0.02)  # was 0.02-0.12
        decay = np.exp(-np.linspace(0, 10, min(pop_len, n-pos)))
        end = min(pos+pop_len, n)
        crackle[pos:end] += np.random.uniform(-1, 1, end-pos) * amp * decay
    
    # Continuous surface noise — very very subtle
    surface = noise(dur, sr) * 0.002  # was 0.008
    surface = highpass(surface, 3000, sr)
    surface = lowpass(surface, 10000, sr)
    crackle += surface
    
    return crackle

def vinyl_hiss(dur, sr=SAMPLE_RATE):
    """Subtle vinyl hiss — very quiet"""
    hiss = noise(dur, sr) * 0.004  # was 0.015
    hiss = bandpass(hiss, 5000, 9000, sr)
    return hiss

# ─── Instruments ───
def kick(bpm, sr=SAMPLE_RATE):
    t = np.linspace(0, 0.5, int(sr*0.5))
    f = 160*np.exp(-35*t) + 28
    k = np.sin(2*np.pi*np.cumsum(f)/sr) * np.exp(-10*t)
    k = soft_clip(k*1.3, 2.5)
    k = lowpass(k, 5000)
    return k

def snare(sr=SAMPLE_RATE):
    t = np.linspace(0, 0.2, int(sr*0.2))
    n = noise(0.2) * np.exp(-28*t) * 0.45
    b = 0.3*np.sin(2*np.pi*180*t) * np.exp(-18*t)
    s = highpass(n+b, 180)
    return soft_clip(s, 1.5)

def hihat(open_=False, sr=SAMPLE_RATE):
    d = 0.18 if open_ else 0.04
    t = np.linspace(0, d, int(sr*d))
    h = noise(d)*np.exp((-20 if open_ else -80)*t)*0.12
    h = highpass(h, 7000)
    h = lowpass(h, 14000)
    return h

def bass(freq, dur, sr=SAMPLE_RATE):
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    w = 0.5*np.sin(2*np.pi*freq*t) + 0.25*np.sin(2*np.pi*freq*0.5*t) + 0.15*saw(freq, dur)*np.exp(-4*t)
    e = adsr(dur, 0.005, 0.08, 0.75, 0.06)
    w = w*e*0.6
    w = lowpass(w, 700)
    return soft_clip(w, 1.2)

def pad(freq, dur, sr=SAMPLE_RATE):
    w = supersaw(freq, dur, 0.003, 5)
    w += supersaw(freq*2, dur, 0.002, 3)*0.2
    e = adsr(dur, 0.4, 0.3, 0.55, 0.6)
    w = w*e*0.1
    w = lowpass(w, 3500)
    return w

def pluck(freq, dur, sr=SAMPLE_RATE):
    w = supersaw(freq, dur, 0.01, 3)
    e = adsr(dur, 0.002, 0.12, 0.15, 0.08)
    w = w*e*0.15
    w = lowpass(w, 4000)
    return w

def detuned_epiano(freq, dur, sr=SAMPLE_RATE):
    """Detuned electric piano (Lofi classic)"""
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    # Slight detuning for warmth
    w1 = np.sin(2*np.pi*freq*t) * 0.5
    w2 = np.sin(2*np.pi*freq*1.003*t) * 0.4
    w3 = np.sin(2*np.pi*freq*0.997*t) * 0.3
    # Bell tone
    w4 = np.sin(2*np.pi*freq*3*t) * 0.15 * np.exp(-8*t)
    w = w1 + w2 + w3 + w4
    e = adsr(dur, 0.005, 0.2, 0.4, 0.3, sr)
    w = w * e * 0.2
    w = lowpass(w, 5500, sr)
    w = tape_saturate(w, 1.15)
    return w

def arp_note(freq, dur, sr=SAMPLE_RATE):
    w = supersaw(freq, dur, 0.006, 3)
    e = adsr(dur, 0.001, 0.05, 0.3, 0.05)
    return w*e*0.1

# ─── Music Theory ───
SCALES = {
    'minor': [0,2,3,5,7,8,10],
    'major': [0,2,4,5,7,9,11],
    'pentatonic': [0,3,5,7,10],
    'dorian': [0,2,3,5,7,9,10],
    'mixolydian': [0,2,4,5,7,9,10],
}

def freq(root, semi, oct=0):
    return root*(2**((semi+oct*12)/12))

# ─── Markov Melody ───
MELODY_TRANS = {
    0: {0:0.1, 3:0.3, 5:0.3, 7:0.2, 10:0.1},
    3: {0:0.2, 3:0.15, 5:0.35, 7:0.2, 10:0.1},
    5: {0:0.15, 3:0.25, 5:0.15, 7:0.3, 10:0.15},
    7: {0:0.1, 3:0.2, 5:0.3, 7:0.15, 10:0.25},
    10: {0:0.2, 3:0.15, 5:0.2, 7:0.3, 10:0.15},
}

def markov_next(note):
    trans = MELODY_TRANS.get(note, MELODY_TRANS[5])
    notes = list(trans.keys())
    probs = list(trans.values())
    return random.choices(notes, weights=probs, k=1)[0]

# ─── Section Generator ───
def gen_section(bpm, root, scale_name, bars, energy=1.0, section_type='verse',
                style='Lofi Hip Hop', sr=SAMPLE_RATE):
    """Generate a section of music with style-specific enhancements"""
    beat_dur = 60/bpm
    measure_dur = beat_dur*4
    dur = bars*measure_dur
    n_samples = int(sr*dur)
    sec = np.zeros(n_samples)
    scale = SCALES[scale_name]
    
    prog_options = {
        'intro': [[0,0,0,0], [0,4,0,4], [0,5,0,5]],
        'verse': [[0,3,4,0], [0,4,5,3], [5,2,0,4], [0,5,4,3], [3,4,5,0]],
        'chorus': [[0,4,5,3], [4,5,0,0], [0,5,3,4], [5,4,0,3], [0,3,5,4]],
        'bridge': [[2,5,0,4], [4,2,5,0], [5,0,4,2], [0,2,4,5]],  # more tension
        'outro': [[0,4,0,0], [4,0,0,0], [0,5,0,0]],
    }
    progs = prog_options.get(section_type, prog_options['verse'])
    progression = random.choice(progs)
    
    is_lofi = style == 'Lofi Hip Hop'
    
    # ── Drums ──
    if section_type != 'intro' or bars > 2:
        for i in range(int(dur/beat_dur)):
            pos = int(i*beat_dur*sr)
            if pos >= n_samples: break
            beat_in_measure = i % 4
            measure = i // 4
            
            if section_type == 'intro' and measure == 0:
                continue
            
            # Kick
            if beat_in_measure == 0 or (section_type == 'chorus' and beat_in_measure == 2):
                k = kick(bpm)
                end = min(pos+len(k), n_samples)
                sec[pos:end] += k[:end-pos]*0.65*energy
            
            # Snare
            if section_type in ['verse','chorus'] and beat_in_measure in [1,3]:
                s = snare()
                end = min(pos+len(s), n_samples)
                sec[pos:end] += s[:end-pos]*0.4*energy
            
            # Hihat
            if section_type != 'intro':
                for sub in range(2):
                    hp = pos + int(sub*beat_dur*sr/2)
                    if hp >= n_samples: break
                    h = hihat(open_=(i%8==7 and sub==1))
                    end = min(hp+len(h), n_samples)
                    sec[hp:end] += h[:end-hp]*(0.35 if sub==0 else 0.2)*energy
    
    # ── Bass ──
    if section_type != 'outro' or bars > 2:
        for i in range(int(dur/(beat_dur*2))):
            pos = int(i*beat_dur*2*sr)
            if pos >= n_samples: break
            note = scale[progression[(i//2)%len(progression)]%len(scale)]
            b = bass(freq(root, note, -1), beat_dur*1.8)
            b *= 0.4*energy
            end = min(pos+len(b), n_samples)
            sec[pos:end] += b[:end-pos]
    
    # ── Chords ──
    chord_track = np.zeros(n_samples)
    for i in range(bars):
        pos = int(i*measure_dur*sr)
        if pos >= n_samples: break
        chord_root = progression[i%len(progression)]
        for iv in [0, 2, 4]:
            note = scale[(chord_root+iv)%len(scale)]
            if is_lofi and section_type in ['verse', 'chorus']:
                # Lofi: use detuned EP instead of pad
                p = detuned_epiano(freq(root, note, 0), measure_dur*0.95)
            else:
                p = pad(freq(root, note, 0), measure_dur*0.95)
            p *= energy
            end = min(pos+len(p), n_samples)
            chord_track[pos:end] += p[:end-pos]
    
    sec += chord_track
    
    # ── Melody (Markov chain) or Arp (bridge) ──
    melody_scale = [s+12 for s in scale]
    current_note = random.choice(melody_scale)
    
    if section_type == 'bridge':
        # Arpeggio pattern for bridge — dreamy arps
        for i in range(int(dur/(beat_dur/4))):
            pos = int(i*beat_dur/4*sr)
            if pos >= n_samples: break
            # Cycle through chord tones
            chord_idx = (i // 4) % len(progression)
            chord_root = progression[chord_idx]
            arp_interval = [0, 2, 4, 2][i % 4]  # up-down pattern
            note = scale[(chord_root + arp_interval) % len(scale)]
            a_dur = beat_dur * 0.22
            a = arp_note(freq(root, note + 12, random.choice([0, 1])), a_dur)
            a *= 0.18 * energy
            end = min(pos + len(a), n_samples)
            sec[pos:end] += a[:end-pos]
    elif section_type in ['verse', 'chorus']:
        skip = 3 if section_type == 'verse' else 2
        for i in range(int(dur/(beat_dur/skip))):
            if random.random() > 0.55:
                continue
            pos = int(i*beat_dur/skip*sr)
            if pos >= n_samples: break
            current_note = markov_next(current_note)
            n_dur = beat_dur*0.35 if random.random() > 0.3 else beat_dur*0.7
            m = pluck(freq(root, current_note, 1), n_dur)
            m *= 0.25*energy
            end = min(pos+len(m), n_samples)
            sec[pos:end] += m[:end-pos]
    
    # ── Vocal Layer — more prominent, also in bridge ──
    vocal_track = np.zeros(n_samples)
    if is_lofi and section_type in ['verse', 'chorus', 'bridge']:
        vocal_note = scale[progression[0] % len(scale)]
        vocal_freq = freq(root, vocal_note, 1)
        
        if section_type == 'chorus':
            # Prominent chorus vocals
            vow = random.choice(['ooh', 'aah'])
            v = vocal_ooh_aah(vocal_freq, dur, vow, sr)
            v *= 0.28 * energy  # was 0.18
        elif section_type == 'bridge':
            # Bridge: gentle humming with harmony
            vow = random.choice(['mm', 'oo', 'oh'])
            v = vocal_pad(vocal_freq * 0.95, dur, vow, voices=4, sr=sr)
            v *= 0.22 * energy
        else:
            # Verse: subtle vocal pad
            vow = random.choice(['oo', 'mm', 'oh'])
            v = vocal_pad(vocal_freq, dur, vow, voices=4, sr=sr)
            v *= 0.18 * energy  # was 0.12
        
        v_len = min(len(v), n_samples)
        vocal_track[:v_len] += v[:v_len]
    
    sec += vocal_track
    
    return sec, vocal_track

# ─── Main Generator ───
def generate_track(style, duration, mood="", sr=SAMPLE_RATE):
    configs = {
        'Lofi Hip Hop': {'bpm':random.randint(72,85), 'root':220, 'scale':'pentatonic'},
        'Techno': {'bpm':random.randint(128,138), 'root':55, 'scale':'minor'},
        'Cyberpunk': {'bpm':random.randint(120,135), 'root':110, 'scale':'minor'},
        'Cinematic': {'bpm':random.randint(60,75), 'root':130.81, 'scale':'minor'},
        'Epic': {'bpm':random.randint(60,80), 'root':130.81, 'scale':'minor'},
        'Acoustic': {'bpm':random.randint(90,110), 'root':196, 'scale':'major'},
        'Ambient': {'bpm':random.randint(60,80), 'root':174.61, 'scale':'dorian'},
        'Trap': {'bpm':random.randint(130,145), 'root':55, 'scale':'minor'},
        'Synthpop': {'bpm':random.randint(110,125), 'root':164.81, 'scale':'major'},
    }
    cfg = configs.get(style, configs['Lofi Hip Hop'])
    bpm = cfg['bpm']
    root = cfg['root']
    scale = cfg['scale']
    
    print(f"  BPM: {bpm}, Root: {root:.1f}Hz, Scale: {scale}")
    
    beat_dur = 60/bpm
    measure_dur = beat_dur*4
    total_samples = int(sr*duration)
    
    # Song structure — with bridge for variety
    if duration <= 15:
        sections = [('verse', 2, 0.8), ('chorus', 2, 1.0)]
    elif duration <= 30:
        sections = [('intro', 2, 0.4), ('verse', 4, 0.7), ('chorus', 4, 1.0)]
    elif duration <= 60:
        sections = [
            ('intro', 4, 0.3), ('verse', 8, 0.6),
            ('chorus', 8, 0.9), ('bridge', 4, 0.75),
            ('verse', 8, 0.65), ('chorus', 8, 1.0), ('outro', 4, 0.3),
        ]
    else:
        repeat = max(1, duration // 60)
        sections = [('intro', 4, 0.3)]
        for _ in range(repeat):
            sections += [('verse', 8, 0.6), ('chorus', 8, 0.9)]
            sections += [('bridge', 4, 0.75)]  # bridge between cycles
            sections += [('verse', 8, 0.65), ('chorus', 8, 1.0)]
        sections.append(('outro', 4, 0.25))
    
    print(f"  Structure: {' → '.join(f'{s[0]}({s[1]}bar)' for s in sections)}")
    
    master = np.zeros(total_samples)
    all_vocals = np.zeros(total_samples)
    pos = 0
    for stype, bars, energy in sections:
        sec_dur = bars*measure_dur
        sec, voc = gen_section(bpm, root, scale, bars, energy, stype, style)
        end = min(pos+len(sec), total_samples)
        master[pos:end] += sec[:end-pos]
        voc_end = min(pos+len(voc), total_samples)
        all_vocals[pos:voc_end] += voc[:voc_end-pos]
        pos = end
        if pos >= total_samples:
            break
    
    # ── Sidechain (kick ducks vocals/chords) ──
    if style == 'Lofi Hip Hop':
        print("  Lofi: sidechain + vinyl crackle + tape wobble")
        # Extract kick pattern for sidechain trigger
        kick_trigger = np.zeros(total_samples)
        for i in range(int(duration/beat_dur)):
            pos = int(i*beat_dur*sr)
            if pos >= total_samples: break
            if i % 4 == 0:
                k = kick(bpm)
                end = min(pos+len(k), total_samples)
                kick_trigger[pos:end] += k[:end-pos]
        # Sidechain duck the music under kick
        master = sidechain_compress(master, kick_trigger, threshold=0.2, ratio=6.0, release=0.12)
        
        # Vinyl texture
        crackle = vinyl_crackle(duration, density=0.25)
        master[:len(crackle)] += crackle[:len(master)]
        hiss = vinyl_hiss(duration)
        master[:len(hiss)] += hiss[:len(master)]
        
        # Tape wobble (subtle)
        master = tape_wobble(master, rate=0.25, depth=0.001)
    
    # ── Master chain ──
    fx_chain = "compress → reverb → delay"
    if style in ['Cyberpunk', 'Synthpop', 'Techno']:
        fx_chain += " → phaser"
    fx_chain += " → stereo → limit"
    print(f"  Master: {fx_chain}")
    
    master = compressor(master, threshold=0.6, ratio=3.0)
    master = reverb(master)
    master = delay(master, dt=beat_dur*0.75, fb=0.25, mix=0.12)
    if style in ['Cyberpunk', 'Synthpop', 'Techno']:
        master = phaser(master, rate=0.3, depth=0.4)
    master = stereo_widen(master)
    master = lowpass(master, 17000)
    master = highpass(master, 25)
    master = soft_clip(master, 0.7)
    master = limiter(master, 0.92)
    
    return master[:total_samples]

# ─── CLI ───
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ToneForge v4 — Vocal-Enhanced")
    parser.add_argument("--style", default="Lofi Hip Hop")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="")
    args = parser.parse_args()
    
    print(f"🎵 ToneForge v4 — {args.style} | {args.duration}s")
    audio = generate_track(args.style, args.duration, args.mood)
    
    write_wav(args.output, SAMPLE_RATE, audio.astype(np.float32))
    
    mp3 = args.output.replace('.wav','.mp3')
    try:
        import subprocess
        subprocess.run(['ffmpeg','-y','-i',args.output,'-b:a','320k','-ar','44100',mp3],
                       capture_output=True, check=True)
        print(f"✅ WAV: {args.output}")
        print(f"✅ MP3: {mp3}")
    except:
        print(f"✅ WAV: {args.output}")
