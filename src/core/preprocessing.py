from PIL import Image
import os
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """
    Handles robust image loading and preprocessing.
    Decouples PIL dependency from main logic.
    """
    
    @staticmethod
    def load_image(path: str, convert_mode: str = 'RGB') -> Optional[Image.Image]:
        """
        Load an image from path.
        Returns None if loading fails.
        """
        try:
            img = Image.open(path)
            if convert_mode:
                img = img.convert(convert_mode)
            return img
        except Exception as e:
            logger.error(f"Failed to load image {path}: {e}")
            return None
            
    @staticmethod
    def get_dimensions(path: str) -> Tuple[int, int]:
        """
        Get (width, height) without fully loading the file if possible?
        PIL.Image.open is lazy, so it reads header.
        """
        try:
            with Image.open(path) as img:
                return img.size
        except:
            return (0, 0)
