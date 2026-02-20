
import os
import shutil
import datetime
import traceback
from typing import List, Optional
from ..data.schemas import MediaItem

class SortLog:
    def __init__(self, log_dir="data/logs"):
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f"sort_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        self.undo_script = os.path.join(log_dir, f"undo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.bat") # Windows batch for consistency

    def log(self, msg: str):
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now()}: {msg}\n")
            
    def add_undo(self, original_path: str, new_path: str):
        # move "new_path" back to "original_path"
        # Using batch syntax: move "source" "dest"
        cmd = f'move "{new_path}" "{original_path}"\n'
        with open(self.undo_script, "a", encoding="utf-8") as f:
            f.write(cmd)

class PhysicalSorter:
    def __init__(self, log_handler: Optional[SortLog] = None):
        if log_handler:
            self.logger = log_handler
        else:
            self.logger = SortLog()
            
    def sort_file(self, item: MediaItem, dest_root: str, category: str, operation: str = "copy") -> bool:
        """
        Move or Copy file to {dest_root}/{safe_category}/{filename}
        operation: 'copy', 'move', 'dry_run'
        """
        if not os.path.exists(item.file_path):
            self.logger.log(f"ERROR: Source file not found: {item.file_path}")
            return False
            
        try:
            # 1. Sanitize Category Name (Fix for WinError 267 with "re:zero" etc)
            import re
            safe_category = re.sub(r'[<>:"/\\|?*]', '_', category).strip()
            
            # 2. Construct Dest Path
            # Structure: Category / Filename (No Year folder as requested)
            dest_dir = os.path.join(dest_root, safe_category)
            fname = os.path.basename(item.file_path)
            dest_path = os.path.join(dest_dir, fname)
            
            # 3. Handle Collision
            if os.path.exists(dest_path):
                # Check if same file (hash?) - Skip if same
                # For safety, just rename: name_timestamp.ext
                ts = item.created_at or item.modified_at or 0
                base, ext = os.path.splitext(fname)
                dest_path = os.path.join(dest_dir, f"{base}_{int(ts)}{ext}")
                
            if operation == "dry_run":
                self.logger.log(f"DRY RUN: {operation.upper()} {item.file_path} -> {dest_path}")
                return True
                
            # 4. Perform Operation
            os.makedirs(dest_dir, exist_ok=True)
            
            if operation == "move":
                shutil.move(item.file_path, dest_path)
                self.logger.log(f"MOVED: {item.file_path} -> {dest_path}")
                self.logger.add_undo(item.file_path, dest_path)
            elif operation == "copy":
                shutil.copy2(item.file_path, dest_path) # copy2 preserves metadata
                self.logger.log(f"COPIED: {item.file_path} -> {dest_path}")
                # Undo for copy is delete new file
                with open(self.logger.undo_script, "a", encoding="utf-8") as f:
                    f.write(f'del "{dest_path}"\n')
            
            return True
            
        except Exception as e:
            self.logger.log(f"ERROR: Failed to {operation} {item.file_path}: {e}")
            traceback.print_exc()
            return False
