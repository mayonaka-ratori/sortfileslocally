
import torch
import sys
import os

def check_environment():
    print("=== Environment Check ===")
    
    # 1. Python Version
    print(f"Python: {sys.version}")
    
    # 2. CUDA Availability
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA Version: {torch.version.cuda}")
        print(f"Device Count: {torch.cuda.device_count()}")
        print(f"Current Device: {torch.cuda.current_device()}")
        print(f"Device Name: {torch.cuda.get_device_name(0)}")
        
        # Check Tensor Cores (Volta or newer)
        # RTX 4070 is Ada Lovelace (Compute Capability 8.9)
        cap = torch.cuda.get_device_capability(0)
        print(f"Compute Capability: {cap[0]}.{cap[1]}")
        if cap[0] >= 7:
            print("✅ Tensor Cores supported (Volta+).")
        else:
            print("⚠️ Old GPU architecture. Performance may be limited.")
            
    else:
        print("❌ CUDA NOT DETECTED. Using CPU (Slow).")

    # 3. Import Checks
    try:
        import insightface
        print(f"InsightFace: Installed ({insightface.__version__})")
    except ImportError:
        print("❌ InsightFace: Not installed.")

    try:
        import open_clip
        print("OpenCLIP: Installed")
    except ImportError:
        print("❌ OpenCLIP: Not installed.")
        
    try:
        import decord
        print("Decord: Installed")
    except ImportError:
        print("❌ Decord: Not installed.")

if __name__ == "__main__":
    check_environment()
