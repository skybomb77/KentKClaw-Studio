import torch
import torchaudio
from audiocraft.models import MusicGen
from audiocraft.data.audio import audio_write
import argparse
import os
import random

def forge_professional_music(style, mood, duration, output_path):
    print(f"--- Pro Forge Starting: {style} ({duration}s) ---")
    
    # 使用 Meta 的 MusicGen 模型 (small 版適合 12GB VRAM 快速生成)
    # 第一次執行會下載模型，約 2GB
    model = MusicGen.get_pretrained('facebook/musicgen-small')
    model.set_generation_params(duration=duration)

    # 組合專業 Prompt
    descriptions = [f"{style}, {mood}, high fidelity, professional studio mix, masterpiece, 44.1kHz"]
    
    # 生成
    wav = model.generate(descriptions) # [1, 1, samples]
    
    # 儲存 (audio_write 會自動處理格式)
    # output_path 如果帶 .wav 會被 audio_write 重複加，所以去掉後綴
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
        # 這裡可以根據 VRAM 狀況選擇傳統引擎或 Pro 引擎
        # 目前我們先強制啟用 Pro 引擎測試質感
        forge_professional_music(args.style, args.mood, args.duration, args.output)
    except Exception as e:
        print(f"Pro Forge Error: {e}")
        # 如果 Pro 引擎失敗（如 OOM），可以考慮 fallback 回原本的 DSP 引擎
        print("Falling back to DSP Engine...")
        # (這裡原本 generate_music.py 的內容可以放進來作為 fallback)
