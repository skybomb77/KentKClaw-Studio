import json, urllib.request, random, sys

workflow = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": random.randint(1, 999999999),
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 0.45,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["12", 0]
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.safetensors"
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "gentle breathing motion, soft ambient glow, cinematic lighting",
            "clip": ["4", 1]
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "blurry, low quality, watermark, text",
            "clip": ["4", 1]
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "frameforge_test",
            "images": ["8", 0]
        }
    },
    "10": {
        "class_type": "LoadImage",
        "inputs": {
            "image": "test_image.png"
        }
    },
    "12": {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": ["10", 0],
            "vae": ["4", 2]
        }
    }
}

data = json.dumps({"prompt": workflow}).encode()
req = urllib.request.Request(
    "http://localhost:8188/prompt",
    data=data,
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}")
