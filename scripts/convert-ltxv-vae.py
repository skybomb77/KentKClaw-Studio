#!/usr/bin/env python3
"""Convert LTXV diffusers VAE to ComfyUI-compatible format."""
import safetensors.torch
import torch
import torch.nn as nn

src = "/home/skybo/ComfyUI/models/vae/ltxv_vae_diffusion_pytorch_model.safetensors"
dst = "/home/skybo/ComfyUI/models/vae/ltxv_vae_comfy.safetensors"

print("Loading LTXV VAE...")
state = safetensors.torch.load_file(src)

# Check if it's a diffusers 3D VAE (has encoder./decoder. prefixes without quant_conv)
# ComfyUI expects: encoder.conv_in.weight, decoder.conv_in.weight, quant_conv.weight, post_quant_conv.weight
# LTXV has: encoder.conv_in.conv.weight, decoder.conv_in.conv.weight (nested .conv. layer)

# Check structure
sample_keys = list(state.keys())
print(f"Total keys: {len(sample_keys)}")

# LTXV VAE uses .conv. nesting - need to flatten
# Also needs quant_conv and post_quant_conv (identity 1x1 convolutions)
# Check latent channels from encoder output
encoder_out_key = None
for k in state:
    if 'encoder.conv_out' in k and 'weight' in k:
        encoder_out_key = k
        break

if encoder_out_key:
    latent_channels = state[encoder_out_key].shape[0]
    print(f"Latent channels: {latent_channels}")
else:
    latent_channels = 128  # LTXV default
    print(f"Using default latent channels: {latent_channels}")

# Build new state dict with ComfyUI-compatible keys
new_state = {}

for key, tensor in state.items():
    # Flatten nested .conv. layers: encoder.conv_in.conv.weight -> encoder.conv_in.weight
    if '.conv.' in key:
        parts = key.split('.conv.')
        if len(parts) == 2:
            new_key = parts[0] + '.' + parts[1]
            new_state[new_key] = tensor
            continue
    new_state[key] = tensor

# Add identity quant_conv and post_quant_conv if missing
# These are typically Conv2d(4, 4, 1) or Conv2d(latent_ch, latent_ch, 1) in SD VAEs
# For 3D VAEs they might be Conv3d
if 'quant_conv.weight' not in new_state:
    # Find the encoder output to determine if it's 2D or 3D
    enc_out = new_state.get('encoder.conv_out.weight')
    if enc_out is not None:
        is_3d = len(enc_out.shape) == 5  # Conv3d weights are 5D
        if is_3d:
            ch = enc_out.shape[0]
            # Conv3d identity: ch -> ch, kernel 1x1x1
            new_state['quant_conv.weight'] = torch.eye(ch).unsqueeze(-1).unsqueeze(-1).unsqueeze(-1)
            new_state['quant_conv.bias'] = torch.zeros(ch)
            new_state['post_quant_conv.weight'] = torch.eye(ch).unsqueeze(-1).unsqueeze(-1).unsqueeze(-1)
            new_state['post_quant_conv.bias'] = torch.zeros(ch)
            print(f"Added Conv3d identity quant_conv/post_quant_conv ({ch} channels)")
        else:
            ch = enc_out.shape[0]
            new_state['quant_conv.weight'] = torch.eye(ch).unsqueeze(-1).unsqueeze(-1)
            new_state['quant_conv.bias'] = torch.zeros(ch)
            new_state['post_quant_conv.weight'] = torch.eye(ch).unsqueeze(-1).unsqueeze(-1)
            new_state['post_quant_conv.bias'] = torch.zeros(ch)
            print(f"Added Conv2d identity quant_conv/post_quant_conv ({ch} channels)")

print(f"New state dict: {len(new_state)} keys")

# Save
safetensors.torch.save_file(new_state, dst)
print(f"Saved to {dst}")
print("Done!")
