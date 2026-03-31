import numpy as np
from scipy.io.wavfile import write
import random

# Configuration for "Neon Nostalgia"
SAMPLE_RATE = 44100
BPM = 95
BEAT_DURATION = 60 / BPM
BAR_DURATION = BEAT_DURATION * 4
# TOTAL_DURATION = BAR_DURATION * 4  # OLD: 4 bars loop (approx 10s)
TOTAL_DURATION = 180 # NEW: 3 minutes target

def generate_sine_wave(freq, duration, volume=0.5):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    wave = volume * np.sin(2 * np.pi * freq * t)
    # Smooth envelope
    envelope = np.concatenate([
        np.linspace(0, 1, int(SAMPLE_RATE * 0.05)),
        np.ones(int(SAMPLE_RATE * (duration - 0.1))),
        np.linspace(1, 0, int(SAMPLE_RATE * 0.05))
    ])
    if len(envelope) < len(wave):
        envelope = np.pad(envelope, (0, len(wave) - len(envelope)), 'constant')
    return wave * envelope[:len(wave)]

def generate_saw_wave(freq, duration, volume=0.3):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Switch to Sine/Triangle for sleepier feel (Saw is too buzzy)
    wave = volume * np.sin(2 * np.pi * freq * t)
    # Add a bit of 3rd harmonic for warmth (Triangle-ish)
    wave += (volume * 0.2) * np.sin(2 * np.pi * freq * 3 * t)

    # Longer attack/release for pads
    envelope = np.concatenate([
        np.linspace(0, 1, int(SAMPLE_RATE * 0.5)), # Slow attack
        np.ones(int(SAMPLE_RATE * (duration - 1.0))),
        np.linspace(1, 0, int(SAMPLE_RATE * 0.5))  # Slow release
    ])
    if len(envelope) < len(wave):
        envelope = np.pad(envelope, (0, len(wave) - len(envelope)), 'constant')
    return wave * envelope[:len(wave)]

def create_drum_beat(total_samples):
    beat = np.zeros(total_samples)
    samples_per_beat = int(SAMPLE_RATE * BEAT_DURATION)
    
    # Kick (Deep, soft) -> Softer attack, lower freq
    kick_len = int(SAMPLE_RATE * 0.3)
    t = np.linspace(0, 0.3, kick_len)
    kick = 0.6 * np.sin(2 * np.pi * np.linspace(80, 30, kick_len) * t) * np.exp(-10 * t) # Lower pitch, softer

    # Snare (Crisp) -> Replaced with soft rimshot/clap feel
    snare_len = int(SAMPLE_RATE * 0.1)
    t_snare = np.linspace(0, 0.1, snare_len)
    snare = 0.3 * np.random.normal(0, 1, snare_len) * np.exp(-30 * t_snare) # Quieter noise

    # Hats (Closed) -> Super soft shaker
    hat_len = int(SAMPLE_RATE * 0.05)
    hat = 0.1 * np.random.normal(0, 1, hat_len) * np.exp(-50 * np.linspace(0, 0.05, hat_len))

    # Vinyl crackle (Rain) -> Boosted slightly for ambiance
    noise_bg = np.random.normal(0, 0.015, total_samples) # 0.01 -> 0.015

    for i in range(16):
        pos = i * samples_per_beat
        
        # Kick: 1, 3 (plus syncopation)
        if i % 4 == 0 or (i % 16 == 10): 
            end = min(pos + kick_len, total_samples)
            beat[pos:end] += kick[:end-pos]
            
        # Snare: 2, 4
        if i % 4 == 2: # Delayed feel (beat 3 in 4/4 is index 2 here? No, index 4 is beat 2)
             # Wait, 16 steps. Beat 1=0, Beat 2=4, Beat 3=8, Beat 4=12
             pass
        if i % 16 == 4 or i % 16 == 12:
            end = min(pos + snare_len, total_samples)
            beat[pos:end] += snare[:end-pos]

        # Hats: Every 8th
        for k in range(2):
            hat_pos = pos + int(k * samples_per_beat / 2)
            end = min(hat_pos + hat_len, total_samples)
            if end > hat_pos:
                beat[hat_pos:end] += hat[:end-hat_pos]
             
    return beat

def create_chords(total_samples):
    track = np.zeros(total_samples)
    samples_per_bar = int(SAMPLE_RATE * BAR_DURATION)
    
    # Dm9 - G13 - CMaj9 - Am7
    chords = [
        [293.66, 349.23, 440.00, 523.25, 659.25], # Dm9
        [196.00, 246.94, 293.66, 349.23, 329.63], # G13
        [261.63, 329.63, 392.00, 493.88, 587.33], # CMaj9
        [220.00, 261.63, 329.63, 392.00]          # Am7
    ]
    
    for i, chord in enumerate(chords):
        pos = i * samples_per_bar
        end = min(pos + samples_per_bar, total_samples)
        duration = (end - pos) / SAMPLE_RATE
        
        for freq in chord:
            track[pos:end] += generate_saw_wave(freq, duration, volume=0.08)

    return track

def create_melody(total_samples):
    track = np.zeros(total_samples)
    samples_per_beat = int(SAMPLE_RATE * BEAT_DURATION)
    
    # E ... D ... C-B-A ... G -> Lower octave for sleep
    melody_notes = [
        (329.63, 0, 4),   # E4 -> E3
        (293.66, 4, 4),   # D4 -> D3
        (261.63, 8, 1),   # C4 -> C3
        (246.94, 9, 1),   # B3 -> B2
        (220.00, 10, 2),  # A3 -> A2
        (196.00, 12, 4),  # G3 -> G2
    ]
    
    for freq, start_beat, duration_beats in melody_notes:
        pos = start_beat * samples_per_beat
        duration_sec = duration_beats * BEAT_DURATION
        end = min(pos + int(duration_sec * SAMPLE_RATE), total_samples)
        
        # Super soft sine with slow envelope
        t = np.linspace(0, duration_sec, int(SAMPLE_RATE * duration_sec), endpoint=False)
        wave = 0.15 * np.sin(2 * np.pi * freq * t) # Quieter
        env = np.concatenate([
             np.linspace(0, 1, int(SAMPLE_RATE * 0.1)),
             np.linspace(1, 0, int(SAMPLE_RATE * (duration_sec - 0.1))) # Long decay like a bell
        ])
        if len(env) < len(wave):
             env = np.pad(env, (0, len(wave) - len(env)), 'constant')
             
        track[pos:end] += wave[:end-pos] * env[:end-pos]
        
    return track

from scipy.io import wavfile

def load_and_process_vocals(total_samples):
    track = np.zeros(total_samples)
    samples_per_beat = int(SAMPLE_RATE * BEAT_DURATION)
    
    # Load raw vocal
    try:
        rate, data = wavfile.read('KentKClaw-Studio/audio_output/vocal_raw.wav')
        # Normalize to float -1..1
        if data.dtype == np.int16:
            data = data / 32768.0
        
        # If stereo, take mono
        if len(data.shape) > 1:
            data = data[:, 0]
            
        # Resample if needed (simple linear interpolation or just assume 44100 since we ffmpeg'd it)
        # We did ffmpeg -ar 44100, so rate should be 44100.
        
        # Pitch shift effect (simple speed change = resampling)
        # To shift pitch up, we play it faster (fewer samples)
        # Shift +2 semitones = 2^(2/12) ~= 1.122
        speed_factor = 1.12
        new_len = int(len(data) / speed_factor)
        data_shifted = np.interp(
            np.linspace(0, len(data), new_len),
            np.arange(len(data)),
            data
        )
        
        # Chop it!
        # "I miss..." -> start 0, take 0.5s
        # "...rain" -> start 1.2s, take 0.5s
        chop1_start = int(0.0 * SAMPLE_RATE)
        chop1_len = int(0.5 * SAMPLE_RATE)
        chop1 = data_shifted[chop1_start : chop1_start + chop1_len] * 1.5 # Boost vol
        
        chop2_start = int(1.0 * SAMPLE_RATE) # Approximate "rain"
        chop2_len = int(0.6 * SAMPLE_RATE)
        chop2 = data_shifted[chop2_start : chop2_start + chop2_len] * 1.5
        
        # Place chops in the beat
        # Bar 2, Beat 1: "I miss"
        pos1 = (4) * samples_per_beat # Bar 2 start
        end1 = min(pos1 + len(chop1), total_samples)
        track[pos1:end1] += chop1[:end1-pos1]
        
        # Bar 2, Beat 2.5: "rain" (Syncopated)
        pos2 = int((4 + 2.5) * samples_per_beat)
        end2 = min(pos2 + len(chop2), total_samples)
        track[pos2:end2] += chop2[:end2-pos2]
        
        # Bar 4, Beat 1: "Stay..."
        # Let's reuse chop1 for echo effect
        pos3 = (12) * samples_per_beat
        end3 = min(pos3 + len(chop1), total_samples)
        track[pos3:end3] += chop1[:end3-pos3] * 0.8 # Quieter
        
        # Add simple delay/echo to the whole vocal track
        delay_samples = int(SAMPLE_RATE * (60/BPM) * 0.5) # 8th note delay
        track_delayed = np.zeros_like(track)
        track_delayed[delay_samples:] = track[:-delay_samples] * 0.4
        track += track_delayed

    except Exception as e:
        print(f"Warning: Could not load vocals: {e}")
        
    return track

# Generate
print("Compiling Neon Nostalgia (Extended)...")
total_samples = int(SAMPLE_RATE * TOTAL_DURATION)
final_mix = np.zeros(total_samples)

# Loop the composition to fill duration
# Basic loop length in samples
loop_bars = 4
loop_samples = int(SAMPLE_RATE * BAR_DURATION * loop_bars)

# Generate one loop first
one_loop = np.zeros(loop_samples)
one_loop += create_drum_beat(loop_samples)
one_loop += create_chords(loop_samples)
one_loop += create_melody(loop_samples)

def apply_filter_sweep(audio_data):
    # Apply a Low-Pass Filter sweep (Low -> High -> Low) to create movement
    # Simple moving average implementation for LPF
    # We'll vary the window size: Larger window = Lower cutoff
    
    length = len(audio_data)
    swept_audio = np.zeros(length)
    
    # Sweep LFO (0 to 1) very slow
    t = np.linspace(0, 1, length)
    lfo = 0.5 + 0.4 * np.sin(2 * np.pi * 0.05 * t) # 0.05Hz = 20s cycle
    
    # Process in chunks to simulate time-variant filter
    chunk_size = 1000
    for i in range(0, length, chunk_size):
        chunk = audio_data[i:i+chunk_size]
        # Map LFO to filter intensity (window size 1 to 50)
        current_lfo = lfo[i]
        window_size = int(1 + 50 * (1 - current_lfo)) # High LFO = Small window (Bright)
        
        kernel = np.ones(window_size) / window_size
        # Apply filter
        filtered_chunk = np.convolve(chunk, kernel, mode='same')
        swept_audio[i:i+chunk_size] = filtered_chunk
        
    return swept_audio

# Tile it to fill total duration but add variation
repeats = int(np.ceil(total_samples / loop_samples))
full_track = np.zeros(total_samples)

for i in range(repeats):
    start = i * loop_samples
    end = min(start + loop_samples, total_samples)
    
    # Base loop
    segment = one_loop[:end-start]
    
    # Variation 1: Drop percussion every 4th loop
    if i % 4 == 3:
        # Re-generate simple loop without drums
        chords_only = np.zeros(loop_samples)
        chords_only += create_chords(loop_samples)
        chords_only += create_melody(loop_samples)
        segment = chords_only[:end-start]
        
    # Variation 2: Add random high-pitch "sparkles" (piano high notes)
    if i % 2 == 1:
        sparkle = np.zeros(len(segment))
        sparkle_t = np.linspace(0, len(segment)/SAMPLE_RATE, len(segment))
        # Random pentatonic notes
        for _ in range(2):
            pos = random.randint(0, len(segment)-10000)
            freq = random.choice([523.25, 659.25, 783.99]) * 2 # High C, E, G
            note = 0.1 * np.sin(2*np.pi*freq*sparkle_t[:10000]) * np.exp(-5*sparkle_t[:10000])
            sparkle[pos:pos+10000] += note
        segment += sparkle

    full_track[start:end] = segment

# Apply Filter Sweep to whole track
full_track = apply_filter_sweep(full_track)

# Add continuous background noise (Rain/Vinyl) for the whole track to avoid loop seams
noise = np.random.normal(0, 0.015, total_samples)
final_mix = full_track + noise

# Normalize
final_mix = final_mix / np.max(np.abs(final_mix))

output_file = "KentKClaw-Studio/audio_output/neon_nostalgia_pure.wav"
write(output_file, SAMPLE_RATE, final_mix.astype(np.float32))
print(f"Saved to {output_file}")
