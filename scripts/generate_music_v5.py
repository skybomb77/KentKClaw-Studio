#!/usr/bin/env python3
"""ToneForge v5 — Professional Lofi DSP Engine
- Rich 7th/9th jazz chords with warmth
- Layered vocal harmonies (3rd + 5th + octave)
- Swing drums with ghost notes
- Multi-band mastering chain
- Tape saturation + analog warmth
- Rich frequency spectrum (sub-bass to airy highs)
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

def triangle(f, d, sr=SAMPLE_RATE):
    t = np.linspace(0, d, int(sr*d), endpoint=False)
    return 2.0 * np.abs(2.0*(t*f - np.floor(0.5+t*f))) - 1.0

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

# ─── Filters ───
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

# ─── Dynamics ───
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
    env = np.abs(trigger)
    rt = int(sr*release)
    smooth = np.zeros_like(env)
    smooth[0] = env[0]
    for i in range(1, len(env)):
        alpha = 1.0/rt if env[i] < smooth[i-1] else 1.0
        smooth[i] = smooth[i-1] + (env[i]-smooth[i-1])*alpha
    duck = np.ones_like(smooth)
    mask = smooth > threshold
    duck[mask] = 1.0 - (smooth[mask]-threshold)*ratio
    duck = np.clip(duck, 0.15, 1.0)
    duck = lowpass(duck, 15, sr)
    return sig * duck[:len(sig)]

def limiter(sig, ceiling=0.95):
    peak = np.max(np.abs(sig))
    if peak > ceiling:
        sig = sig * (ceiling/peak)
    return np.clip(sig, -ceiling, ceiling)

# ─── Effects ───
def reverb(sig, delays=None, decays=None, sr=SAMPLE_RATE):
    if delays is None:
        delays = [0.023, 0.031, 0.037, 0.047, 0.059, 0.073, 0.089, 0.107]
    if decays is None:
        decays = [0.5, 0.42, 0.35, 0.28, 0.22, 0.16, 0.12, 0.08]
    out = sig.copy()
    for dl, dc in zip(delays, decays):
        d = int(sr*dl)
        if d < len(sig):
            pad = np.zeros(len(sig)+d)
            pad[d:d+len(sig)] += sig*dc
            if len(out) < len(pad):
                out = np.pad(out, (0, len(pad)-len(out)))
            out[:len(pad)] += pad[:len(out)]
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

def tape_wobble(sig, rate=0.2, depth=0.001, sr=SAMPLE_RATE):
    t = np.arange(len(sig))/sr
    mod = np.sin(2*np.pi*rate*t) * depth * sr
    indices = np.arange(len(sig), dtype=np.float64) + mod
    indices = np.clip(indices, 0, len(sig)-1)
    lo = np.floor(indices).astype(int)
    hi = np.minimum(lo + 1, len(sig) - 1)
    frac = indices - lo
    return sig[lo] * (1 - frac) + sig[hi] * frac

def tape_saturate(sig, drive=1.3):
    return np.tanh(sig*drive) * (1.0 + 0.1*np.sin(np.abs(sig)*np.pi))

# ─── Analog Warmth (multi-band saturation) ───
def analog_warmth(sig, sr=SAMPLE_RATE):
    """Subtle multi-band saturation for analog feel"""
    low = lowpass(sig, 300, sr, order=2) * 1.05  # warm low end
    mid = bandpass(sig, 300, 4000, sr, order=2)
    mid = np.tanh(mid * 1.2) * 0.9  # gentle mid saturation
    high = highpass(sig, 4000, sr, order=2) * 0.95  # tame highs
    return low + mid + high

# ─── Lofi Textures ───
def vinyl_crackle(dur, density=0.12, sr=SAMPLE_RATE):
    n = int(sr*dur)
    crackle = np.zeros(n)
    n_pops = int(dur * density * 30)
    for _ in range(n_pops):
        pos = random.randint(0, n-1)
        pop_len = random.randint(5, 25)
        amp = random.uniform(0.002, 0.015)
        decay = np.exp(-np.linspace(0, 12, min(pop_len, n-pos)))
        end = min(pos+pop_len, n)
        crackle[pos:end] += np.random.uniform(-1, 1, end-pos) * amp * decay
    surface = noise(dur, sr) * 0.0015
    surface = highpass(surface, 3500, sr)
    surface = lowpass(surface, 9000, sr)
    crackle += surface
    return crackle

def vinyl_hiss(dur, sr=SAMPLE_RATE):
    hiss = noise(dur, sr) * 0.003
    hiss = bandpass(hiss, 5000, 8500, sr)
    return hiss

# ─── Formant Vocals (Enhanced) ───
VOWELS = {
    'ah': [(800, 80, 1.0), (1200, 100, 0.5), (2500, 120, 0.2)],
    'oh': [(600, 70, 1.0), (900, 90, 0.5), (2200, 110, 0.15)],
    'ee': [(300, 60, 1.0), (2300, 90, 0.6), (2900, 100, 0.2)],
    'oo': [(350, 60, 1.0), (900, 80, 0.3), (2400, 100, 0.1)],
    'mm': [(280, 50, 1.0), (900, 70, 0.2), (2200, 90, 0.05)],
    'nn': [(280, 50, 1.0), (1800, 90, 0.4), (2600, 100, 0.15)],
}

def formant_vocal(freq, dur, vowel='ah', vibrato_rate=5.0, vibrato_depth=0.025, breath=0.018, sr=SAMPLE_RATE):
    """Rich vocal synthesis with formant filtering"""
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    
    # Glottal pulse — rich harmonics
    pulse = np.zeros_like(t)
    for h, amp in [(1, 0.45), (2, 0.30), (3, 0.18), (4, 0.10), (5, 0.05), (6, 0.025)]:
        pulse += np.sin(2*np.pi*freq*h*t) * amp
    
    # Dual vibrato for natural feel
    vib = np.sin(2*np.pi*vibrato_rate*t) * vibrato_depth * freq
    vib += np.sin(2*np.pi*(vibrato_rate*0.53)*t) * vibrato_depth * 0.35 * freq
    pulse += np.sin(2*np.pi*(freq+vib)*t) * 0.3
    
    # Formant filtering
    forms = VOWELS.get(vowel, VOWELS['ah'])
    vocal = np.zeros_like(pulse)
    for center, bw, gain in forms:
        filtered = bandpass(pulse, max(center-bw, 50), min(center+bw, sr//2-1), sr)
        vocal += filtered * gain
    
    # Smooth breathiness
    br = noise(dur, sr) * breath
    br = highpass(br, 3500, sr)
    br = lowpass(br, 7000, sr)
    br = lowpass(br, 7000, sr)
    vocal += br * adsr(dur, 0.06, 0.1, 0.55, 0.15, sr)
    
    # Warm envelope
    e = adsr(dur, 0.1, 0.12, 0.7, 0.22, sr)
    vocal *= e
    
    return soft_clip(vocal, 1.15) * 0.32

def vocal_pad(freq, dur, vowel='oo', voices=6, detune=0.003, sr=SAMPLE_RATE):
    """Rich choir pad with layered harmonies"""
    pad = np.zeros(int(sr*dur))
    
    # Main voices
    for i in range(voices):
        df = 1.0 + detune*(i-voices//2)/voices
        v = formant_vocal(freq*df, dur, vowel, sr=sr)
        pad[:len(v)] += v
    
    # +5th harmony
    fifth = freq * 1.5
    for i in range(3):
        df = 1.0 + detune*(i-1)/3
        v = formant_vocal(fifth*df, dur, vowel, sr=sr) * 0.3
        pad[:len(v)] += v
    
    # +3rd harmony (major/minor feel)
    third = freq * 1.26  # minor third
    for i in range(2):
        df = 1.0 + detune*(i-0.5)/2
        v = formant_vocal(third*df, dur, vowel, sr=sr) * 0.2
        pad[:len(v)] += v
    
    # +octave shimmer
    oct = freq * 2.0
    v = formant_vocal(oct, dur, 'mm', sr=sr) * 0.12
    pad[:len(v)] += v
    
    total_weight = voices + 3*0.3 + 2*0.2 + 0.12
    pad /= total_weight
    
    # Lush reverb
    pad = reverb(pad, delays=[0.03, 0.05, 0.075, 0.11, 0.16, 0.22], decays=[0.5, 0.38, 0.28, 0.18, 0.1, 0.05])
    return lowpass(pad, 3800, sr)

def vocal_ooh_aah(freq, dur, phrase='ooh', sr=SAMPLE_RATE):
    """Ooh/Aah phrase with smooth vowel morphing"""
    n_samples = int(sr*dur)
    result = np.zeros(n_samples)
    
    if phrase == 'ooh':
        vowels = ['oo', 'oh', 'ah', 'mm', 'oh', 'oo']
    else:
        vowels = ['ah', 'ee', 'oh', 'ah', 'mm', 'ah']
    
    # Overlap segments for smoothness
    seg_dur = dur / len(vowels) * 1.3  # 30% overlap
    for i, vow in enumerate(vowels):
        start = int(i * (dur / len(vowels)) * sr)
        v = formant_vocal(freq, seg_dur, vow, sr=sr)
        end = min(start + len(v), n_samples)
        result[start:end] += v[:end-start]
    
    return result

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

def ghost_snare(sr=SAMPLE_RATE):
    """Quiet ghost snare for swing feel"""
    t = np.linspace(0, 0.08, int(sr*0.08))
    n = noise(0.08) * np.exp(-50*t) * 0.15
    return highpass(n, 200)

def bass(freq, dur, sr=SAMPLE_RATE):
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    w = 0.5*np.sin(2*np.pi*freq*t) + 0.25*np.sin(2*np.pi*freq*0.5*t) + 0.15*saw(freq, dur)*np.exp(-4*t)
    e = adsr(dur, 0.005, 0.08, 0.75, 0.06)
    w = w*e*0.6
    w = lowpass(w, 700)
    return soft_clip(w, 1.2)

def rhodes(freq, dur, sr=SAMPLE_RATE):
    """Electric piano (Rhodes-like) — rich bell tones"""
    t = np.linspace(0, dur, int(sr*dur), endpoint=False)
    w = np.zeros_like(t)
    # Fundamental + harmonics with bell character
    w += np.sin(2*np.pi*freq*t) * 0.4
    w += np.sin(2*np.pi*freq*2*t) * 0.25 * np.exp(-3*t)
    w += np.sin(2*np.pi*freq*3*t) * 0.15 * np.exp(-5*t)
    w += np.sin(2*np.pi*freq*5.04*t) * 0.08 * np.exp(-8*t)  # inharmonic bell
    w += np.sin(2*np.pi*freq*7*t) * 0.04 * np.exp(-10*t)
    # Slight detuning for warmth
    w += np.sin(2*np.pi*freq*1.003*t) * 0.2
    w += np.sin(2*np.pi*freq*0.997*t) * 0.15
    e = adsr(dur, 0.003, 0.15, 0.45, 0.25, sr)
    w = w * e * 0.18
    w = lowpass(w, 5000, sr)
    w = tape_saturate(w, 1.1)
    return w

def pad(freq, dur, sr=SAMPLE_RATE):
    w = supersaw(freq, dur, 0.003, 5)
    w += supersaw(freq*2, dur, 0.002, 3)*0.15
    e = adsr(dur, 0.4, 0.3, 0.55, 0.6)
    w = w*e*0.08
    w = lowpass(w, 3200)
    return w

def pluck(freq, dur, sr=SAMPLE_RATE):
    w = supersaw(freq, dur, 0.01, 3)
    e = adsr(dur, 0.002, 0.12, 0.15, 0.08)
    w = w*e*0.15
    w = lowpass(w, 4000)
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
    'blues': [0,3,5,6,7,10],
}

def freq(root, semi, oct=0):
    return root*(2**((semi+oct*12)/12))

# ─── Jazz Chord Voicings ───
def jazz_chord_notes(root_semi, scale, chord_type='7th'):
    """Generate jazz chord tones (7th, 9th, etc.)"""
    intervals = {
        'triad': [0, 2, 4],
        '7th': [0, 2, 4, 6],        # root, 3rd, 5th, 7th
        '9th': [0, 2, 4, 6, 1],     # add 9th
        'maj7': [0, 2, 4, 6],       # major 7th
        'min7': [0, 2, 4, 6],       # minor 7th (scale determines quality)
    }
    ivs = intervals.get(chord_type, intervals['7th'])
    return [scale[(root_semi + iv) % len(scale)] for iv in ivs]

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
        'bridge': [[2,5,0,4], [4,2,5,0], [5,0,4,2], [0,2,4,5]],
        'outro': [[0,4,0,0], [4,0,0,0], [0,5,0,0]],
    }
    progs = prog_options.get(section_type, prog_options['verse'])
    progression = random.choice(progs)
    
    is_lofi = style == 'Lofi Hip Hop'
    
    # ── Drums with swing ──
    swing = 0.06 if is_lofi else 0  # swing offset
    if section_type != 'intro' or bars > 2:
        for i in range(int(dur/beat_dur)):
            # Swing: delay off-beats
            swing_offset = swing if (i % 2 == 1) else 0
            pos = int((i*beat_dur + swing_offset)*sr)
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
            
            # Ghost snare (swing feel)
            if section_type in ['verse','chorus'] and random.random() > 0.7:
                ghost_pos = pos + int(beat_dur*0.5*sr)
                if ghost_pos < n_samples:
                    gs = ghost_snare()
                    ge = min(ghost_pos+len(gs), n_samples)
                    sec[ghost_pos:ge] += gs[:ge-ghost_pos]*energy
            
            # Hihat
            if section_type != 'intro':
                for sub in range(2):
                    hp = pos + int(sub*beat_dur*sr/2)
                    if hp >= n_samples: break
                    h = hihat(open_=(i%8==7 and sub==1))
                    # Varied velocity
                    vel = (0.35 if sub==0 else 0.2) * energy
                    if random.random() > 0.8:
                        vel *= 0.5  # ghost hihat
                    end = min(hp+len(h), n_samples)
                    sec[hp:end] += h[:end-hp]*vel
    
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
    
    # ── Chords — jazz voicings with Rhodes ──
    chord_track = np.zeros(n_samples)
    for i in range(bars):
        pos = int(i*measure_dur*sr)
        if pos >= n_samples: break
        chord_root = progression[i%len(progression)]
        
        if is_lofi:
            # Jazz 7th chord with Rhodes
            chord_notes = jazz_chord_notes(chord_root, scale, '7th')
            for j, note in enumerate(chord_notes):
                octave = 0 if j == 0 else 0  # all same octave for tight voicing
                p = rhodes(freq(root, note, octave), measure_dur*0.92)
                # Higher notes softer
                p *= (1.0 - j*0.1) * energy
                end = min(pos+len(p), n_samples)
                chord_track[pos:end] += p[:end-pos]
            
            # Pad layer underneath (softer)
            for iv in [0, 4]:
                note = scale[(chord_root+iv)%len(scale)]
                p = pad(freq(root, note, 0), measure_dur*0.95)
                p *= 0.4 * energy
                end = min(pos+len(p), n_samples)
                chord_track[pos:end] += p[:end-pos]
        else:
            for iv in [0, 2, 4]:
                note = scale[(chord_root+iv)%len(scale)]
                p = pad(freq(root, note, 0), measure_dur*0.95)
                p *= energy
                end = min(pos+len(p), n_samples)
                chord_track[pos:end] += p[:end-pos]
    
    sec += chord_track
    
    # ── Melody / Arp ──
    melody_scale = [s+12 for s in scale]
    current_note = random.choice(melody_scale)
    
    if section_type == 'bridge':
        # Dreamy arpeggios
        for i in range(int(dur/(beat_dur/4))):
            pos = int(i*beat_dur/4*sr)
            if pos >= n_samples: break
            chord_idx = (i // 4) % len(progression)
            chord_root = progression[chord_idx]
            arp_interval = [0, 2, 4, 2][i % 4]
            note = scale[(chord_root + arp_interval) % len(scale)]
            a_dur = beat_dur * 0.22
            a = arp_note(freq(root, note + 12, random.choice([0, 1])), a_dur)
            a *= 0.18 * energy
            end = min(pos + len(a), n_samples)
            sec[pos:end] += a[:end-pos]
    elif section_type in ['verse', 'chorus']:
        skip = 3 if section_type == 'verse' else 2
        for i in range(int(dur/(beat_dur/skip))):
            if random.random() > 0.5:
                continue
            pos = int(i*beat_dur/skip*sr)
            if pos >= n_samples: break
            current_note = markov_next(current_note)
            n_dur = beat_dur*0.35 if random.random() > 0.3 else beat_dur*0.7
            m = pluck(freq(root, current_note, 1), n_dur)
            m *= 0.22*energy
            end = min(pos+len(m), n_samples)
            sec[pos:end] += m[:end-pos]
    
    # ── Vocal Layer — rich and prominent ──
    vocal_track = np.zeros(n_samples)
    if is_lofi and section_type in ['verse', 'chorus', 'bridge']:
        vocal_note = scale[progression[0] % len(scale)]
        vocal_freq = freq(root, vocal_note, 1)
        
        if section_type == 'chorus':
            # Rich chorus vocals — two layers
            vow1 = random.choice(['ooh', 'aah'])
            v1 = vocal_ooh_aah(vocal_freq, dur, vow1, sr)
            v1 *= 0.30 * energy
            # Second voice a 3rd above
            vow2 = random.choice(['ooh', 'mm'])
            third_freq = vocal_freq * 1.26
            v2 = vocal_ooh_aah(third_freq, dur, vow2, sr) * 0.15 * energy
            v = v1[:n_samples] + v2[:len(v1)]
            v = v[:n_samples] if len(v) > n_samples else np.pad(v, (0, n_samples-len(v)))
        elif section_type == 'bridge':
            # Bridge: lush humming with 3 harmonies
            vow = random.choice(['mm', 'oo', 'oh'])
            v = vocal_pad(vocal_freq * 0.95, dur, vow, voices=5, sr=sr)
            v *= 0.24 * energy
        else:
            # Verse: warm vocal pad
            vow = random.choice(['oo', 'mm', 'oh', 'nn'])
            v = vocal_pad(vocal_freq, dur, vow, voices=5, sr=sr)
            v *= 0.20 * energy
        
        v_len = min(len(v), n_samples)
        vocal_track[:v_len] += v[:v_len]
    
    sec += vocal_track
    
    return sec, vocal_track

# ─── Main Generator ───
def generate_track(style, duration, mood="", sr=SAMPLE_RATE):
    configs = {
        'Lofi Hip Hop': {'bpm':random.randint(72,88), 'root':220, 'scale':'pentatonic'},
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
            sections += [('bridge', 4, 0.75)]
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
    
    # ── Lofi processing ──
    if style == 'Lofi Hip Hop':
        print("  Lofi: sidechain + vinyl + tape + analog warmth")
        # Sidechain
        kick_trigger = np.zeros(total_samples)
        for i in range(int(duration/beat_dur)):
            pos = int(i*beat_dur*sr)
            if pos >= total_samples: break
            if i % 4 == 0:
                k = kick(bpm)
                end = min(pos+len(k), total_samples)
                kick_trigger[pos:end] += k[:end-pos]
        master = sidechain_compress(master, kick_trigger, threshold=0.2, ratio=6.0, release=0.12)
        
        # Vinyl texture (very subtle)
        crackle = vinyl_crackle(duration, density=0.12)
        master[:len(crackle)] += crackle[:len(master)] * 0.6
        hiss = vinyl_hiss(duration)
        master[:len(hiss)] += hiss[:len(master)] * 0.4
        
        # Tape wobble
        master = tape_wobble(master, rate=0.18, depth=0.0008)
        
        # Analog warmth
        master = analog_warmth(master, sr)
    
    # ── Master chain — rich and polished ──
    fx_chain = "warmth → compress → reverb → delay"
    if style in ['Cyberpunk', 'Synthpop', 'Techno']:
        fx_chain += " → phaser"
    fx_chain += " → stereo → tape → limit"
    print(f"  Master: {fx_chain}")
    
    # Multi-stage compression
    master = compressor(master, threshold=0.55, ratio=2.5, attack=0.008, release=0.15)
    master = compressor(master, threshold=0.7, ratio=2.0, attack=0.02, release=0.3)  # glue
    
    # Reverb (lush but controlled)
    master = reverb(master, delays=[0.02, 0.035, 0.05, 0.07, 0.095, 0.125],
                    decays=[0.4, 0.3, 0.22, 0.15, 0.08, 0.04])
    
    # Tempo-synced delay
    master = delay(master, dt=beat_dur*0.75, fb=0.2, mix=0.10)
    
    if style in ['Cyberpunk', 'Synthpop', 'Techno']:
        master = phaser(master, rate=0.25, depth=0.35)
    
    master = stereo_widen(master)
    
    # Final tape saturation (warm clipping)
    master = tape_saturate(master, 1.15)
    
    # EQ sculpting
    master = lowpass(master, 16500)
    master = highpass(master, 22)
    
    # Soft clip then limit
    master = soft_clip(master, 0.65)
    master = limiter(master, 0.90)
    
    return master[:total_samples]

# ─── CLI ───
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ToneForge v5 — Professional Lofi")
    parser.add_argument("--style", default="Lofi Hip Hop")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="")
    args = parser.parse_args()
    
    print(f"🎵 ToneForge v5 — {args.style} | {args.duration}s")
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
