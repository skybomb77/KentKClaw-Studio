#!/usr/bin/env python3
"""ToneForge v3 — Advanced DSP Music Generator
- Song structure (intro/verse/chorus/outro)
- Advanced effects (compressor, limiter, phaser, stereo widen)
- Markov chain melody generation
- Multi-section chord progressions
- Supports 15s to 180s
"""
import numpy as np
from scipy.io.wavfile import write as write_wav
from scipy.signal import butter, lfilter, hilbert
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

def compressor(sig, threshold=0.5, ratio=4.0, attack=0.003, release=0.1, sr=SAMPLE_RATE):
    """Dynamic range compressor"""
    env = np.abs(sig)
    # Smooth envelope
    at = int(sr*attack); rt = int(sr*release)
    smooth = np.zeros_like(env)
    smooth[0] = env[0]
    for i in range(1, len(env)):
        if env[i] > smooth[i-1]:
            smooth[i] = smooth[i-1] + (env[i]-smooth[i-1])/max(at, 1)
        else:
            smooth[i] = smooth[i-1] + (env[i]-smooth[i-1])/max(rt, 1)
    # Gain reduction
    gain = np.ones_like(smooth)
    mask = smooth > threshold
    gain[mask] = threshold + (smooth[mask]-threshold)/ratio
    gain[mask] /= smooth[mask]+1e-8
    return sig * gain

def limiter(sig, ceiling=0.95):
    """Brick wall limiter"""
    peak = np.max(np.abs(sig))
    if peak > ceiling:
        sig = sig * (ceiling/peak)
    return np.clip(sig, -ceiling, ceiling)

def stereo_widen(sig, width=1.3):
    """Mid-side stereo widening (returns mono sum for WAV)"""
    # For mono output, apply subtle chorus-like widening
    delayed = np.zeros_like(sig)
    d = int(0.002 * SAMPLE_RATE)
    delayed[d:] = sig[:-d] * 0.15
    return sig + delayed

def phaser(sig, rate=0.5, depth=0.7, sr=SAMPLE_RATE):
    """Simple phaser effect"""
    t = np.arange(len(sig))/sr
    mod = np.sin(2*np.pi*rate*t)
    # Variable delay
    delay = ((mod+1)/2 * 0.005 * sr).astype(int)
    out = sig.copy()
    for i in range(len(sig)):
        j = i - delay[i]
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
# Transition probabilities for pentatonic scale
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
def gen_section(bpm, root, scale_name, bars, energy=1.0, section_type='verse', sr=SAMPLE_RATE):
    """Generate a section of music"""
    beat_dur = 60/bpm
    measure_dur = beat_dur*4
    dur = bars*measure_dur
    n_samples = int(sr*dur)
    sec = np.zeros(n_samples)
    scale = SCALES[scale_name]
    
    prog_options = {
        'intro': [[0,0,0,0], [0,4,0,4]],
        'verse': [[0,3,4,0], [0,4,5,3], [5,2,0,4]],
        'chorus': [[0,4,5,3], [4,5,0,0], [0,5,3,4]],
        'outro': [[0,4,0,0], [4,0,0,0]],
    }
    progs = prog_options.get(section_type, prog_options['verse'])
    progression = random.choice(progs)
    
    # Drums
    if section_type != 'intro' or bars > 2:
        for i in range(int(dur/beat_dur)):
            pos = int(i*beat_dur*sr)
            if pos >= n_samples: break
            beat_in_measure = i % 4
            measure = i // 4
            
            # Kick: skip first bar of intro
            if section_type == 'intro' and measure == 0:
                continue
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
    
    # Bass
    if section_type != 'outro' or bars > 2:
        for i in range(int(dur/(beat_dur*2))):
            pos = int(i*beat_dur*2*sr)
            if pos >= n_samples: break
            note = scale[progression[(i//2)%len(progression)]%len(scale)]
            b = bass(freq(root, note, -1), beat_dur*1.8)
            b *= 0.4*energy
            end = min(pos+len(b), n_samples)
            sec[pos:end] += b[:end-pos]
    
    # Chords/Pad
    for i in range(bars):
        pos = int(i*measure_dur*sr)
        if pos >= n_samples: break
        chord_root = progression[i%len(progression)]
        for iv in [0, 2, 4]:
            note = scale[(chord_root+iv)%len(scale)]
            p = pad(freq(root, note, 0), measure_dur*0.95)
            p *= energy
            end = min(pos+len(p), n_samples)
            sec[pos:end] += p[:end-pos]
    
    # Melody (Markov chain)
    melody_scale = [s+12 for s in scale]
    current_note = random.choice(melody_scale)
    if section_type in ['verse', 'chorus']:
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
    
    return sec

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
    
    # Song structure
    if duration <= 15:
        sections = [('verse', 2, 0.8), ('chorus', 2, 1.0)]
    elif duration <= 30:
        sections = [('intro', 2, 0.4), ('verse', 4, 0.7), ('chorus', 4, 1.0)]
    elif duration <= 60:
        sections = [
            ('intro', 4, 0.3), ('verse', 8, 0.6),
            ('chorus', 8, 0.9), ('verse', 8, 0.65),
            ('chorus', 8, 1.0), ('outro', 4, 0.3),
        ]
    else:
        # 60s+ extended structure
        repeat = max(1, duration // 60)
        sections = [('intro', 4, 0.3)]
        for _ in range(repeat):
            sections += [('verse', 8, 0.6), ('chorus', 8, 0.9)]
            sections += [('verse', 8, 0.65), ('chorus', 8, 1.0)]
        sections.append(('outro', 4, 0.25))
    
    print(f"  Structure: {' → '.join(f'{s[0]}({s[1]}bar)' for s in sections)}")
    
    master = np.zeros(total_samples)
    pos = 0
    for stype, bars, energy in sections:
        sec_dur = bars*measure_dur
        sec = gen_section(bpm, root, scale, bars, energy, stype)
        end = min(pos+len(sec), total_samples)
        master[pos:end] += sec[:end-pos]
        pos = end
        if pos >= total_samples:
            break
    
    # Master chain
    print("  Master chain: compress → reverb → delay → phaser → limit")
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
    parser = argparse.ArgumentParser(description="ToneForge v3")
    parser.add_argument("--style", default="Lofi Hip Hop")
    parser.add_argument("--duration", type=int, default=15)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mood", default="")
    args = parser.parse_args()
    
    print(f"🎵 ToneForge v3 — {args.style} | {args.duration}s")
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
