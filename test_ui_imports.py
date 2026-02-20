
import os
import sys

sys.path.append(os.path.abspath("src"))

try:
    from src.ui.cluster_view import render_cluster_view
    from src.ui.cleaner_view import render_cleaner_view
    from app import main
    print("UI Imports Successful")
except ImportError as e:
    print(f"Import Failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Other Error: {e}")
    sys.exit(1)
