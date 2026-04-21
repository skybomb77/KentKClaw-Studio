import json
import urllib.request

prompt = {
    "1": {
        "class_type": "UNETLoader",
        "inputs": {
            "unet_name": "ltxv-2b-0.9.8-distilled-fp8.safetensors",
            "weight_dtype": "fp8_e4m3fn"
        }
    },
    "2": {
        "class_type": "CLIPLoader",
        "inputs": {
            "clip_name": "umt5-xxl-enc-fp8_e4m3fn.safetensors",
            "type": "ltxv"
        }
    },
    "3": {
        "class_type": "VAELoader",
        "inputs": {
            "vae_name": "ltxv_vae_comfy.safetensors"
        }
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "A beautiful golden sunset over calm ocean waves, cinematic lighting, 4k quality, smooth camera pan from left to right, warm colors reflecting on water",
            "clip": ["2", 0]
        }
    },
    "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "blurry, low quality, distorted, watermark, text, static, ugly, deformed",
            "clip": ["2", 0]
        }
    },
    "6": {
        "class_type": "LTXVConditioning",
        "inputs": {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "frame_rate": 24.0
        }
    },
    "7": {
        "class_type": "EmptyLTXVLatentVideo",
        "inputs": {
            "width": 768,
            "height": 512,
            "length": 49,
            "batch_size": 1
        }
    },
    "8": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["6", 0],
            "negative": ["6", 1],
            "latent_image": ["7", 0],
            "seed": 42,
            "steps": 30,
            "cfg": 3.5,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0
        }
    },
    "9": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["8", 0],
            "vae": ["3", 0]
        }
    },
    "10": {
        "class_type": "CreateVideo",
        "inputs": {
            "images": ["9", 0],
            "fps": 24.0
        }
    },
    "11": {
        "class_type": "SaveVideo",
        "inputs": {
            "video": ["10", 0],
            "filename_prefix": "ltxv_test",
            "format": "mp4",
            "codec": "h264"
        }
    }
}

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
