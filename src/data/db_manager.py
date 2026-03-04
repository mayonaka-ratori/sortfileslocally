import sqlite3
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
        self.verify_index_integrity()

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

        # Add favorite if missing
        if 'favorite' not in columns:
            print("Migrating DB: Adding favorite column")
            c.execute("ALTER TABLE files ADD COLUMN favorite BOOLEAN DEFAULT 0")

        # Add folder_path if missing
        if 'folder_path' not in columns:
            print("Migrating DB: Adding folder_path column")
            c.execute("ALTER TABLE files ADD COLUMN folder_path TEXT")
            # Populate folder_path for existing files
            c.execute("UPDATE files SET folder_path = ?", (None,)) # Temporary null
            # Actually, let's try to populate it if possible, but safely.
            # We can't easily do it with pure SQL for directory names in SQLite without extensions, 
            # so we'll leave it to be populated on next scan or just leave it for now.

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

        # Video Scenes Table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='video_scenes'")
        if not c.fetchone():
            print("Migrating DB: Creating video_scenes table")
            c.execute('''
                CREATE TABLE video_scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL NOT NULL,
                    caption TEXT,
                    tags TEXT, -- JSON List
                    character_tags TEXT, -- JSON List
                    series_tags TEXT, -- JSON List
                    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
                )
            ''')
        
        # Add missing columns to video_scenes (for 4.7 upgrade)
        for col, definition in [
            ("scene_index", "INTEGER DEFAULT 0"),
            ("thumbnail_path", "TEXT"),
            ("clip_vector_id", "INTEGER"),
            ("start_frame", "INTEGER DEFAULT 0"),
            ("end_frame", "INTEGER DEFAULT 0"),
        ]:
            try:
                c.execute(f"ALTER TABLE video_scenes ADD COLUMN {col} {definition}")
            except Exception as e:
                logger.debug(f"Column migration for video_scenes skipped or failed: {e}")
                pass # Column already exists
        
        try:
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_scene_file_index ON video_scenes(file_id, scene_index)")
        except Exception as e:
            logger.debug(f"Index migration for video_scenes skipped or failed: {e}")
            pass
        
        # Vector Mapping Table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vector_mapping'")
        if not c.fetchone():
            print("Migrating DB: Creating vector_mapping table")
            c.execute('''
                CREATE TABLE vector_mapping (
                    faiss_id INTEGER PRIMARY KEY,
                    entity_type TEXT NOT NULL, -- 'file' or 'scene'
                    entity_id INTEGER NOT NULL
                )
            ''')
            # [Migration] Map existing file-level vectors
            # Existing users have faiss_id == file_id in the clip_index.
            # We can't easily iterate FAISS here without loading it, but we can assume
            # that any already-processed file has a vector in the clip_index.
            # To be safe, we insert mapping for all processed files.
            c.execute('''
                INSERT INTO vector_mapping (faiss_id, entity_type, entity_id)
                SELECT id, 'file', id FROM files WHERE is_processed = 1
            ''')

        # Default Settings
        for key, default in [
            ("scene_threshold", "27.0"),
            ("auto_scene_detection", "false"),
            ("max_video_duration", "7200"),
            ("locale", "en"),
            ("demo_mode", "0"),
            ("last_opened", "0"),
            ("onboarding_dismissed", "false"),
        ]:
            try:
                c.execute("SELECT 1 FROM app_settings WHERE key = ?", (key,))
                if not c.fetchone():
                    import time
                    c.execute("INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)", (key, default, time.time()))
            except Exception as e:
                logger.debug(f"Default setting insert failed for {key}: {e}")
                pass

        # Create indexes for performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_files_tags ON files(tags)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_files_media_type ON files(media_type)")
        c.execute("DROP INDEX IF EXISTS idx_files_rating")
        c.execute("CREATE INDEX IF NOT EXISTS idx_files_favorite ON files(favorite)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_path)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_files_modified ON files(modified_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_video_scenes_file_id ON video_scenes(file_id)")

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
                favorite BOOLEAN DEFAULT 0,
                folder_path TEXT,
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

        # Video Scenes Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS video_scenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                caption TEXT,
                tags TEXT, -- JSON List
                character_tags TEXT, -- JSON List
                series_tags TEXT, -- JSON List
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')

        # Vector Mapping Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS vector_mapping (
                faiss_id INTEGER PRIMARY KEY,
                entity_type TEXT NOT NULL, -- 'file' or 'scene'
                entity_id INTEGER NOT NULL
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

    def verify_index_integrity(self):
        """Check FAISS index count matches SQLite vector_mapping count on startup.
        Repairs any orphaned vectors or dangling references automatically."""
        try:
            conn = self._connect()
            c = conn.cursor()
            c.execute("SELECT faiss_id, entity_type, entity_id FROM vector_mapping")
            mapping_rows = c.fetchall()
            
            sqlite_ids = {row[0] for row in mapping_rows}
            mapping_dict = {row[0]: (row[1], row[2]) for row in mapping_rows}
            sqlite_count = len(sqlite_ids)
            
            faiss_count = 0
            faiss_ids_set = set()
            if self.clip_index:
                try:
                    faiss_count = self.clip_index.ntotal
                    # Get all faiss IDs
                    if faiss_count > 0:
                        faiss_ids_array = faiss.vector_to_array(self.clip_index.id_map)
                        faiss_ids_set = set(int(fid) for fid in faiss_ids_array if fid != -1)
                except Exception as e:
                    logger.error(f"Failed to get FAISS ntotal or extract IDs: {e}")
                    faiss_count = 0

            # Find Orphans and Dangling references
            orphans = faiss_ids_set - sqlite_ids
            dangling = sqlite_ids - faiss_ids_set
            
            if not orphans and not dangling:
                logger.info(f"Index integrity OK: {sqlite_count} vectors mapped")
                conn.close()
                return

            logger.info(f"Index mismatch detected. Starting active repair. SQLite={sqlite_count}, FAISS={faiss_count}")
            
            needs_save = False

            if orphans:
                logger.info(f"Found {len(orphans)} orphaned vectors in FAISS. Removing...")
                try:
                    with self._faiss_lock:
                        self.clip_index.remove_ids(np.array(list(orphans), dtype='int64'))
                    needs_save = True
                    logger.info(f"Successfully removed {len(orphans)} orphaned vectors from FAISS.")
                except Exception as e:
                    logger.error(f"Failed to remove orphaned vectors from FAISS: {e}")

            if dangling:
                logger.info(f"Found {len(dangling)} dangling references in SQLite mappings. Cleaning up...")
                
                # To trigger re-scan, find the specific file IDs involved.
                file_ids_to_rescan = set()
                mapping_ids_to_delete = list(dangling)
                
                for faiss_id in dangling:
                    entity_type, entity_id = mapping_dict.get(faiss_id, (None, None))
                    if entity_type == 'file':
                        file_ids_to_rescan.add(entity_id)
                    elif entity_type == 'scene':
                        # Find the corresponding file_id for the scene
                        c.execute("SELECT file_id FROM video_scenes WHERE id = ?", (entity_id,))
                        row = c.fetchone()
                        if row:
                            file_ids_to_rescan.add(row[0])

                try:
                    # Set is_processed=0 for these files
                    if file_ids_to_rescan:
                        placeholders = ','.join(['?'] * len(file_ids_to_rescan))
                        c.execute(f"UPDATE files SET is_processed = 0 WHERE id IN ({placeholders})", list(file_ids_to_rescan))
                        logger.info(f"Set is_processed=0 for {len(file_ids_to_rescan)} files to trigger re-scan.")
                    
                    # Delete mappings
                    if mapping_ids_to_delete:
                        placeholders = ','.join(['?'] * len(mapping_ids_to_delete))
                        c.execute(f"DELETE FROM vector_mapping WHERE faiss_id IN ({placeholders})", mapping_ids_to_delete)
                        logger.info(f"Deleted {len(mapping_ids_to_delete)} dangling mappings from SQLite.")

                    conn.commit()
                except Exception as e:
                    logger.error(f"Failed to cleanup dangling references in SQLite: {e}")
                    conn.rollback()

            if needs_save:
                self.save_indices()
                logger.info("Saved repaired FAISS index.")

            conn.close()
            
        except Exception as e:
            logger.error(f"Index integrity check failed: {e}")


    def create_backup(self):
        """Create a backup of the SQLite database."""
        from datetime import datetime
        backup_dir = os.path.join(self.db_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        db_path = self.sqlite_path
        backup_path = os.path.join(backup_dir, f'localcurator_{timestamp}.db')
        
        try:
            # Use SQLite backup API for hot backup
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(backup_path)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            
            # Keep only last 5 backups
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
            while len(backups) > 5:
                old_backup = backups.pop(0)
                try:
                    os.remove(os.path.join(backup_dir, old_backup))
                except Exception as e:
                    logger.error(f"Failed to remove old backup {old_backup}: {e}")
            
            logger.info(f"Database backed up to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise e

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
                 
            # --- Cleanup Old Data (for re-processing) ---
            
            # 1. Cleanup CLIP vectors via vector_mapping
            # Get all FAISS IDs related to this file (the file itself and its scenes)
            c.execute('''
                SELECT faiss_id FROM vector_mapping 
                WHERE (entity_type = 'file' AND entity_id = ?)
                OR (entity_type = 'scene' AND entity_id IN (SELECT id FROM video_scenes WHERE file_id = ?))
            ''', (file_id, file_id))
            old_faiss_ids = [row[0] for row in c.fetchall()]
            
            # Fallback for legacy data (where faiss_id was file_id and no mapping existed)
            # We check if file_id exists in clip_index but not in vector_mapping
            c.execute('SELECT 1 FROM vector_mapping WHERE entity_type = "file" AND entity_id = ?', (file_id,))
            if not c.fetchone():
                old_faiss_ids.append(file_id)

            if old_faiss_ids:
                # 1. Delete mapping entries in SQLite first
                try:
                    placeholders = ','.join(['?'] * len(old_faiss_ids))
                    c.execute(f'DELETE FROM vector_mapping WHERE faiss_id IN ({placeholders})', old_faiss_ids)
                except Exception as e:
                    logger.error(f"SQLite mapping deletion failed: {e}")
                
                # 2. Cleanup CLIP vectors from FAISS
                try:
                    with self._faiss_lock:
                        self.clip_index.remove_ids(np.array(old_faiss_ids, dtype='int64'))
                except Exception as e:
                    logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for clip_index removal: {e}")

            # 2. Cleanup Scenes & Faces
            c.execute('DELETE FROM video_scenes WHERE file_id = ?', (file_id,))
            
            c.execute('SELECT id FROM faces WHERE file_id = ?', (file_id,))
            old_face_ids = [row[0] for row in c.fetchall()]
            if old_face_ids:
                # 1. Delete from faces in SQLite first
                try:
                    c.execute('DELETE FROM faces WHERE file_id = ?', (file_id,))
                except Exception as e:
                    logger.error(f"SQLite face deletion failed: {e}")

                # 2. Cleanup from FAISS
                try:
                    with self._faiss_lock:
                        self.face_index.remove_ids(np.array(old_face_ids, dtype='int64'))
                except Exception as e:
                    logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for face_index removal: {e}")

            # --- Add New Data ---

            if result.success:
                # 1. Add File CLIP Vector
                if vec_data and vec_data.clip_vector:
                    clip_vec = np.array([vec_data.clip_vector], dtype='float32')
                    faiss.normalize_L2(clip_vec)
                    
                    c.execute('INSERT INTO vector_mapping (entity_type, entity_id) VALUES (?, ?)', ('file', file_id))
                    faiss_id = c.lastrowid
                    
                    try:
                        with self._faiss_lock:
                            self.clip_index.add_with_ids(clip_vec, np.array([faiss_id], dtype='int64'))
                    except Exception as e:
                        logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for clip_index add: {e}")
                
                # 2. Add Video Scenes
                if result.scenes:
                    for scene in result.scenes:
                        c.execute('''
                            INSERT INTO video_scenes (
                                file_id, start_time, end_time, scene_index, thumbnail_path, 
                                start_frame, end_frame, caption, tags, character_tags, series_tags
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            file_id, scene.start_time, scene.end_time, scene.scene_index, scene.thumbnail_path,
                            scene.start_frame, scene.end_frame, scene.caption,
                            json.dumps(scene.tags), json.dumps(scene.character_tags), json.dumps(scene.series_tags)
                        ))
                        scene_id = c.lastrowid
                        
                        if scene.clip_vector:
                            scene_vec = np.array([scene.clip_vector], dtype='float32')
                            faiss.normalize_L2(scene_vec)
                            
                            c.execute('INSERT INTO vector_mapping (entity_type, entity_id) VALUES (?, ?)', ('scene', scene_id))
                            scene_faiss_id = c.lastrowid
                            
                            # Store the faiss_id in video_scenes for easy lookup
                            c.execute('UPDATE video_scenes SET clip_vector_id = ? WHERE id = ?', (scene_faiss_id, scene_id))
                            
                            try:
                                with self._faiss_lock:
                                    self.clip_index.add_with_ids(scene_vec, np.array([scene_faiss_id], dtype='int64'))
                            except Exception as e:
                                logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for scene clip_index add: {e}")

                # 3. Add Faces
                if vec_data and vec_data.face_vectors:
                    face_vecs = np.array(vec_data.face_vectors, dtype='float32')
                    faiss.normalize_L2(face_vecs)
                    
                    for i, face_vec in enumerate(face_vecs):
                        timestamp = result.faces[i].timestamp if i < len(result.faces) else 0.0
                        bbox_json = json.dumps(result.faces[i].bbox) if i < len(result.faces) else "[]"
                        
                        c.execute('INSERT INTO faces (file_id, face_index, timestamp, bbox) VALUES (?, ?, ?, ?)', (file_id, i, timestamp, bbox_json))
                        face_db_id = c.lastrowid
                        
                        try:
                            with self._faiss_lock:
                                self.face_index.add_with_ids(np.array([face_vec]), np.array([face_db_id], dtype='int64'))
                        except Exception as e:
                            logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for face_index add: {e}")

            conn.commit()
            
        except Exception as e:
            logger.error(f"DB Error in add_result for file {file_id}: {e}")
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
        
        faiss_ids = [int(idx) for idx in I[0] if idx != -1]
        scores = [float(s) for s, idx in zip(D[0], I[0]) if idx != -1]
        
        if not faiss_ids:
            return []
            
        conn = self._connect()
        c = conn.cursor()
        
        # Resolve Mapping efficiently
        placeholders = ','.join(['?'] * len(faiss_ids))
        c.execute(f'''
            SELECT m.faiss_id, m.entity_type, f.file_path, sf.file_path as scene_file_path
            FROM vector_mapping m
            LEFT JOIN files f ON m.entity_type = 'file' AND m.entity_id = f.id
            LEFT JOIN video_scenes s ON m.entity_type = 'scene' AND m.entity_id = s.id
            LEFT JOIN files sf ON s.file_id = sf.id
            WHERE m.faiss_id IN ({placeholders})
        ''', faiss_ids)
        
        mapping = {} # faiss_id -> file_path
        for row in c.fetchall():
            fid, etype, fpath, sfpath = row
            if etype == 'file' and fpath:
                mapping[fid] = fpath
            elif etype == 'scene' and sfpath:
                mapping[fid] = sfpath

        # Legacy fallback
        missing_ids = [fid for fid in faiss_ids if fid not in mapping]
        if missing_ids:
            # Assume missing mappings were direct file_ids (legacy)
            placeholders = ','.join(['?'] * len(missing_ids))
            c.execute(f"SELECT id, file_path FROM files WHERE id IN ({placeholders})", missing_ids)
            for row in c.fetchall():
                mapping[row[0]] = row[1]

        conn.close()
        
        results = []
        seen_paths = set()
        for fid, score in zip(faiss_ids, scores):
            if fid in mapping:
                path = mapping[fid]
                if path not in seen_paths:
                    results.append((path, score))
                    seen_paths.add(path)
                
        return results[:top_k]

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
            
            paths = [r.media_item.file_path for r in results]
            placeholders = ','.join(['?'] * len(paths))
            c.execute(f"SELECT file_path, id FROM files WHERE file_path IN ({placeholders})", paths)
            path_to_id = {row[0]: row[1] for row in c.fetchall()}
            file_ids = list(path_to_id.values())
            
            # --- Cleanup Old Data in Batch ---
            if file_ids:
                fid_placeholders = ','.join(['?'] * len(file_ids))
                
                # Get all CLIP FAISS IDs
                c.execute(f'''
                    SELECT faiss_id FROM vector_mapping 
                    WHERE (entity_type = 'file' AND entity_id IN ({fid_placeholders}))
                    OR (entity_type = 'scene' AND entity_id IN (SELECT id FROM video_scenes WHERE file_id IN ({fid_placeholders})))
                ''', file_ids + file_ids)
                old_faiss_ids = [row[0] for row in c.fetchall()]
                
                # Legacy fallback check
                # IDs that are in files but not in vector_mapping as 'file'
                c.execute(f'''
                    SELECT id FROM files 
                    WHERE id IN ({fid_placeholders}) 
                    AND id NOT IN (SELECT entity_id FROM vector_mapping WHERE entity_type = 'file')
                ''', file_ids)
                old_faiss_ids.extend([row[0] for row in c.fetchall()])

                if old_faiss_ids:
                    # 1. SQLite Mapping Delete First
                    try:
                        mapping_placeholders = ','.join(['?'] * len(old_faiss_ids))
                        c.execute(f'DELETE FROM vector_mapping WHERE faiss_id IN ({mapping_placeholders})', old_faiss_ids)
                    except Exception as e:
                        logger.error(f"SQLite mapping batch deletion failed: {e}")

                    # 2. FAISS Index Cleanup
                    try:
                        with self._faiss_lock:
                            self.clip_index.remove_ids(np.array(old_faiss_ids, dtype='int64'))
                    except Exception as e:
                        logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for clip_index batch removal: {e}")

                # Cleanup scenes & faces
                c.execute(f'DELETE FROM video_scenes WHERE file_id IN ({fid_placeholders})', file_ids)
                
                c.execute(f'SELECT id FROM faces WHERE file_id IN ({fid_placeholders})', file_ids)
                old_face_ids = [row[0] for row in c.fetchall()]
                if old_face_ids:
                    # 1. SQLite Face Delete First
                    try:
                        c.execute(f'DELETE FROM faces WHERE id IN ({",".join(["?"] * len(old_face_ids))})', old_face_ids)
                    except Exception as e:
                        logger.error(f"SQLite faces batch deletion failed: {e}")

                    # 2. FAISS Index Cleanup
                    try:
                        with self._faiss_lock:
                            self.face_index.remove_ids(np.array(old_face_ids, dtype='int64'))
                    except Exception as e:
                        logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for face_index batch removal: {e}")

            # --- Add New Data ---
            clip_vectors_to_add = []
            clip_ids_to_add = []
            
            face_vectors_to_add = []
            face_ids_to_add = []
            
            for r in results:
                if not r.success:
                    continue
                
                fid = path_to_id.get(r.media_item.file_path)
                if fid is None:
                    continue

                # 1. File CLIP Vector
                if r.vector_data and r.vector_data.clip_vector:
                    c.execute('INSERT INTO vector_mapping (entity_type, entity_id) VALUES (?, ?)', ('file', fid))
                    faiss_id = c.lastrowid
                    clip_vectors_to_add.append(r.vector_data.clip_vector)
                    clip_ids_to_add.append(faiss_id)
                
                # 2. Video Scenes
                if r.scenes:
                    for scene in r.scenes:
                        c.execute('''
                            INSERT INTO video_scenes (
                                file_id, start_time, end_time, scene_index, thumbnail_path, 
                                start_frame, end_frame, caption, tags, character_tags, series_tags
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            fid, scene.start_time, scene.end_time, scene.scene_index, scene.thumbnail_path,
                            scene.start_frame, scene.end_frame, scene.caption,
                            json.dumps(scene.tags), json.dumps(scene.character_tags), json.dumps(scene.series_tags)
                        ))
                        scene_id = c.lastrowid
                        
                        if scene.clip_vector:
                            c.execute('INSERT INTO vector_mapping (entity_type, entity_id) VALUES (?, ?)', ('scene', scene_id))
                            scene_faiss_id = c.lastrowid
                            
                            # Store the faiss_id in video_scenes for easy lookup
                            c.execute('UPDATE video_scenes SET clip_vector_id = ? WHERE id = ?', (scene_faiss_id, scene_id))
                            
                            clip_vectors_to_add.append(scene.clip_vector)
                            clip_ids_to_add.append(scene_faiss_id)

                # 3. Faces
                if r.vector_data and r.vector_data.face_vectors:
                    for i, fvec in enumerate(r.vector_data.face_vectors):
                        timestamp = r.faces[i].timestamp if i < len(r.faces) else 0.0
                        bbox = json.dumps(r.faces[i].bbox) if i < len(r.faces) else "[]"
                        
                        c.execute('INSERT INTO faces (file_id, face_index, timestamp, bbox) VALUES (?, ?, ?, ?)', (fid, i, timestamp, bbox))
                        face_db_id = c.lastrowid
                        face_vectors_to_add.append(fvec)
                        face_ids_to_add.append(face_db_id)

            # --- Commit to FAISS ---
            if clip_vectors_to_add:
                vecs = np.array(clip_vectors_to_add, dtype='float32')
                ids = np.array(clip_ids_list if 'clip_ids_list' in locals() else clip_ids_to_add, dtype='int64') # Wait, clip_ids_list was old name
                ids = np.array(clip_ids_to_add, dtype='int64')
                faiss.normalize_L2(vecs)
                try:
                    with self._faiss_lock:
                        self.clip_index.add_with_ids(vecs, ids)
                except Exception as e:
                    logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for clip_index batch add: {e}")
            
            if face_vectors_to_add:
                f_vecs = np.array(face_vectors_to_add, dtype='float32')
                f_ids = np.array(face_ids_to_add, dtype='int64')
                faiss.normalize_L2(f_vecs)
                try:
                    with self._faiss_lock:
                        self.face_index.add_with_ids(f_vecs, f_ids)
                except Exception as e:
                    logger.error(f"FAISS index inconsistency: SQLite updated but FAISS operation failed for face_index batch add: {e}")

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

    def get_video_scenes(self, file_id: int) -> List[Dict]:
        """Get all scenes for a specific video file."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute('''
                SELECT id, start_time, end_time, caption, tags, character_tags, series_tags
                FROM video_scenes WHERE file_id = ?
                ORDER BY start_time ASC
            ''', (file_id,))
            rows = c.fetchall()
            return [dict(row) for row in rows]
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
                except Exception as e:
                    logger.warning(f"JSON parse failure for tags in remove_tags: {e}")
                    return []
                
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
    # Tag Editing Methods
    # ------------------------------------------------------------------ #

    def _get_tag_column(self, category: str) -> str:
        mapping = {
            "general": "tags",
            "character": "character_tags",
            "series": "series_tags"
        }
        if category not in mapping:
            raise ValueError(f"Invalid tag category: {category}")
        return mapping[category]
    def _deduplicate_tags_ci(self, tags: List[str]) -> List[str]:
        seen = set()
        result = []
        for tag in tags:
            clean = tag.strip()
            if not clean:
                continue
            if clean.lower() not in seen:
                seen.add(clean.lower())
                result.append(clean)
        return result

    def add_tags(self, file_id: int, tags: List[str], category: str = "general") -> List[str]:
        """Append tags to the specified category, deduplicate, and return updated list."""
        tags = self._deduplicate_tags_ci(tags)
        column = self._get_tag_column(category)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            c.execute(f"SELECT {column} FROM files WHERE id = ?", (file_id,))
            row = c.fetchone()
            if not row:
                raise ValueError(f"File ID {file_id} not found")
            
            def safe_parse(val):
                if not val: return []
                try: return json.loads(val)
                except Exception as e:
                    logger.warning(f"JSON parse failure for tags in add_tags: {e}")
                    return []
            
            current_tags = safe_parse(row[0])
            # Case-insensitive deduplication while preserving original case if already present
            # For simplicity, we'll just use a set of lowercase to check, but keep original if it exists
            new_tags_set = set(t.strip() for t in tags if t.strip())
            updated_tags = current_tags[:]
            
            lowercase_current = [t.lower() for t in current_tags]
            for nt in new_tags_set:
                if nt.lower() not in lowercase_current:
                    updated_tags.append(nt)
            
            c.execute(f"UPDATE files SET {column} = ? WHERE id = ?", (json.dumps(updated_tags), file_id))
            conn.commit()
            return updated_tags
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def remove_tags(self, file_id: int, tags: List[str], category: str = "general") -> List[str]:
        """Remove tags from the specified category and return updated list."""
        column = self._get_tag_column(category)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        try:
            c.execute(f"SELECT {column} FROM files WHERE id = ?", (file_id,))
            row = c.fetchone()
            if not row:
                raise ValueError(f"File ID {file_id} not found")
            
            def safe_parse(val):
                if not val: return []
                try: return json.loads(val)
                except Exception as e:
                    logger.warning(f"JSON parse failure for tags in remove_tags: {e}")
                    return []
                
            current_tags = safe_parse(row[0])
            to_remove = set(t.lower() for t in tags)
            updated_tags = [t for t in current_tags if t.lower() not in to_remove]
            
            c.execute(f"UPDATE files SET {column} = ? WHERE id = ?", (json.dumps(updated_tags), file_id))
            conn.commit()
            return updated_tags
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def bulk_update_tags(self, file_ids: List[int], action: str, tags: List[str], category: str = "general") -> Dict[str, Any]:
        """Update tags for multiple files in a single transaction."""
        tags = self._deduplicate_tags_ci(tags)
        column = self._get_tag_column(category)
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        affected_count = 0
        errors = []
        
        def safe_parse(val):
            if not val: return []
            try:
                return json.loads(val)
            except Exception as e:
                logger.warning(f"JSON parse failure for tags in bulk_update_tags: {e}")
                return []

        try:
            # We use a single transaction for efficiency
            for fid in file_ids:
                try:
                    c.execute(f"SELECT {column} FROM files WHERE id = ?", (fid,))
                    row = c.fetchone()
                    if not row:
                        errors.append({"file_id": fid, "error": "File not found"})
                        continue
                    
                    current_tags = safe_parse(row[0])
                    updated_tags = current_tags[:]
                    
                    if action == "add":
                        new_tags_set = set(t.strip() for t in tags if t.strip())
                        lowercase_current = [t.lower() for t in current_tags]
                        for nt in new_tags_set:
                            if nt.lower() not in lowercase_current:
                                updated_tags.append(nt)
                    elif action == "remove":
                        to_remove = set(t.lower() for t in tags)
                        updated_tags = [t for t in current_tags if t.lower() not in to_remove]
                    elif action == "replace":
                        updated_tags = [t.strip() for t in tags if t.strip()]
                    else:
                        raise ValueError(f"Invalid action: {action}")
                    
                    c.execute(f"UPDATE files SET {column} = ? WHERE id = ?", (json.dumps(updated_tags), fid))
                    affected_count += 1
                except Exception as e:
                    errors.append({"file_id": fid, "error": str(e)})
            
            conn.commit()
            return {"affected_count": affected_count, "errors": errors}
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def suggest_tags(self, query: str, category: str = "general", limit: int = 10) -> List[Dict[str, Any]]:
        """Autocomplete suggestions based on prefix match, ordered by usage count."""
        column = self._get_tag_column(category)
        conn = self._connect()
        c = conn.cursor()
        
        try:
            # Use json_each to flatten the array of tags
            # We want to count occurrences of each tag that matches the prefix
            # Note: prefix match is case-insensitive by default in some SQLite setups, 
            # but we'll use LOWER() for safety.
            sql = f"""
                SELECT value as tag, COUNT(*) as count
                FROM files, json_each({column})
                WHERE LOWER(value) LIKE ?
                GROUP BY value
                ORDER BY count DESC
                LIMIT ?
            """
            c.execute(sql, (f"{query.lower()}%", limit))
            rows = c.fetchall()
            return [{"tag": row[0], "count": row[1]} for row in rows]
        finally:
            conn.close()

    def search_scenes(self, query_vector: List[float], top_k: int = 20) -> List[Dict[str, Any]]:
        """Semantic search specifically for video scenes."""
        if self.clip_index is None:
            return []
            
        params = np.array([query_vector], dtype='float32')
        faiss.normalize_L2(params)
        
        # We need to search more than top_k because some hits might be files
        k_search = top_k * 5
        D, I = self.clip_index.search(params, k_search)
        
        faiss_ids = [int(idx) for idx in I[0] if idx != -1]
        faiss_id_to_score = {int(idx): float(score) for idx, score in zip(I[0], D[0]) if idx != -1}
        
        if not faiss_ids:
            return []
            
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        placeholders = ','.join(['?'] * len(faiss_ids))
        # Filter vector_mapping for 'scene' type
        c.execute(f'''
            SELECT m.faiss_id, m.entity_id as scene_id, s.file_id, f.file_path, 
                   s.scene_index, s.start_time, s.end_time, s.thumbnail_path,
                   s.caption, s.tags, s.character_tags, s.series_tags
            FROM vector_mapping m
            JOIN video_scenes s ON m.entity_id = s.id
            JOIN files f ON s.file_id = f.id
            WHERE m.entity_type = 'scene' AND m.faiss_id IN ({placeholders})
        ''', faiss_ids)
        
        results = []
        for row in c.fetchall():
            res = dict(row)
            res['score'] = faiss_id_to_score.get(res['faiss_id'], 0.0)
            # Remove faiss_id from final output if desired
            results.append(res)
            
        conn.close()
        
        # Sort by score and limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

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
            
        faiss_id_to_score = {idx: score for idx, score in candidates}
        faiss_ids = [idx for idx, _ in candidates]
        
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # 1. Resolve faiss_ids to file_ids and metadata
        placeholders = ','.join(['?'] * len(faiss_ids))
        c.execute(f'''
            SELECT m.faiss_id, m.entity_type, m.entity_id, 
                   s.file_id as scene_parent_id, s.start_time, s.end_time, s.caption as scene_caption
            FROM vector_mapping m
            LEFT JOIN video_scenes s ON m.entity_type = 'scene' AND m.entity_id = s.id
            WHERE m.faiss_id IN ({placeholders})
        ''', faiss_ids)
        
        mapping = {} # faiss_id -> {file_id, is_scene, scene_id, ...}
        for row in c.fetchall():
            fid = row['faiss_id']
            if row['entity_type'] == 'file':
                mapping[fid] = {'file_id': row['entity_id'], 'is_scene': False}
            else:
                mapping[fid] = {
                    'file_id': row['scene_parent_id'], 
                    'is_scene': True,
                    'scene_id': row['entity_id'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'scene_caption': row['scene_caption']
                }

        # Legacy fallback
        missing_ids = [fid for fid in faiss_ids if fid not in mapping]
        if missing_ids:
            for fid in missing_ids:
                mapping[fid] = {'file_id': fid, 'is_scene': False}

        file_id_to_max_score = {} # Highest score per file
        file_id_to_best_scene = {} # Best scene metadata if multiple match
        
        for fid, score in faiss_id_to_score.items():
            if fid in mapping:
                m = mapping[fid]
                file_id = m['file_id']
                if not file_id: continue # Should not happen with clean DB
                
                if score > file_id_to_max_score.get(file_id, 0.0):
                    file_id_to_max_score[file_id] = score
                    if m['is_scene']:
                        file_id_to_best_scene[file_id] = m
                    else:
                        file_id_to_best_scene.pop(file_id, None)

        relevant_file_ids = list(file_id_to_max_score.keys())
        if not relevant_file_ids:
            conn.close()
            return []
            
        # 2. Build SQL filters
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

        final_results = []
        # Chunk file_ids by 500 to avoid SQL variable limits
        for i in range(0, len(relevant_file_ids), 500):
            chunk = relevant_file_ids[i:i+500]
            placeholders = ','.join(['?'] * len(chunk))
            
            query = f"SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, caption FROM files WHERE id IN ({placeholders})"
            if where_clauses:
                query += " AND " + " AND ".join(where_clauses)
            
            c.execute(query, chunk + sql_params)
            for r in c.fetchall():
                row = dict(r)
                fid = row['id']
                row['score'] = file_id_to_max_score[fid]
                if fid in file_id_to_best_scene:
                    row['matched_scene'] = file_id_to_best_scene[fid]
                final_results.append(row)
            
        conn.close()
        
        final_results.sort(key=lambda x: x['score'], reverse=True)
        return final_results[:top_k]

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

    # ------------------------------------------------------------------ #
    # Tag Dashboard Methods
    # ------------------------------------------------------------------ #

    def get_tag_stats(self) -> Dict[str, Any]:
        """Returns all tags with usage counts grouped by category."""
        conn = self._connect()
        c = conn.cursor()
        
        try:
            stats = {}
            total_unique_tags = set()
            
            for category, column in [("general", "tags"), ("character", "character_tags"), ("series", "series_tags")]:
                # Use json_each to flatten and count
                sql = f"""
                    SELECT value as tag, COUNT(*) as count
                    FROM files, json_each(files.{column})
                    GROUP BY value
                    ORDER BY count DESC
                """
                c.execute(sql)
                rows = c.fetchall()
                category_tags = [{"tag": row[0], "count": row[1]} for row in rows]
                stats[category] = category_tags
                for row in rows:
                    total_unique_tags.add((category, row[0]))
            
            stats["total_tags"] = len(total_unique_tags)
            
            # untagged_count: COUNT of files where tags is NULL or empty JSON array '[]'
            c.execute("SELECT COUNT(*) FROM files WHERE tags IS NULL OR tags = '[]'")
            stats["untagged_count"] = c.fetchone()[0]
            
            return stats
        finally:
            conn.close()

    def get_untagged_files(self, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """Returns files with no tags."""
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        offset = (page - 1) * per_page
        
        try:
            # Files with no tags - following spec: tags IS NULL OR tags = '[]'
            where_clause = "tags IS NULL OR tags = '[]'"
            
            c.execute(f"SELECT COUNT(*) FROM files WHERE {where_clause}")
            total_count = c.fetchone()[0]
            
            c.execute(f"""
                SELECT id, file_path, media_type, width, height, tags, character_tags, series_tags, caption
                FROM files
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            rows = c.fetchall()
            return {
                "files": [dict(r) for r in rows],
                "total_count": total_count
            }
        finally:
            conn.close()

    def rename_tag(self, old_tag: str, new_tag: str, category: str) -> Dict[str, int]:
        """
        Rename or delete a tag across all files.
        If new_tag is empty, it's a deletion.
        """
        column = self._get_tag_column(category)
        conn = self._connect()
        c = conn.cursor()
        
        renamed_count = 0
        merged_count = 0
        
        try:
            # Find all files containing the old tag
            c.execute(f"""
                SELECT DISTINCT files.id FROM files, json_each(files.{column})
                WHERE value = ?
            """, (old_tag,))
            file_ids = [row[0] for row in c.fetchall()]
            
            for fid in file_ids:
                c.execute(f"SELECT {column} FROM files WHERE id = ?", (fid,))
                row = c.fetchone()
                if not row: continue
                
                tags = json.loads(row[0]) if row[0] else []
                
                # Check if new_tag already exists in this file (case-insensitive check but original preserve)
                has_new = False
                if new_tag:
                    has_new = any(t.lower() == new_tag.lower() for t in tags)
                
                # Remove old tag (exact match)
                new_tags_list = [t for t in tags if t != old_tag]
                
                if new_tag:
                    if not has_new:
                        new_tags_list.append(new_tag)
                        renamed_count += 1
                    else:
                        # old_tag removed, new_tag already there.
                        merged_count += 1
                else:
                    # Deletion case: old tag matched and removed
                    renamed_count += 1
                
                c.execute(f"UPDATE files SET {column} = ? WHERE id = ?", (json.dumps(new_tags_list), fid))
            
            conn.commit()
            return {"renamed_count": renamed_count, "merged_count": merged_count}
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    def get_insights(self) -> List[Dict[str, Any]]:
        """
        Analyze the library and return actionable suggestions.
        """
        insights = []
        insights.extend(self._insight_duplicates())
        insights.extend(self._insight_untagged())
        insights.extend(self._insight_album_suggestions())
        insights.extend(self._insight_low_quality_tags())
        return insights

    def _insight_duplicates(self) -> List[Dict[str, Any]]:
        from src.core.deduplication import Deduplicator
        deduper = Deduplicator(self)
        try:
            # Quick check: do we have enough vectors to even have duplicates?
            if self.clip_index.ntotal < 2:
                return []
                
            # We use a relatively high threshold for insights to avoid noise
            pairs = deduper.find_duplicates(threshold_img=0.98, threshold_vid=0.99)
            if len(pairs) > 0:
                return [{
                    "type": "duplicate_found",
                    "title": "Similar images detected",
                    "message": f"{len(pairs)} groups of similar images found in your library",
                    "action_url": "/settings",
                    "action_label": "Open Cleaner",
                    "priority": "high",
                    "count": len(pairs)
                }]
        except Exception as e:
            logger.error(f"Insight duplication check failed: {e}")
        return []

    def _insight_untagged(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        c = conn.cursor()
        try:
            c.execute("SELECT COUNT(*) FROM files WHERE tags IS NULL OR tags = '[]' OR tags = ''")
            count = c.fetchone()[0]
            if count > 0:
                return [{
                    "type": "untagged_files",
                    "title": "Untagged files",
                    "message": f"{count} files categorized as untagged",
                    "action_url": "/tags",
                    "action_label": "Tag Dashboard",
                    "priority": "high" if count > 50 else "medium",
                    "count": count
                }]
        finally:
            conn.close()
        return []

    def _insight_album_suggestions(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        c = conn.cursor()
        try:
            # Find top 3 tags with 20+ files
            c.execute("""
                SELECT value as tag, COUNT(*) as count
                FROM files, json_each(files.tags)
                GROUP BY value
                HAVING count >= 20
                ORDER BY count DESC
                LIMIT 10
            """)
            top_tags = c.fetchall()
            
            # Check if any of these already have an album
            c.execute("SELECT name FROM albums")
            existing_albums = {row[0].lower() for row in c.fetchall()}
            
            suggestions = []
            for tag, count in top_tags:
                if tag.lower() not in existing_albums:
                    query_json = json.dumps({
                        "query": "",
                        "filters": {"tags": [tag]},
                        "top_k": 100
                    })
                    suggestions.append({
                        "type": "album_suggestion",
                        "title": "New Smart Album?",
                        "message": f'"{tag}" appears in {count} files — create a Smart Album?',
                        "action_url": f"/api/albums", # Handled specially by frontend
                        "action_label": "Create Album",
                        "priority": "medium",
                        "tag": tag,
                        "query_json": query_json,
                        "count": count
                    })
                    if len(suggestions) >= 3:
                        break
            return suggestions
        finally:
            conn.close()
        return []

    def _insight_low_quality_tags(self) -> List[Dict[str, Any]]:
        conn = self._connect()
        c = conn.cursor()
        try:
            # Files with 1-2 tags that HAVE been processed (so we actually extracted something but it's sparse)
            c.execute("""
                SELECT COUNT(*) FROM files 
                WHERE is_processed = 1 
                AND tags IS NOT NULL 
                AND json_array_length(tags) > 0 
                AND json_array_length(tags) <= 2
            """)
            count = c.fetchone()[0]
            if count > 10:
                return [{
                    "type": "low_quality_tags",
                    "title": "Sparse metadata",
                    "message": f"{count} files have very few tags — consider rescanning them",
                    "action_url": "/tags",
                    "action_label": "View Tags",
                    "priority": "low",
                    "count": count
                }]
        finally:
            conn.close()
        return []
