import platform
import psutil
import torch
import shutil
import json
import time

def generate_report() -> dict:
    """Auto-detect hardware, memory, and simple benchmark."""
    
    # OS & CPU Info
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    cpu_info = platform.processor()
    cores = psutil.cpu_count(logical=False)
    threads = psutil.cpu_count(logical=True)
    
    # RAM
    ram_info = psutil.virtual_memory()
    total_ram_gb = round(ram_info.total / (1024**3), 2)
    avail_ram_gb = round(ram_info.available / (1024**3), 2)
    
    # Disk Space (Root)
    disk_usage = shutil.disk_usage("/")
    free_disk_gb = round(disk_usage.free / (1024**3), 2)
    
    # GPU / VRAM via PyTorch
    gpu_available = torch.cuda.is_available()
    gpu_name = "None"
    vram_gb = 0.0
    if gpu_available:
        gpu_name = torch.cuda.get_device_name(0)
        vram_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_gb = round(vram_bytes / (1024**3), 2)
    
    # Micro-Benchmark (matrix multiplication to simulate inference load)
    benchmark_ms = -1
    if gpu_available:
        try:
            device = torch.device('cuda')
            # Warmup
            m1 = torch.randn(1000, 1000, device=device)
            m2 = torch.randn(1000, 1000, device=device)
            torch.matmul(m1, m2)
            torch.cuda.synchronize()
            
            start = time.perf_counter()
            for _ in range(10):
                torch.matmul(m1, m2)
            torch.cuda.synchronize()
            benchmark_ms = (time.perf_counter() - start) * 1000 / 10
        except Exception:
            benchmark_ms = -1
    else:
        # CPU benchmark fallback
        try:
            m1 = torch.randn(1000, 1000)
            m2 = torch.randn(1000, 1000)
            start = time.perf_counter()
            for _ in range(10):
                torch.matmul(m1, m2)
            benchmark_ms = (time.perf_counter() - start) * 1000 / 10
        except Exception:
            benchmark_ms = -1

    return {
        "os": os_info,
        "cpu": f"{cpu_info} ({cores}C/{threads}T)",
        "ram": f"{avail_ram_gb}GB free / {total_ram_gb}GB total",
        "disk": f"{free_disk_gb}GB free",
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
        "benchmark_matmul_avg_ms": round(benchmark_ms, 2)
    }

if __name__ == "__main__":
    print(json.dumps(generate_report(), indent=4))
