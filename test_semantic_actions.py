import unittest
from unittest.mock import patch, MagicMock
from src.core.semantic_actions import SemanticEngine

class TestSemanticEngine(unittest.TestCase):
    @patch('src.core.semantic_actions.ollama.Client')
    @patch('src.core.semantic_actions.sqlite3.connect')
    def test_semantic_engine_parsing(self, mock_sqlite, mock_ollama_client):
        # Mock Ollama Client
        mock_client_instance = MagicMock()
        mock_ollama_client.return_value = mock_client_instance
        
        # Mock response
        mock_client_instance.chat.return_value = {
            'message': {
                'tool_calls': [{
                    'function': {
                        'name': 'organize_files',
                        'arguments': {
                            'condition_type': 'tag',
                            'condition_value': 'screenshot',
                            'destination_folder': 'trash'
                        }
                    }
                }]
            }
        }
        
        # Mock DB SQLite
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock DB data directly
        mock_cursor.fetchall.return_value = [
            {
                'file_path': 'C:/fake/img1.png', 'file_hash': 'h1', 'file_size': 100,
                'media_type': 'image', 'created_at': 1000, 'modified_at': 1000,
                'width': 800, 'height': 600, 'duration': 0, 
                'tags': '["screenshot"]', 'character_tags': '[]', 'series_tags': '[]',
                'error_msg': None
            }
        ]
        
        engine = SemanticEngine(model_name="test-model")
        
        mock_db_manager = MagicMock()
        mock_db_manager.sqlite_path = "fake.db"
        
        mock_sorter = MagicMock()
        mock_sorter.sort_file.return_value = True
        
        mock_logger = MagicMock()
        
        result = engine.parse_and_execute(
            prompt="Move screenshots to trash",
            dest_root="C:/SortedMedia",
            operation="dry_run",
            db_manager=mock_db_manager,
            sorter=mock_sorter,
            logger=mock_logger
        )
        
        # Verifications
        self.assertTrue(result['success'])
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['args_used']['condition_value'], 'screenshot')
        self.assertEqual(result['args_used']['destination_folder'], 'trash')
        
        # Check that sorter was called with correct parameters
        mock_sorter.sort_file.assert_called_once()
        called_args, _ = mock_sorter.sort_file.call_args
        called_item = called_args[0]
        self.assertEqual(called_item.file_path, 'C:/fake/img1.png')
        self.assertEqual(called_args[2], 'trash') # destination_folder
        self.assertEqual(called_args[3], 'dry_run') # operation

if __name__ == '__main__':
    unittest.main()
