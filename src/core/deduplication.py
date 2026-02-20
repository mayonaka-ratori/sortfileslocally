
import numpy as np
import sqlite3
import os
import faiss
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from ..data.db_manager import DBManager
from ..data.schemas import MediaItem

@dataclass
class DuplicatePair:
    file_a: MediaItem
    file_b: MediaItem
    similarity: float
    recommended_action: str # 'keep_a', 'keep_b', 'review'
    reason: str

class Deduplicator:
    def __init__(self, db_manager: DBManager):
        self.db_manager = db_manager

    def find_duplicates(self, threshold_img: float = 0.95, threshold_vid: float = 0.98) -> List[DuplicatePair]:
        """
        Find duplicate candidates.
        """
        print("Running Deduplication Scan...")
        pairs = []
        
        # 1. Fetch all processed items with vectors
        # For huge datasets, we should do blocking or FAISS range search.
        # But here we assume < 100k items, simple approach ok or pure SQL?
        # SQL/Vectors usually separate.
        # Use FAISS range_search for finding neighbors radius < (1-sim).
        
        index = self.db_manager.clip_index
        ntotal = index.ntotal
        if ntotal < 2:
            return []
            
        # FAISS search strategy:
        # Range Search for each vector with radius corresponding to threshold.
        # sim = 0.95 -> dist_sq = 2*(1-0.95) = 0.1 (L2 normalized)
        # Inner Product is simpler: sim > 0.95
        # IndexFlatIP supports range_search but creates huge output if low threshold.
        # 0.95 is very high, so list should be small.
        
        try:
            print("Fetching vectors/IDs from FAISS...")
             # Reconstruct vectors (or use iterator if too large)
             # Reconstruct vectors (or use iterator if too large)
            # Use offset based reconstruction safe for IDMap
            sub_index = index.index if hasattr(index, 'index') else index
            
            vectors = []
            for i in range(ntotal):
                 vec = sub_index.reconstruct(i)
                 vectors.append(vec)
            vectors = np.array(vectors)
                 
            print(f"Vectors shape: {vectors.shape}")
            # IDs
            ids = faiss.vector_to_array(index.id_map)
            print(f"IDs shape: {ids.shape}")
            
            # Range Search
            # limit query? O(N^2) naive, FAISS optimizes a bit.
            # Lim, D, I = index.range_search(vectors, threshold_img) # range_search uses distance/sim depending on metric
            # IndexFlatIP range_search returns results > radius? 
            # Yes, for METRIC_INNER_PRODUCT it is sim > radius.
            
            # Using simple dot product for python control (N < 5000 is fast enough).
            # If N > 10000, use FAISS. Let's use FAISS.
            
            res_lims, res_D, res_I = index.range_search(vectors, threshold_img)
            
            # Resolve to pairs
            # res_lims is standard start-end ptrs
            
            # Fetch Metadata Cache
            conn = sqlite3.connect(self.db_manager.sqlite_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Need to map ID -> MediaItem
            # Query all files
            c.execute("SELECT * FROM files WHERE is_processed=1")
            file_map = {}
            for row in c.fetchall():
                 item = MediaItem(
                     file_path=row['file_path'],
                     file_hash=row['file_hash'],
                     file_size=row['file_size'],
                     media_type=row['media_type'],
                     created_at=row['created_at'],
                     modified_at=row['modified_at'],
                     width=row['width'],
                     height=row['height'],
                     duration=row['duration'],
                     error_msg=row['error_msg']
                 )
                 file_map[row['id']] = item
            conn.close()
            
            checked = set()
            
            for i in range(ntotal):
                query_id = ids[i]
                start = res_lims[i]
                end = res_lims[i+1]
                
                for j in range(start, end):
                    target_id = res_I[j]
                    sim = res_D[j]
                    
                    if query_id >= target_id: continue # Avoid self and duplicates (A-B, B-A)
                    if sim > 0.9999: continue # Probably exact same file (or self if diagonal not skipped)
                    
                    pair_key = tuple(sorted((query_id, target_id)))
                    if pair_key in checked: continue
                    checked.add(pair_key)
                    
                    item_a = file_map.get(int(query_id))
                    item_b = file_map.get(int(target_id))
                    
                    if not item_a or not item_b: continue
                    
                    if self._is_sequential(item_a.file_path, item_b.file_path):
                        continue

                    # Video specific check
                    if item_a.media_type == 'video' and item_b.media_type == 'video':
                        # Check duration similarity
                        dur_a = item_a.duration or 0
                        dur_b = item_b.duration or 0
                        
                        if abs(dur_a - dur_b) > 2.0: # Tolerance 2s
                             continue
                        
                        if sim < threshold_vid:
                             continue
                             
                    elif item_a.media_type != item_b.media_type:
                        # Skip cross-media
                        continue
                        
                    # --- NEW: dHash Check for Images ---
                    # CLIP is semantic, dHash is structural.
                    # If CLIP says duplicate but dHash diff is large -> False Positive (e.g. same character but different pose)
                    if item_a.media_type == 'image' and item_b.media_type == 'image':
                        # Only check if sim is borderline? No, check always to be safe.
                        from .hashing import compute_dhash, hamming_distance
                        
                        # We calculate on fly? Yes (disk I/O cost but cleaner is offline task)
                        # Ideally should cache hash in DB during scan.. but for now:
                        try:
                            # Use cache if we had it, but we don't.
                            # Just computing for candidates.
                            hash_a = compute_dhash(item_a.file_path)
                            hash_b = compute_dhash(item_b.file_path)
                            
                            dist = hamming_distance(hash_a, hash_b)
                            
                            # If dist > 10 (out of 64), likely different structure
                            # Let's use strict threshold 8 for "Duplicate"
                            if dist > 8:
                                continue # Skip, structural diff too large
                                
                        except Exception as e:
                            print(f"Hash calc failed: {e}")
                            pass
                        
                    # Determine Action
                    action, reason = self._recommend_action(item_a, item_b)
                    
                    pairs.append(DuplicatePair(
                        file_a=item_a,
                        file_b=item_b,
                        similarity=float(sim),
                        recommended_action=action,
                        reason=reason
                    ))
                    
        except Exception as e:
            print(f"Deduplication Error: {e}")
            import traceback
            traceback.print_exc()
            raise e
            
        print(f"Found {len(pairs)} duplicate pairs.")
        return pairs

    def _recommend_action(self, a: MediaItem, b: MediaItem) -> Tuple[str, str]:
        """
        Decide which file to keep.
        """
        # 1. Resolution (Area)
        area_a = (a.width or 0) * (a.height or 0)
        area_b = (b.width or 0) * (b.height or 0)
        
        if area_a > area_b * 1.05: # 5% margin
            return 'keep_a', f"Resolution A ({a.width}x{a.height}) > B ({b.width}x{b.height})"
        elif area_b > area_a * 1.05:
            return 'keep_b', f"Resolution B ({b.width}x{b.height}) > A ({a.width}x{a.height})"
            
        # 2. File Size (Quality/Bitrate proxy)
        if a.file_size > b.file_size * 1.05:
            return 'keep_a', f"File Size A ({a.file_size//1024}KB) > B ({b.file_size//1024}KB)"
        elif b.file_size > a.file_size * 1.05:
            return 'keep_b', f"File Size B ({b.file_size//1024}KB) > A ({a.file_size//1024}KB)"
            
        # 3. Timestamp (Prefer Newer? Or Older? Usually keep Original/Older)
        # Let's keep Newer (User preference varies, but let's decide logic)
        # Let's keep the one with OLDER creation time (Original)
        if a.created_at < b.created_at: 
             return 'keep_a', "A is older (likely original)"
        else:
             return 'keep_b', "B is older (likely original)"
             
        return 'review', "Indistinguishable"

    def _is_sequential(self, path_a: str, path_b: str) -> bool:
        """
        Check if two filenames are sequential (e.g. img_01.jpg and img_02.jpg).
        """
        name_a = os.path.splitext(os.path.basename(path_a))[0]
        name_b = os.path.splitext(os.path.basename(path_b))[0]
        
        if len(name_a) < 3 or len(name_b) < 3:
            return False
            
        # Find common prefix
        min_len = min(len(name_a), len(name_b))
        prefix_len = 0
        for i in range(min_len):
            if name_a[i] == name_b[i]:
                prefix_len += 1
            else:
                break
        
        if prefix_len < 3:
            return False
            
        # Characters after prefix
        rem_a = name_a[prefix_len:]
        rem_b = name_b[prefix_len:]
        
        # If both remainders are just numeric/short suffixes (like _p0, _p1 or 1, 2)
        import re
        # Pattern for numeric/sequential suffix
        pattern = re.compile(r'^[_ \-p\(r]*[0-9]+[\)]*$', re.IGNORECASE)
        
        if (not rem_a or pattern.match(rem_a)) and (not rem_b or pattern.match(rem_b)):
            return True
            
        return False

