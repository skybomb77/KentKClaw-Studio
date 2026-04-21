import json
import urllib.request
import time

# Build ComfyUI API prompt format
prompt = {
    "1": {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": "Wan2_1-T2V-1_3B_fp8_e4m3fn.safetensors",
            "weight_dtype": "fp8_e4m3fn"
        }
    },
    "2": {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": "umt5-xxl-enc-fp8_e4m3fn.safetensors",
            "type": "wan"
        }
    },
    "3": {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": "Wan2_2_VAE_bf16.safetensors"
        }
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "A beautiful sunset over the ocean with golden waves, cinematic, 4k, smooth camera movement, warm colors, peaceful",
            "clip": ["2", 0]
        }
    },
    "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "blurry, low quality, distorted, static image, watermark, text, ugly",
            "clip": ["2", 0]
        }
    },
    "6": {
        "class_type": "WanImageToVideo",
        "inputs": {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "vae": ["3", 0],
            "width": 832,
            "height": 480,
            "length": 41,
            "batch_size": 1
        }
    },
    "7": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["6", 0],
            "negative": ["6", 1],
            "latent_image": ["6", 2],
            "seed": 42,
            "steps": 20,
            "cfg": 6.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["7", 0],
            "vae": ["3", 0]
        }
    },
    "9": {
        "class_type": "CreateVideo",
        "inputs": {
            "images": ["8", 0],
            "fps": 16.0
        }
    },
    "10": {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["9", 0],
            "filename_prefix": "wan_test",
            "format": "mp4",
            "codec": "h264"
        }
    }
}

# Queue the prompt
payload = {"prompt": prompt}
req = urllib.request.Request(
    "http://127.0.0.1:8188/prompt",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)

try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(f"Queued! Prompt ID: {result.get('prompt_id')}")
    print(json.dumps(result, indent=2))
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f"Error {e.code}: {error_body}")
except Exception as e:
    print(f"Error: {e}")
