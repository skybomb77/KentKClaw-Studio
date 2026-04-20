#!/usr/bin/env python3
"""FrameForge — Image-to-Video pipeline via ComfyUI + ffmpeg"""
import json, urllib.request, time, subprocess, os, sys, random

COMFYUI = "http://localhost:8188"
INPUT_DIR = "/home/skybo/ComfyUI/input"
OUTPUT_DIR = "/home/skybo/ComfyUI/output"

def submit_workflow(image_name, prompt, neg_prompt, seed, denoise, steps=20):
    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed, "steps": steps, "cfg": 7.0,
                "sampler_name": "euler", "scheduler": "normal", "denoise": denoise,
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["12", 0]
            }
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": neg_prompt, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "frameforge_anim", "images": ["8", 0]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "12": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}}
    }
    data = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(f"{COMFYUI}/prompt", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"]

def wait_for_completion(prompt_id, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        resp = urllib.request.urlopen(f"{COMFYUI}/history/{prompt_id}")
        history = json.loads(resp.read())
        if prompt_id in history:
            status = history[prompt_id].get("status", {}).get("status_str")
            if status == "success":
                return True
            elif status == "error":
                return False
        time.sleep(2)
    return False

def main():
    if len(sys.argv) < 3:
        print("Usage: frameforge_gen.py <input_image> <output_video>")
        sys.exit(1)
    
    input_image = sys.argv[1]
    output_video = sys.argv[2]
    image_name = os.path.basename(input_image)
    
    # Copy input to ComfyUI input dir
    subprocess.run(["cp", input_image, f"{INPUT_DIR}/{image_name}"], check=True)
    
    prompt = sys.argv[4] if len(sys.argv) > 4 else "gentle breathing motion, soft ambient glow, cinematic lighting, beautiful"
    neg = "blurry, low quality, watermark, text, deformed, flickering"
    num_frames = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    
    base_seed = random.randint(1, 999999)
    
    print(f"🎬 FrameForge: Generating {num_frames} frames from {image_name}")
    print(f"   Prompt: {prompt}")
    
    frame_dir = "/tmp/frameforge_frames"
    os.makedirs(frame_dir, exist_ok=True)
    
    for i in range(num_frames):
        denoise = 0.3 + (i * 0.03)  # Progressive denoise
        seed = base_seed + i
        print(f"   Frame {i+1}/{num_frames} (denoise={denoise:.2f}, seed={seed})...")
        
        pid = submit_workflow(image_name, prompt, neg, seed, denoise)
        if not wait_for_completion(pid):
            print(f"   ❌ Frame {i+1} failed!")
            continue
        
        # Find and copy the output
        time.sleep(1)
        outputs = sorted([f for f in os.listdir(OUTPUT_DIR) if f.startswith("frameforge_anim")])
        if outputs:
            latest = os.path.join(OUTPUT_DIR, outputs[-1])
            frame_path = os.path.join(frame_dir, f"frame_{i:04d}.png")
            subprocess.run(["cp", latest, frame_path])
            print(f"   ✅ Frame {i+1} saved")
    
    # Combine frames into video with ffmpeg
    print(f"🎞️  Combining {num_frames} frames into video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", f"{frame_dir}/frame_%04d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-vf", "minterpolate=fps=24:mi_mode=mci",
        output_video
    ], check=True)
    
    size = os.path.getsize(output_video) / 1024 / 1024
    print(f"✅ Done! Output: {output_video} ({size:.1f}MB)")

if __name__ == "__main__":
    main()
