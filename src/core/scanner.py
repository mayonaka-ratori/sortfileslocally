
import os
import hashlib
from typing import Iterator, List
from ..data.schemas import MediaItem
from datetime import datetime
from ..config import Config

class Scanner:
    def __init__(self, allowed_extensions: List[str] = None):
        if allowed_extensions is None:
            # Flatten dict from config
            exts = []
            for k, v in Config.ALLOWED_EXTENSIONS.items():
                exts.extend(v)
            self.allowed_extensions = set(exts)
        else:
            self.allowed_extensions = set(ext.lower() for ext in allowed_extensions)
    
    def calculate_md5(self, file_path: str) -> str:
        """
        Calculate a fast fingerprint hash of the file.
        Reads only metadata and head/tail chunks to avoid reading the whole file.
        Highly efficient for large image/video libraries.
        """
        try:
            stat = os.stat(file_path)
            # Combine size and modified time
            fingerprint = f"{stat.st_size}_{stat.st_mtime}"
            
            # Read first 8KB and last 8KB
            with open(file_path, 'rb') as f:
                head = f.read(8192)
                f.seek(max(0, stat.st_size - 8192))
                tail = f.read(8192)
            
            # Build final hash
            data = f"{fingerprint}_{head.hex()}_{tail.hex()}"
            return hashlib.md5(data.encode()).hexdigest()
        except Exception:
            # Fallback to simple path-based hash if something goes wrong
            return hashlib.md5(file_path.encode()).hexdigest()

    def _get_media_type(self, ext: str) -> str:
        for m_type, exts in Config.ALLOWED_EXTENSIONS.items():
            if ext in exts:
                return m_type
        return 'image' # Fallback default


    
    def scan_directory(self, root_dir: str, exclude_dirs: List[str] = None) -> Iterator[str]:
        """Generator that yields file paths recursively. Honors exclude_dirs."""
        exclude_set = set()
        if exclude_dirs:
            for d in exclude_dirs:
                if d and os.path.exists(d):
                    exclude_set.add(os.path.abspath(d))

        for entry in os.scandir(root_dir):
            if entry.is_dir(follow_symlinks=False):
                # Skip .hidden folders
                if entry.name.startswith('.'):
                    continue
                    
                full_path = os.path.abspath(entry.path)
                
                # Check exclude
                is_excluded = False
                for ex in exclude_set:
                     if full_path.startswith(ex):
                         is_excluded = True
                         break
                if is_excluded:
                    continue

                yield from self.scan_directory(entry.path, exclude_dirs=exclude_dirs)
            elif entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in self.allowed_extensions:
                    yield entry.path

    def inspect_file(self, file_path: str) -> MediaItem:
        """Get basic file stats and create MediaItem."""
        stat = os.stat(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        
        return MediaItem(
            file_path=file_path,
            file_hash=self.calculate_md5(file_path),
            file_size=stat.st_size,
            media_type=self._get_media_type(ext),
            created_at=stat.st_ctime,
            modified_at=stat.st_mtime,
            is_processed=False
        )
