
import sqlite3
import pandas as pd
import numpy as np
import os
import pickle
import faiss
import json
from typing import List, Optional, Tuple, Dict
from .schemas import MediaItem, VectorData, ProcessingResult

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
        
        self._init_sqlite()
        self._migrate_schema()
        self._init_faiss()

    def _migrate_schema(self):
        """Add missing columns to existing database if needed."""
        conn = sqlite3.connect(self.sqlite_path)
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
            
        conn.commit()
        conn.close()

    def _init_sqlite(self):
        """Initialize SQLite tables."""
        conn = sqlite3.connect(self.sqlite_path)
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
                rating INTEGER DEFAULT 0
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
                FOREIGN KEY(file_id) REFERENCES files(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def _init_faiss(self):
        """Initialize FAISS indices."""
        # 1. CLIP Index (Inner Product for Cosine Similarity - vectors must be normalized)
        if os.path.exists(self.faiss_path):
            self.clip_index = faiss.read_index(self.faiss_path)
        else:
            self.clip_index = faiss.IndexFlatIP(self.clip_dim)
            # Use IDMap to map vector IDs to File IDs
            self.clip_index = faiss.IndexIDMap(self.clip_index)

        # 2. Face Index
        if os.path.exists(self.face_faiss_path):
            self.face_index = faiss.read_index(self.face_faiss_path)
        else:
            self.face_index = faiss.IndexFlatIP(self.face_dim)
            self.face_index = faiss.IndexIDMap(self.face_index)

    def save_indices(self):
        """Persist FAISS indices to disk."""
        faiss.write_index(self.clip_index, self.faiss_path)
        faiss.write_index(self.face_index, self.face_faiss_path)

    def is_file_processed(self, file_path: str, file_hash: str) -> bool:
        """Check if file exists and hash matches."""
        conn = sqlite3.connect(self.sqlite_path)
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
        
        conn = sqlite3.connect(self.sqlite_path)
        c = conn.cursor()
        
        try:
            # Upsert File Info
            # SQLite upsert syntax (ON CONFLICT)
            c.execute('''
                INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags, character_tags, series_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    is_processed=excluded.is_processed,
                    error_msg=excluded.error_msg,
                    modified_at=excluded.modified_at,
                    tags=excluded.tags,
                    character_tags=excluded.character_tags,
                    series_tags=excluded.series_tags
            ''', (
                item.file_path, item.file_hash, item.file_size, item.media_type, 
                item.created_at, item.modified_at, item.width, item.height, item.duration,
                1 if result.success else 0, item.error_msg, 
                json.dumps(item.tags), json.dumps(item.character_tags), json.dumps(item.series_tags)
            ))
            
            file_id = c.lastrowid
            if not file_id:
                 # In case of update, lastrowid might be 0, need to fetch
                 c.execute('SELECT id FROM files WHERE file_path = ?', (item.file_path,))
                 file_id = c.fetchone()[0]

            if result.success and vec_data:
                # 1. Add CLIP Vector
                clip_vec = np.array([vec_data.clip_vector], dtype='float32') # (1, 768)
                faiss.normalize_L2(clip_vec) # Ensure normalized
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
                        
                        c.execute('INSERT INTO faces (file_id, face_index, timestamp) VALUES (?, ?, ?)', (file_id, i, timestamp))
                        face_db_id = c.lastrowid
                        
                        # Add to FAISS
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
        conn = sqlite3.connect(self.sqlite_path)
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

        conn = sqlite3.connect(self.sqlite_path)
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
                   json.dumps(item.tags), json.dumps(item.character_tags), json.dumps(item.series_tags)
                ))
            
            c.executemany('''
                INSERT INTO files (file_path, file_hash, file_size, media_type, created_at, modified_at, width, height, duration, is_processed, error_msg, tags, character_tags, series_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    file_hash=excluded.file_hash,
                    is_processed=excluded.is_processed,
                    error_msg=excluded.error_msg,
                    modified_at=excluded.modified_at,
                    tags=excluded.tags,
                    character_tags=excluded.character_tags,
                    series_tags=excluded.series_tags
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
                    
                # CLIP Result
                clip_vectors_list.append(r.vector_data.clip_vector)
                clip_ids_list.append(fid)
                
                # Face Results
                if r.vector_data.face_vectors:
                     for i, fvec in enumerate(r.vector_data.face_vectors):
                         timestamp = r.faces[i].timestamp if i < len(r.faces) else 0.0
                         face_vectors_list.append(fvec)
                         face_metadata_list.append((fid, i, timestamp))

            # --- Commit to FAISS & DB (Faces) ---
            
            # A. CLIP FAISS
            if clip_vectors_list:
                # Add to FAISS
                vecs = np.array(clip_vectors_list, dtype='float32')
                ids = np.array(clip_ids_list, dtype='int64')
                faiss.normalize_L2(vecs)
                self.clip_index.add_with_ids(vecs, ids)
            
            # B. Face Metadata (SQLite) (One by one loop for safety to get IDs) & Face FAISS
            if face_vectors_list:
                f_vecs_to_add = []
                f_ids_to_add = []
                
                for i, (fid, fidx, ts) in enumerate(face_metadata_list):
                    c.execute('INSERT INTO faces (file_id, face_index, timestamp) VALUES (?, ?, ?)', (fid, fidx, ts))
                    face_row_id = c.lastrowid
                    f_vecs_to_add.append(face_vectors_list[i])
                    f_ids_to_add.append(face_row_id)
                
                if f_vecs_to_add:
                    f_vecs = np.array(f_vecs_to_add, dtype='float32')
                    f_ids = np.array(f_ids_to_add, dtype='int64')
                    faiss.normalize_L2(f_vecs)
                    self.face_index.add_with_ids(f_vecs, f_ids)

            conn.commit()
            self.save_indices()
            
        except Exception as e:
            print(f"Batch Insert Error: {e}")
            conn.rollback()
            raise e
        finally:
            conn.close()
