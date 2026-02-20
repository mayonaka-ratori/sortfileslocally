from PIL import Image
import numpy as np

def compute_dhash(image_path: str, hash_size: int = 8) -> str:
    """
    Compute difference hash (dHash) for an image.
    Robust to resizing and slight color shifts.
    """
    try:
        with Image.open(image_path) as img:
            # 1. Grayscale
            img = img.convert("L")
            # 2. Resize to (width=hash_size+1, height=hash_size)
            # using LANCZOS for quality downsampling, though bilinear is fine for hash
            img = img.resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
            
            pixels = np.array(img.getdata(), dtype=np.int8).reshape((hash_size, hash_size + 1))
            
            # 3. Compare adjacent pixels
            # if P[x] > P[x+1] -> 1 else 0
            diff = pixels[:, 1:] > pixels[:, :-1]
            
            # 4. Create hash
            return _binary_array_to_hex(diff.flatten())
            
    except Exception as e:
        print(f"Error hashing {image_path}: {e}")
        return ""

def _binary_array_to_hex(arr: np.ndarray) -> str:
    bit_string = "".join(["1" if b else "0" for b in arr])
    return hex(int(bit_string, 2))[2:].rjust(len(arr)//4, '0')

def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate hamming distance between two hex strings."""
    if not hash1 or not hash2:
        return 999
        
    # Convert to int
    h1 = int(hash1, 16)
    h2 = int(hash2, 16)
    
    # XOR
    x = h1 ^ h2
    
    # Count bits
    return bin(x).count('1')
