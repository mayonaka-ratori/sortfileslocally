import os
import sys
import time
import json
import argparse
import psutil
import torch
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.processor import Processor
from src.data.db_manager import DBManager

def get_process_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # MB

def get_gpu_memory():
    if torch.cuda.is_available():
        # Returns current allocated memory (tracked by torch)
        return torch.cuda.memory_allocated() / (1024 * 1024)  # MB
    return 0

def benchmark_scan(target_dir, limit=50):
    print(f"Starting benchmark on: {target_dir}")
    print(f"File limit: {limit}")
    
    # Setup
    db_dir = "benchmarks/db"
    if os.path.exists(db_dir):
        import shutil
        shutil.rmtree(db_dir)
    os.makedirs(db_dir, exist_ok=True)
    
    # Initialize Processor and DBManager
    processor = Processor(db_dir=db_dir)
    
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "target_dir": target_dir,
        "file_limit": limit,
        "stages": {},
        "peak_rss_mb": 0,
        "peak_vram_mb": 0,
        "total_files_scanned": 0,
        "newly_processed": 0
    }
    
    total_start = time.time()
    
    # We use the actual Processor.process_folder generator
    print("Running scan pipeline...")
    
    try:
        for status in processor.process_folder(target_dir, force_reprocess=True):
            # Update metrics
            current_rss = get_process_memory()
            current_vram = get_gpu_memory()
            metrics["peak_rss_mb"] = max(metrics["peak_rss_mb"], current_rss)
            metrics["peak_vram_mb"] = max(metrics["peak_vram_mb"], current_vram)
            
            if 'current' in status:
                metrics["total_files_scanned"] = status['current']
                metrics["newly_processed"] = status.get('newly_processed', 0)
                
                if status['current'] % 10 == 0:
                    print(f"  Progress: {status['current']}/{status['total']} (RSS: {current_rss:.1f}MB, VRAM: {current_vram:.1f}MB)")
                
                if status['current'] >= limit:
                    print(f"  Reached limit of {limit} files. Stopping.")
                    break
            
            if 'error' in status:
                print(f"  Error processing {status.get('filename')}: {status['error']}")

    except Exception as e:
        import traceback
        print(f"Fatal benchmark error: {e}")
        traceback.print_exc()
        metrics["fatal_error"] = str(e)

    metrics["total_duration"] = time.time() - total_start
    
    # Final cleanup of DB to release memory
    del processor
    
    # Save report
    report_name = f"scan_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join("benchmarks", report_name)
    with open(report_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"\nBenchmark Result:")
    print(f"  Duration: {metrics['total_duration']:.2f}s")
    print(f"  TPS: {metrics['newly_processed'] / metrics['total_duration']:.2f} files/sec") if metrics['total_duration'] > 0 else None
    print(f"  Peak RSS: {metrics['peak_rss_mb']:.2f} MB")
    print(f"  Peak VRAM: {metrics['peak_vram_mb']:.2f} MB")
    print(f"  Report saved: {report_path}")
    
    return metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_dir", help="Directory to scan")
    parser.add_argument("--limit", type=int, default=50, help="Max files to scan")
    args = parser.parse_args()
    
    if not os.path.exists(args.target_dir):
        print(f"Target directory {args.target_dir} not found.")
        sys.exit(1)
        
    benchmark_scan(args.target_dir, args.limit)
