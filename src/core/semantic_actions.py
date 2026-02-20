import ollama
import sqlite3
import json
import os
import datetime
from typing import List, Dict, Any, Optional

from ..data.db_manager import DBManager
from ..data.schemas import MediaItem
from .sorter import PhysicalSorter, SortLog

class SemanticEngine:
    def __init__(self, model_name: str = "mistral-nemo"): # Standardized on mistral-nemo
        self.model_name = model_name
        self.client = ollama.Client(host='http://localhost:11434')

    def ping(self) -> bool:
        """Check if Ollama server is reachable and model is available."""
        try:
            models = self.client.list()
            # Optionally check if model_name is in models
            return True
        except Exception:
            return False

    def parse_and_execute(self, prompt: str, dest_root: str, operation: str, db_manager: DBManager, sorter: PhysicalSorter, logger: SortLog) -> Dict[str, Any]:
        """
        Parses the natural language prompt using LLM function calling and executes the sort.
        """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "organize_files",
                    "description": "Find files matching criteria and move them to a destination",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition_type": {
                                "type": "string",
                                "enum": ["tag", "year", "media_type", "character", "series"],
                                "description": "The type of condition to filter files by. Use 'tag' for general objects/styles (e.g., screenshot, photo, landscape), 'year' for dates, 'media_type' for 'image'/'video', 'character' for person names, 'series' for franchise names."
                            },
                            "condition_value": {
                                "type": "string",
                                "description": "The value to search for. For years, use YYYY format. For tags/characters, use lowercase string."
                            },
                            "destination_folder": {
                                "type": "string",
                                "description": "The name of the destination folder (e.g., 'trash', '2023_Archive')."
                            }
                        },
                        "required": ["condition_type", "condition_value", "destination_folder"]
                    }
                }
            }
        ]
        
        system_prompt = "You are an AI assistant that helps organize files. The user will ask you to move certain files into a specific folder. Map their request directly to the `organize_files` tool. Example 1: 'Move screenshots to trash' -> condition_type='tag', condition_value='screenshot', destination_folder='trash'. Example 2: 'Move 2023 photos to Archive' -> condition_type='year', condition_value='2023', destination_folder='Archive'. Example 3: '動画をVideosに移動' -> condition_type='media_type', condition_value='video', destination_folder='Videos'."

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                tools=tools
            )
        except Exception as e:
            return {"success": False, "error": f"Failed to connect to Ollama or run inference: {e}"}

        message = response.get('message', {})
        if not message.get('tool_calls'):
            return {"success": False, "error": "LLM did not return a valid tool call. It might not have understood your request, or the model doesn't support tools."}

        tool_call = message['tool_calls'][0]
        args = tool_call.get('function', {}).get('arguments', {})
        
        cond_type = args.get('condition_type')
        cond_val = args.get('condition_value')
        dest_folder = args.get('destination_folder')
        
        if not all([cond_type, cond_val, dest_folder]):
            return {"success": False, "error": f"LLM returned incomplete arguments: {args}"}

        # Validate conditions
        if cond_type == "year" and not str(cond_val).isdigit():
             return {"success": False, "error": f"Year must be a number, got: {cond_val}"}

        # Query DB based on condition
        conn = sqlite3.connect(db_manager.sqlite_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = "SELECT * FROM files WHERE is_processed=1 AND error_msg IS NULL"
        params = []
        
        if cond_type == "tag":
            query += " AND tags LIKE ?"
            params.append(f"%{cond_val.lower()}%")
        elif cond_type == "year":
            try:
                year_start = datetime.datetime(int(cond_val), 1, 1).timestamp()
                year_end = datetime.datetime(int(cond_val), 12, 31, 23, 59, 59).timestamp()
                query += " AND created_at >= ? AND created_at <= ?"
                params.extend([year_start, year_end])
            except ValueError:
                conn.close()
                return {"success": False, "error": f"Invalid year value: {cond_val}"}
        elif cond_type == "media_type":
            # ensure 'video' or 'image'
            val = cond_val.lower()
            if "video" in val or "movie" in val: val = "video"
            elif "image" in val or "photo" in val or "picture" in val: val = "image"
            query += " AND media_type = ?"
            params.append(val)
        elif cond_type == "character":
            query += " AND character_tags LIKE ?"
            params.append(f"%{cond_val}%")
        elif cond_type == "series":
            query += " AND series_tags LIKE ?"
            params.append(f"%{cond_val}%")

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        
        if not rows:
             return {"success": True, "processed": 0, "message": f"Operation aborted: No files found for {cond_type}='{cond_val}'", "args_used": args, "logs": []}
        
        count = 0
        logs = []
        
        for row in rows:
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
                 tags=json.loads(row['tags']) if row['tags'] else [],
                 character_tags=json.loads(row['character_tags']) if 'character_tags' in row.keys() and row['character_tags'] else [],
                 series_tags=json.loads(row['series_tags']) if 'series_tags' in row.keys() and row['series_tags'] else [],
                 error_msg=row['error_msg']
             )
             
             # Call sorter with the destination_folder as the category
             # sorter.sort_file will put it in dest_root/category/filename
             success = sorter.sort_file(item, dest_root, dest_folder, operation)
             if success:
                 count += 1
                 logs.append(f"[{operation.upper()}] {os.path.basename(item.file_path)} -> {dest_folder}")
                 
        return {
            "success": True, 
            "processed": count, 
            "message": f"Successfully processed {count} files.", 
            "logs": logs,
            "args_used": args
        }
