import sqlite3
import pandas as pd
import numpy as np
import os
import pickle
import faiss
import json
import threading
import logging
from typing import List, Optional, Tuple, Dict, Any
from .schemas import MediaItem, VectorData, ProcessingResult

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, db_dir: str = "data/db"):
        self.db_dir = db_dir
        os.makedirs(db_dir, exist_ok=True)
        
        self.sqlite_path = os.path.join(db_dir, "metadata.db")
        self.faiss_path = os.path.join(db_dir, "vectors.index")
        self.face_faiss_path = os.path.join(db_dir, "faces.index")
        
        # Dimensions
        self.clip_dim = 768
        self.face_dim = 512
        self._faiss_lock = threading.Lock()
        
        self._init_sqlite()
        self._migrate_schema()
        self._init_faiss()

    def _connect(self):
        conn = sqlite3.connect(self.sqlite_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _migrate_schema(self):
        """Add missing columns to existing database if needed."""
        conn = self._connect()
        c = conn.cursor()
        
        # Check current columns
        c.execute("PRAGMA table_info(files)")
        columns = [row[1] for row in c.fetchall()]
        
        # Add character_tags if missing
        if 'character_tags' not in columns:
            print("Migrating DB: Adding character_tags column")
            c.execute("ALTER TABLE files ADD COLUMN character_tags TEXT")
            
        # Add series_tags if missing
        if 'series_tags' not in columns:
            print("Migrating DB: Adding series_tags column")
            c.execute("ALTER TABLE files ADD COLUMN series_tags TEXT")

        # Add audio_transcription if missing
        if 'audio_transcription' not in columns:
            print("Migrating DB: Adding audio_transcription column")
            c.execute("ALTER TABLE files ADD COLUMN audio_transcription TEXT")

        # Add frame_descriptions if missing
        if 'frame_descriptions' not in columns:
            print("Migrating DB: Adding frame_descriptions column")
            c.execute("ALTER TABLE files ADD COLUMN frame_descriptions TEXT")
            
        # Add caption if missing
        if 'caption' not in columns:
            print("Migrating DB: Adding caption column")
            c.execute("ALTER TABLE files ADD COLUMN caption TEXT")

        # Create albums table if missing
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='albums'")
        if not c.fetchone():
            print("Migrating DB: Creating albums table")
            c.execute('''
                CREATE TABLE albums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    is_dynamic BOOLEAN NOT NULL DEFAULT 0,
                    query_json TEXT, -- only used for dynamic albums
                    cover_file_id INTEGER, -- FK to files table
                    item_count INTEGER DEFAULT 0, -- Cache for static albums
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(cover_file_id) REFERENCES files(id)
                )
            ''')

        # Create album_media table if missing
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='album_media'")
        if not c.fetchone():
            print("Migrating DB: Creating album_media table")
            c.execute('''
                CREATE TABLE album_media (
                    album_id INTEGER NOT NULL,
                    file_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (album_id, file_id),
                    FOREIGN KEY(album_id) REFERENCES albums(id) ON DELETE CASCADE,
                    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            ''')

        # Search History Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                filters_json TEXT,
                result_count INTEGER NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_search_history_query ON search_history(query_text, filters_json)")

        # Add item_count to albums if missing (in case table was created earlier without it)
        c.execute("PRAGMA table_info(albums)")
        albums_cols = [row[1] for row in c.fetchall()]
        if 'item_count' not in albums_cols:
            print("Migrating DB: Adding item_count to albums")
            c.execute("ALTER TABLE albums ADD COLUMN item_count INTEGER DEFAULT 0")

        # Migrate faces table for bbox and person_name
        c.execute("PRAGMA table_info(faces)")
        faces_columns = [row[1] for row in c.fetchall()]
        
        if 'bbox' not in faces_columns:
            print("Migrating DB: Adding bbox column to faces")
            c.execute("ALTER TABLE faces ADD COLUMN bbox TEXT")
            
        if 'person_name' not in faces_columns:
            print("Migrating DB: Adding person_name column to faces")
            c.execute("ALTER TABLE faces ADD COLUMN person_name TEXT")

        # Create search_history table if missing
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='search_history'")
        if not c.fetchone():
            print("Migrating DB: Creating search_history table")
            c.execute('''
                CREATE TABLE search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_text TEXT NOT NULL,
                    filters_json TEXT,
                    result_count INTEGER NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_search_history_query ON search_history(query_text, filters_json)")

        conn.commit()
        conn.close()

    def _init_sqlite(self):
        """Initialize SQLite tables."""
        conn = self._connect()
        c = conn.cursor()
        
        # Files Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                file_hash TEXT,
                file_size INTEGER,
                media_type TEXT,
                created_at REAL,
                modified_at REAL,
                width INTEGER,
                height INTEGER,
                duration REAL,
                is_processed BOOLEAN DEFAULT 0,
                error_msg TEXT,
                tags TEXT, -- JSON List
                character_tags TEXT, -- JSON List
                series_tags TEXT, -- JSON List
                rating INTEGER DEFAULT 0,
                audio_transcription TEXT, -- JSON List
                frame_descriptions TEXT, -- JSON List
                caption TEXT -- Text
            )
        ''')
        
        # Faces Table (Metadata for faces)
        c.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                face_index INTEGER, -- Index in the file's face list
                cluster_id INTEGER DEFAULT -1,
                timestamp REAL,
                bbox TEXT, -- JSON List
                person_name TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id)
            )
        ''')

        # Scan Jobs Table (Persistent scan state for resume)
        c.execute('''
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, paused, completed, failed
                total_files INTEGER DEFAULT 0,
                processed_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                force_reprocess BOOLEAN DEFAULT 0,
                current_file TEXT,
                started_at REAL,
                updated_at REAL,
                completed_at REAL,
                last_processed_path TEXT  -- For resume: last file successfully processed
            )
        ''')

        # Scan Errors Table (Per-file error log)
        c.execute('''
            CREATE TABLE IF NOT EXISTS scan_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                error_message TEXT,
                traceback TEXT,
                occurred_at REAL,
                FOREIGN KEY(job_id) REFERENCES scan_jobs(id)
            )
        ''')

        # App Settings Table (Key-Value pair)
        c.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at REAL
            )
        ''')

        # Albums Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_dynamic BOOLEAN NOT NULL DEFAULT 0,
                query_json TEXT,
                cover_file_id INTEGER,
                item_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(cover_file_id) REFERENCES files(id)
            )
        ''')

        # Album Media Table (Static)
        c.execute('''
            CREATE TABLE IF NOT EXISTS album_media (
                album_id INTEGER NOT NULL,
                file_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (album_id, file_id),
                FOREIGN KEY(album_id) REFERENCES albums(id) ON DELETE CASCADE,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        
        # Check for existing users to auto-complete setup
        c.execute('SELECT COUNT(*) FROM files')
        if c.fetchone()[0] > 0:
            c.execute('SELECT value FROM app_settings WHERE key = "setup_completed"')
            if not c.fetchone():
                import time
                c.execute('INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)', 
                         ("setup_completed", "1", time.time()))
                conn.commit()
                
        conn.close()

    def _init_faiss(self):
        """Initialize FAISS indices."""
        # 1. CLIP Index (Inner Product for Cosine Similarity - vectors must be normalized)
        if os.path.exists(self.faiss_path):
            self.clip_index = faiss.read_index(self.faiss_path)
        else:
            self.clip_index = faiss.IndexFlatIP(self.clip_dim)
            # Use IDMap2 to map vector IDs to File IDs, supporting reconstruct()
            self.clip_index = faiss.IndexIDMap2(self.clip_index)

        # 2. Face Index
        if os.path.exists(self.face_faiss_path):
            self.face_index = faiss.read_index(self.face_faiss_path)
        else:
            self.face_index = faiss.IndexFlatIP(self.face_dim)
            self.face_index = faiss.IndexIDMap2(self.face_index)

    def save_indices(self):
        """Persist FAISS indices to disk."""
        with self._faiss_lock:
            faiss.write_index(self.clip_index, self.faiss_path)
            faiss.write_index(self.face_index, self.face_faiss_path)

    def is_file_processed(self, file_path: str, file_hash: str) -> bool:
        """Check if file exists and hash matches."""
        conn = self._connect()
        c = conn.cursor()
        c.execute('SELECT file_hash, is_processed FROM files WHERE file_path = ?', (file_path,))
        row = c.fetchone()
        conn.close()
        
        if row:
            stored_hash, is_processed = row
            if stored_hash == file_hash and is_processed:
                return True
        return False

    def add_result(self, result: ProcessingResult):
        """Add processing result to DB and Indices."""
        item = result.media_item
        vec_data = result.vector_data
        
        conn = self._connect()
        c = conn.cursor()
        
        try:
            # Upsert File Info
            # SQLite upsert syntax (ON CONFLICT)
            c.execute('''
                INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags, character_tags, series_tags, audio_transcription, frame_descriptions, caption)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    is_processed=excluded.is_processed,
                    error_msg=excluded.error_msg,
                    modified_at=excluded.modified_at,
                    tags=excluded.tags,
                    character_tags=excluded.character_tags,
                    series_tags=excluded.series_tags,
                    audio_transcription=excluded.audio_transcription,
                    frame_descriptions=excluded.frame_descriptions,
                    caption=excluded.caption
            ''', (
                item.file_path, item.file_hash, item.file_size, item.media_type, 
                item.created_at, item.modified_at, item.width, item.height, item.duration,
                1 if result.success else 0, item.error_msg, 
                json.dumps(item.tags), json.dumps(item.character_tags), json.dumps(item.series_tags),
                json.dumps(item.audio_transcription) if item.audio_transcription is not None else None,
                json.dumps(item.frame_descriptions) if item.frame_descriptions is not None else None,
                item.caption
            ))
            
            file_id = c.lastrowid
            if not file_id:
                 # In case of update, lastrowid might be 0, need to fetch
                 c.execute('SELECT id FROM files WHERE file_path = ?', (item.file_path,))
                 file_id = c.fetchone()[0]
                 
                 # Remove old embeddings from faiss explicitly before re-adding
                 try:
                     with self._faiss_lock:
                         self.clip_index.remove_ids(np.array([file_id], dtype='int64'))
                 except Exception as e:
                     logger.error(f"FAISS operation failed during clip index removal: {e}")
                     
                 # Remove old face mappings
                 c.execute('SELECT id FROM faces WHERE file_id = ?', (file_id,))
                 old_face_ids = [row[0] for row in c.fetchall()]
                 if old_face_ids:
                     try:
                         with self._faiss_lock:
                             self.face_index.remove_ids(np.array(old_face_ids, dtype='int64'))
                     except Exception as e:
                         logger.error(f"FAISS operation failed during face index removal: {e}")
                     c.execute('DELETE FROM faces WHERE file_id = ?', (file_id,))

            if result.success and vec_data:
                # 1. Add CLIP Vector
                clip_vec = np.array([vec_data.clip_vector], dtype='float32') # (1, 768)
                faiss.normalize_L2(clip_vec) # Ensure normalized
                with self._faiss_lock:
                    self.clip_index.add_with_ids(clip_vec, np.array([file_id], dtype='int64'))
                
                # 2. Add Face Vectors
                if vec_data.face_vectors:
                    face_vecs = np.array(vec_data.face_vectors, dtype='float32')
                    faiss.normalize_L2(face_vecs)
                    
                    # We need unique IDs for faces. 
                    # Strategy: Use a large offset or separate logic. 
                    # Simple approach: Store metadata in SQLite 'faces' table, use its ID.
                    
                    for i, face_vec in enumerate(face_vecs):
                        timestamp = result.faces[i].timestamp if i < len(result.faces) else 0.0
                        bbox_json = json.dumps(result.faces[i].bbox) if i < len(result.faces) else "[]"
                        
                        c.execute('INSERT INTO faces (file_id, face_index, timestamp, bbox) VALUES (?, ?, ?, ?)', (file_id, i, timestamp, bbox_json))
                        face_db_id = c.lastrowid
                        
                        # Add to FAISS
                        with self._faiss_lock:
                            self.face_index.add_with_ids(np.array([face_vec]), np.array([face_db_id], dtype='int64'))

            conn.commit()
            
        except Exception as e:
            print(f"DB Error: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()

            # For performance, might not want to save index every single file, but for safety we do or batch it.
            # Here we save to be safe.
            self.save_indices()

    def search_similar_images(self, query_vector: np.ndarray, top_k: int = 20) -> List[Tuple[str, float]]:
        """Search similar images using CLIP vector."""
        if self.clip_index.ntotal == 0:
            return []
            
        params = np.array([query_vector], dtype='float32')
        faiss.normalize_L2(params)
        
        D, I = self.clip_index.search(params, top_k)
        
        # I[0] contains IDs (file_ids)
        file_ids = [int(idx) for idx in I[0] if idx != -1]
        scores = [float(s) for s, idx in zip(D[0], I[0]) if idx != -1]
        
        if not file_ids:
            return []
            
        # Resolve File Paths
        conn = self._connect()
        c = conn.cursor()
        
        placeholders = ','.join(['?'] * len(file_ids))
        # Preserving order is tricky in SQL IN clause.
        # Format: (id, path)
        c.execute(f'SELECT id, file_path FROM files WHERE id IN ({placeholders})', file_ids)
        rows = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        
        results = []
        for fid, score in zip(file_ids, scores):
            if fid in rows:
                results.append((rows[fid], score))
                
        return results

    def add_results_batch(self, results: List[ProcessingResult]):
        """
        Batch insert for performance.
        Much faster than single insert loop.
        """
        if not results:
            return

        conn = self._connect()
        c = conn.cursor()
        
        try:
            # 1. Upsert files in batch
            # Prepare data
            # Format: (path, hash, size, type, created, modified, width, height, duration, is_processed, error_msg)
            files_data = []
            for r in results:
                item = r.media_item
                files_data.append((
                   item.file_path, item.file_hash, item.file_size, item.media_type,
                   item.created_at, item.modified_at, item.width, item.height, item.duration,
                   1 if r.success else 0, item.error_msg, 
                   json.dumps(item.tags), json.dumps(item.character_tags), json.dumps(item.series_tags),
                   json.dumps(item.audio_transcription) if item.audio_transcription is not None else None,
                   json.dumps(item.frame_descriptions) if item.frame_descriptions is not None else None,
                   item.caption
                ))
            
            c.executemany('''
                INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags, character_tags, series_tags, audio_transcription, frame_descriptions, caption)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    is_processed=excluded.is_processed,
                    error_msg=excluded.error_msg,
                    modified_at=excluded.modified_at,
                    tags=excluded.tags,
                    character_tags=excluded.character_tags,
                    series_tags=excluded.series_tags,
                    audio_transcription=excluded.audio_transcription,
                    frame_descriptions=excluded.frame_descriptions,
                    caption=excluded.caption
            ''', files_data)
            
            # Need to get IDs Back. 
            # In SQLite, executemany doesn't return list of IDs.
            # We must query them back efficiently.
            
            paths = [r.media_item.file_path for r in results]
            placeholders = ','.join(['?'] * len(paths))
            c.execute(f"SELECT file_path, id FROM files WHERE file_path IN ({placeholders})", paths)
            path_to_id = {row[0]: row[1] for row in c.fetchall()}
            
            # 2. Prepare Vectors
            clip_vectors_list = []
            clip_ids_list = []
            
            face_vectors_list = []
            face_metadata_list = [] # (file_id, face_index, timestamp)
            
            for r in results:
                if not r.success or not r.vector_data:
                    continue
                    
                fid = path_to_id.get(r.media_item.file_path)
                if fid is None:
                    continue
                    
                # Clean up old vectors/faces to prevent duplicates on upsert
                try:
                    with self._faiss_lock:
                        self.clip_index.remove_ids(np.array([fid], dtype='int64'))
                except Exception as e:
                    logger.error(f"FAISS operation failed during clip index batch removal: {e}")
                c.execute('SELECT id FROM faces WHERE file_id = ?', (fid,))
                old_face_ids = [row[0] for row in c.fetchall()]
                if old_face_ids:
                    try:
                        with self._faiss_lock:
                            self.face_index.remove_ids(np.array(old_face_ids, dtype='int64'))
                    except Exception as e:
                        logger.error(f"FAISS operation failed during face index batch removal: {e}")
                    c.execute('DELETE FROM faces WHERE file_id = ?', (fid,))
                    
                # CLIP Result
                clip_vectors_list.append(r.vector_data.clip_vector)
                clip_ids_list.append(fid)
                
                # Face Results
                if r.vector_data.face_vectors:
                     for i, fvec in enumerate(r.vector_data.face_vectors):
                         timestamp = r.faces[i].timestamp if i < len(r.faces) else 0.0
                         bbox = json.dumps(r.faces[i].bbox) if i < len(r.faces) else "[]"
                         face_vectors_list.append(fvec)
                         face_metadata_list.append((fid, i, timestamp, bbox))

            # --- Commit to FAISS & DB (Faces) ---
            
            # A. CLIP FAISS
            if clip_vectors_list:
                 # Add to FAISS
                 vecs = np.array(clip_vectors_list, dtype='float32')
                 ids = np.array(clip_ids_list, dtype='int64')
                 faiss.normalize_L2(vecs)
                 with self._faiss_lock:
                     self.clip_index.add_with_ids(vecs, ids)
            
            # B. Face Metadata (SQLite) (One by one loop for safety to get IDs) & Face FAISS
            if face_vectors_list:
                f_vecs_to_add = []
                f_ids_to_add = []
                
                for i, (fid, fidx, ts, bbox) in enumerate(face_metadata_list):
                    c.execute('INSERT INTO faces (file_id, face_index, timestamp, bbox) VALUES (?, ?, ?, ?)', (fid, fidx, ts, bbox))
                    face_row_id = c.lastrowid
                    f_vecs_to_add.append(face_vectors_list[i])
                    f_ids_to_add.append(face_row_id)
                
                if f_vecs_to_add:
                    f_vecs = np.array(f_vecs_to_add, dtype='float32')
                    f_ids = np.array(f_ids_to_add, dtype='int64')
                    faiss.normalize_L2(f_vecs)
                    with self._faiss_lock:
                        self.face_index.add_with_ids(f_vecs, f_ids)

            conn.commit()
            self.save_indices()
            
        except Exception as e:
            print(f"Batch Insert Error: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()

    def search_similar_faces(self, query_face_vector: np.ndarray, top_k: int = 20) -> List[Tuple[int, float]]:
        """Search similar faces using face vector from FAISS."""
        if self.face_index.ntotal == 0:
            return []
            
        params = np.array([query_face_vector], dtype='float32')
        faiss.normalize_L2(params)
        
        D, I = self.face_index.search(params, top_k)
        
        face_ids = [int(idx) for idx in I[0] if idx != -1]
        scores = [float(s) for s, idx in zip(D[0], I[0]) if idx != -1]
        
        if not face_ids:
            return []
            
        results = []
        for fid, score in zip(face_ids, scores):
            results.append((fid, score))
            
        return results

    def get_face_vector(self, face_id: int) -> Optional[np.ndarray]:
        """Retrieve a specific face vector from FAISS via ID."""
        try:
            return self.face_index.reconstruct(face_id)
        except Exception as e:
            print(f"Failed to reconstruct face vector {face_id}: {e}. Ensure IndexIDMap2 is used.")
            return None

    def get_faces_for_file(self, file_id: int) -> List[Dict]:
        """Get all face metadata for a specific file."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            c.execute('SELECT id, file_id, face_index, timestamp, bbox, person_name FROM faces WHERE file_id = ? ORDER BY face_index ASC', (file_id,))
            rows = c.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_face_details(self, face_ids: List[int]) -> List[Dict]:
        """Fetch file and face details for a list of face IDs."""
        if not face_ids:
            return []
            
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            placeholders = ','.join(['?'] * len(face_ids))
            c.execute(f'''
                SELECT f.id as face_id, f.file_id, f.bbox, f.person_name, f.timestamp, 
                       fi.file_path, fi.media_type, fi.width, fi.height
                FROM faces f
                JOIN files fi ON f.file_id = fi.id
                WHERE f.id IN ({placeholders})
            ''', face_ids)
            
            rows = c.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_files_by_ids(self, file_ids: List[int]) -> List[Dict]:
        """Fetch files by their IDs."""
        if not file_ids:
            return []
            
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            placeholders = ','.join(['?'] * len(file_ids))
            c.execute(f'''
                SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, caption
                FROM files
                WHERE id IN ({placeholders})
            ''', file_ids)
            
            rows = c.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_face_person(self, face_id: int, person_name: str) -> bool:
        """Update the person name for a given face."""
        conn = self._connect()
        c = conn.cursor()
        
        try:
            c.execute('UPDATE faces SET person_name = ? WHERE id = ?', (person_name, face_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating face person {face_id}: {e}")
            return False
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # App Settings Methods
    # ------------------------------------------------------------------ #

    def merge_metadata(self, source_path: str, target_path: str) -> bool:
        """
        Merge tags, character_tags, series_tags, and captions from source to target.
        """
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            # Fetch source
            c.execute('SELECT tags, character_tags, series_tags, caption FROM files WHERE file_path = ?', (source_path,))
            src = c.fetchone()
            if not src:
                return False
                
            # Fetch target
            c.execute('SELECT tags, character_tags, series_tags, caption FROM files WHERE file_path = ?', (target_path,))
            tgt = c.fetchone()
            if not tgt:
                return False
                
            def safe_parse(val):
                if not val: return []
                try: return json.loads(val)
                except: return []
                
            # Merge JSON arrays
            new_tags = list(set(safe_parse(src['tags']) + safe_parse(tgt['tags'])))
            new_chars = list(set(safe_parse(src['character_tags']) + safe_parse(tgt['character_tags'])))
            new_series = list(set(safe_parse(src['series_tags']) + safe_parse(tgt['series_tags'])))
            
            # Merge captions
            new_caption = tgt['caption']
            if src['caption']:
                if new_caption:
                    if src['caption'] not in new_caption:
                        new_caption += "\n" + src['caption']
                else:
                    new_caption = src['caption']
                    
            c.execute('''
                UPDATE files SET
                    tags = ?,
                    character_tags = ?,
                    series_tags = ?,
                    caption = ?
                WHERE file_path = ?
            ''', (json.dumps(new_tags), json.dumps(new_chars), json.dumps(new_series), new_caption, target_path))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Merge error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a setting value by key."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute('SELECT value FROM app_settings WHERE key = ?', (key,))
            row = c.fetchone()
            return row[0] if row else default
        finally:
            conn.close()

    def set_setting(self, key: str, value: str):
        """Save or update a setting value."""
        import time
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
            ''', (key, value, time.time()))
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # Hybrid Search Methods
    # ------------------------------------------------------------------ #

    def hybrid_search(self, query_vector: np.ndarray, filters: Dict, top_k: int = 50) -> Dict:
        """
        Hybrid search using FAISS retrieval followed by SQLite filtering.
        """
        if self.clip_index.ntotal == 0:
            return {"results": [], "total_candidates": 0, "filters_applied": filters}

        # FAISS Score Threshold (Cosine Similarity >= 0.15)
        MIN_SCORE = 0.15

        def get_faiss_results(k):
            params = np.array([query_vector], dtype='float32')
            faiss.normalize_L2(params)
            D, I = self.clip_index.search(params, k)
            ids = [int(idx) for idx in I[0] if idx != -1]
            scores = [float(s) for s, idx in zip(D[0], I[0]) if idx != -1]
            # Apply threshold
            valid = [(idx, s) for idx, s in zip(ids, scores) if s >= MIN_SCORE]
            return valid

        # Round 1: top_k * 3
        candidates = get_faiss_results(top_k * 3)
        total_candidates = len(candidates)
        
        filtered_results = self._apply_sqlite_filters(candidates, filters, top_k)
        
        # Round 2: top_k * 10 (only if Round 1 insufficient and more exists)
        if len(filtered_results) < top_k and total_candidates < self.clip_index.ntotal:
            candidates_r2 = get_faiss_results(top_k * 10)
            if len(candidates_r2) > total_candidates:
                total_candidates = len(candidates_r2)
                filtered_results = self._apply_sqlite_filters(candidates_r2, filters, top_k)

        return {
            "results": filtered_results,
            "total_candidates": total_candidates,
            "filters_applied": filters
        }

    def _apply_sqlite_filters(self, candidates: List[Tuple[int, float]], filters: Dict, top_k: int) -> List[Dict]:
        if not candidates:
            return []
            
        file_id_to_score = {idx: score for idx, score in candidates}
        file_ids = [idx for idx, _ in candidates]
        
        # Build SQL filters
        where_clauses = []
        sql_params = []
        
        if filters.get('media_type'):
            where_clauses.append("media_type = ?")
            sql_params.append(filters['media_type'])
            
        if filters.get('extension') and isinstance(filters['extension'], list):
            ext_clauses = ["file_path LIKE ?" for _ in filters['extension']]
            where_clauses.append(f"({' OR '.join(ext_clauses)})")
            for ext in filters['extension']:
                sql_params.append(f"%{ext}")

        for field in ['tags', 'character_tags', 'series_tags']:
            if filters.get(field) and isinstance(filters[field], list):
                for val in filters[field]:
                    where_clauses.append(f"{field} LIKE ?")
                    # SQLite JSON match workaround
                    sql_params.append(f'%"{val}"%')

        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        final_rows = []
        # Chunk file_ids by 500 to avoid SQL variable limits
        for i in range(0, len(file_ids), 500):
            chunk = file_ids[i:i+500]
            placeholders = ','.join(['?'] * len(chunk))
            
            query = f"SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, caption FROM files WHERE id IN ({placeholders})"
            if where_clauses:
                query += " AND " + " AND ".join(where_clauses)
            
            c.execute(query, chunk + sql_params)
            final_rows.extend([dict(r) for r in c.fetchall()])
            
        conn.close()
        
        # Merge scores and sort
        for row in final_rows:
            row['score'] = file_id_to_score.get(row['id'], 0.0)
            
        final_rows.sort(key=lambda x: x['score'], reverse=True)
        return final_rows[:top_k]

    # ------------------------------------------------------------------ #
    # Album Methods
    # ------------------------------------------------------------------ #

    def create_album(self, name: str, is_dynamic: bool, query_json: Optional[str] = None) -> int:
        """Create a new album."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute(
                'INSERT INTO albums (name, is_dynamic, query_json) VALUES (?, ?, ?)',
                (name, 1 if is_dynamic else 0, query_json)
            )
            album_id = c.lastrowid
            conn.commit()
            return album_id
        finally:
            conn.close()

    def delete_album(self, album_id: int) -> bool:
        """Delete an album."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute('DELETE FROM albums WHERE id = ?', (album_id,))
            conn.commit()
            return c.rowcount > 0
        finally:
            conn.close()

    def update_album(self, album_id: int, name: Optional[str] = None, query_json: Optional[str] = None, cover_file_id: Optional[int] = None):
        """Update album metadata."""
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if query_json is not None:
            updates.append("query_json = ?")
            params.append(query_json)
        if cover_file_id is not None:
            updates.append("cover_file_id = ?")
            params.append(cover_file_id)
        
        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(album_id)

        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute(f"UPDATE albums SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        finally:
            conn.close()

    def get_albums(self) -> List[Dict]:
        """List all albums."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM albums ORDER BY created_at DESC')
            return [dict(r) for r in c.fetchall()]
        finally:
            conn.close()

    def get_album(self, album_id: int) -> Optional[Dict]:
        """Get a single album by id."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute('SELECT * FROM albums WHERE id = ?', (album_id,))
            row = c.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def add_to_album(self, album_id: int, file_ids: List[int]):
        """Add files to a static album."""
        conn = self._connect()
        c = conn.cursor()
        try:
            # Verify it's a static album
            c.execute('SELECT is_dynamic FROM albums WHERE id = ?', (album_id,))
            row = c.fetchone()
            if not row or row[0]: # Not found or is dynamic
                return

            # Insert items
            for fid in file_ids:
                c.execute('INSERT OR IGNORE INTO album_media (album_id, file_id) VALUES (?, ?)', (album_id, fid))
            
            # Update item_count
            c.execute('SELECT COUNT(*) FROM album_media WHERE album_id = ?', (album_id,))
            count = c.fetchone()[0]
            c.execute('UPDATE albums SET item_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (count, album_id))
            
            conn.commit()
        finally:
            conn.close()

    def remove_from_album(self, album_id: int, file_ids: List[int]):
        """Remove files from a static album."""
        conn = self._connect()
        c = conn.cursor()
        try:
            placeholders = ','.join(['?'] * len(file_ids))
            c.execute(f'DELETE FROM album_media WHERE album_id = ? AND file_id IN ({placeholders})', [album_id] + file_ids)
            
            # Update item_count
            c.execute('SELECT COUNT(*) FROM album_media WHERE album_id = ?', (album_id,))
            count = c.fetchone()[0]
            c.execute('UPDATE albums SET item_count = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (count, album_id))
            
            conn.commit()
        finally:
            conn.close()

    def get_album_media(self, album_id: int, ai_engine: Optional[Any] = None) -> List[Dict]:
        """Get media items for an album (static or dynamic)."""
        album = self.get_album(album_id)
        if not album:
            return []

        if not album['is_dynamic']:
            # Static album
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            try:
                c.execute('''
                    SELECT f.id, f.file_path, f.media_type, f.width, f.height, f.tags, f.character_tags, f.series_tags, f.caption
                    FROM files f
                    JOIN album_media am ON f.id = am.file_id
                    WHERE am.album_id = ?
                    ORDER BY am.added_at DESC
                ''', (album_id,))
                return [dict(r) for r in c.fetchall()]
            finally:
                conn.close()
        else:
            # Dynamic album
            if not album['query_json'] or not ai_engine:
                return []
            
            try:
                query_data = json.loads(album['query_json'])
                query_text = query_data.get('query')
                filters = query_data.get('filters', {})
                top_k = query_data.get('top_k', 100)
                
                if not query_text:
                    # Optional: handle filter-only dynamic albums? 
                    # For now, require query as per spec.
                    return []
                
                text_vec = ai_engine.extract_clip_text_feature(query_text)
                search_results = self.hybrid_search(text_vec, filters, top_k=top_k)
                return search_results['results']
            except Exception as e:
                logger.error(f"Error executing dynamic album query: {e}")
                return []

    # ------------------------------------------------------------------ #
    # Search History Methods
    # ------------------------------------------------------------------ #

    def save_search_history(self, query_text: str, filters_json: Optional[str], result_count: int):
        """Save search to history with UPSERT logic and size limit."""
        conn = self._connect()
        c = conn.cursor()
        # Use empty JSON string instead of NULL to ensure unique index / UPSERT works
        safe_filters = filters_json if filters_json else "{}"
        try:
            # UPSERT: if same query_text + filters_json exists, update executed_at and result_count.
            c.execute('''
                INSERT INTO search_history (query_text, filters_json, result_count, executed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(query_text, filters_json) DO UPDATE SET
                    result_count=excluded.result_count,
                    executed_at=CURRENT_TIMESTAMP
            ''', (query_text, safe_filters, result_count))
            
            # Enforce limit of 100 rows, use id as tie-breaker for oldest
            c.execute("DELETE FROM search_history WHERE id NOT IN (SELECT id FROM search_history ORDER BY executed_at DESC, id DESC LIMIT 100)")
            
            conn.commit()
        finally:
            conn.close()

    def get_search_history(self, limit: int = 20) -> List[Dict]:
        """Return recent history entries."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute('SELECT id, query_text, filters_json, result_count, executed_at FROM search_history ORDER BY executed_at DESC LIMIT ?', (limit,))
            rows = c.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_search_history(self, history_id: int):
        """Delete a single search history entry."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute('DELETE FROM search_history WHERE id = ?', (history_id,))
            conn.commit()
        finally:
            conn.close()

    def clear_search_history(self):
        """Clear all search history."""
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute('DELETE FROM search_history')
            conn.commit()
        finally:
            conn.close()
