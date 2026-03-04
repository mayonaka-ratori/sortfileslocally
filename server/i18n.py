from typing import Dict

class I18nManager:
    # Default messages for backend errors
    MESSAGES = {
        "en": {
            "error_file_not_found": "File not found: {path}",
            "error_invalid_folder": "Invalid folder path: {path}",
            "error_scan_already_running": "A scan is already running.",
            "error_model_not_loaded": "Failed to load AI model: {model}",
            "error_database_locked": "Database is temporarily locked. Please try again.",
            "status_ready": "System ready.",
            "status_processing": "Processing {current}/{total}...",
            "status_complete": "Processing complete."
        },
        "ja": {
            "error_file_not_found": "ファイルが見つかりません: {path}",
            "error_invalid_folder": "無効なフォルダーパスです: {path}",
            "error_scan_already_running": "スキャンは既に実行中です。",
            "error_model_not_loaded": "AIモデルの読み込みに失敗しました: {model}",
            "error_database_locked": "データベースがロックされています。後で再試行してください。",
            "status_ready": "システム準備完了",
            "status_processing": "{current}/{total} 個を処理中...",
            "status_complete": "処理が完了しました。"
        }
    }

    def __init__(self, default_lang: str = "en"):
        self.lang = default_lang

    def set_language(self, lang: str):
        if lang in self.MESSAGES:
            self.lang = lang

    def t(self, key: str, **kwargs) -> str:
        msg = self.MESSAGES.get(self.lang, self.MESSAGES["en"]).get(key, key)
        try:
            return msg.format(**kwargs)
        except Exception:
            return msg

# Global instance
backend_i18n = I18nManager("ja")
