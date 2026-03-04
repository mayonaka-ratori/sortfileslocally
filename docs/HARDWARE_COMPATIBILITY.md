# Hardware Compatibility Matrix

LocalCurator Prime executes AI models entirely locally. Scan performance and capabilities vary significantly based on your hardware.

## Supported Tiers

| Tier | Description | Minimum Specs | Recommended Profile | Expected Scan Speed |
| ---- | ----------- | ------------- | ------------------- | ------------------- |
| **Tier 1** | Full GPU Acceleration | NVIDIA RTX 2060+, 6GB+ VRAM, 16GB RAM | Full (All Models) | 15-25 items/sec |
| **Tier 2** | Light GPU Acceleration | NVIDIA GTX 1050 Ti, 4GB VRAM, 8GB RAM | Balanced | 5-10 items/sec |
| **Tier 3** | CPU Only (No GPU) | Intel Core i5 / AMD Ryzen 5, 8GB RAM | Lightweight / Balanced | 1-3 items/sec |
| **Tier 4** | Apple Silicon | M1/M2/M3 Base, 8-16GB Unified Memory | Balanced | 8-15 items/sec |

## Known Limitations

- **Tier 3 (CPU Only)**: CLIP embeddings and Whisper transcribe take significantly longer. High CPU usage is expected during initial media scan.
- **AMD GPUs on Windows**: Currently running via CPU fallback or ONNX Runtime DirectML (partial support, slower than NVIDIA CUDA). Official support coming in v1.1.
- **VRAM Constraints**: On Tier 2 devices with 4GB VRAM, the app automatically dynamically loads/unloads models to prevent Out-Of-Memory (OOM) errors.

## Recommended Settings for Older Hardware

If you experience excessive heat or system slowdowns on Tier 3 devices, consider using the **Lightweight** profile via the Initial Setup Wizard.
