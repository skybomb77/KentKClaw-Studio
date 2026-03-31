import mido
from mido import Message, MidiFile, MidiTrack

def create_midi(output_file="KentKClaw-Studio/audio_output/neon_nostalgia.mid"):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    
    # Setup
    track.append(Message('program_change', program=4, time=0)) # Electric Piano
    
    # Tempo 95 BPM -> 631578 microseconds per beat
    # time in mido is in ticks (default 480 per beat)
    ticks_per_beat = 480
    
    # Helper to add note
    def add_note(note, velocity, duration_beats, start_time_beats):
        # Note on
        # We need to calculate delta time from the previous event. 
        # But constructing linear track is easier if we sort events.
        pass

    # Let's build a list of events (absolute time in beats, type, note, velocity)
    events = []
    
    # 1. Chords (Dm9 - G13 - CMaj9 - Am7)
    # Dm9: D4, F4, A4, C5, E5 (62, 65, 69, 72, 76)
    # G13: G3, B3, D4, F4, E4 (55, 59, 62, 65, 64)
    # CMaj9: C4, E4, G4, B4, D5 (60, 64, 67, 71, 74)
    # Am7: A3, C4, E4, G4 (57, 60, 64, 67)
    
    chords = [
        ([62, 65, 69, 72, 76], 0, 4),   # Dm9
        ([55, 59, 62, 65, 64], 4, 4),   # G13
        ([60, 64, 67, 71, 74], 8, 4),   # CMaj9
        ([57, 60, 64, 67], 12, 4)       # Am7
    ]
    
    for notes, start, duration in chords:
        for note in notes:
            # Staggered start (strumming effect)
            strum = (note % 5) * 0.05 
            events.append((start + strum, 'note_on', note, 60))
            events.append((start + duration, 'note_off', note, 0))
            
    # 2. Melody (Lower octave)
    # E3, D3, C3, B2, A2, G2
    # 52, 50, 48, 47, 45, 43
    melody = [
        (52, 0, 4),
        (50, 4, 4),
        (48, 8, 1),
        (47, 9, 1),
        (45, 10, 2),
        (43, 12, 4)
    ]
    
    for note, start, duration in melody:
        events.append((start, 'note_on', note, 80)) # Louder
        events.append((start + duration, 'note_off', note, 0))
        
    # Sort by time
    events.sort(key=lambda x: x[0])
    
    # Write to track
    last_time = 0
    for time, type, note, velocity in events:
        delta_beats = time - last_time
        delta_ticks = int(delta_beats * ticks_per_beat)
        track.append(Message(type, note=note, velocity=velocity, time=delta_ticks))
        last_time = time

    mid.save(output_file)
    print(f"Saved {output_file}")

if __name__ == "__main__":
    create_midi()
