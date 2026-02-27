"""
ModelManager: Centralized registry for all AI model files.

Provides status checks (downloaded/missing/size), and hooks into
huggingface_hub download callbacks for progress streaming.
"""

import os
import time
import threading
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Describes a single model dependency."""
    name: str               # Human readable name
    key: str                # Unique identifier
    source: str             # e.g. "huggingface", "open_clip", "insightface"
    repo_id: str            # HF repo or model name
    files: List[str]        # Expected filenames on disk
    estimated_size_mb: int  # Approximate total download size
    local_dir: str          # Where files should be stored

    @property
    def is_downloaded(self) -> bool:
        """Check if all expected model files are available."""
        if self.source in ("huggingface", "open_clip"):
            # HF cache stores files in nested subdirectories
            return all(self._find_hf_file(f) is not None for f in self.files)
        # Local-dir models (insightface, joytag with explicit dir)
        return all(
            os.path.exists(os.path.join(self.local_dir, f))
            for f in self.files
        )

    @property
    def local_size_mb(self) -> float:
        total = 0
        for f in self.files:
            resolved = self._resolve_file(f)
            if resolved and os.path.exists(resolved):
                total += os.path.getsize(resolved)
        return round(total / (1024 * 1024), 1)

    def _resolve_file(self, filename: str) -> Optional[str]:
        """Get the actual path for a model file."""
        if self.source in ("huggingface", "open_clip"):
            return self._find_hf_file(filename)
        path = os.path.join(self.local_dir, filename)
        return path if os.path.exists(path) else None

    def _find_hf_file(self, filename: str) -> Optional[str]:
        """Find a file inside the HF cache using try_to_load_from_cache."""
        try:
            from huggingface_hub import try_to_load_from_cache
            result = try_to_load_from_cache(self.repo_id, filename)
            if result is not None and isinstance(result, str):
                return result
        except Exception as e:
            # We don't want to spam logs here as this is a frequent check, but at least debug log it
            logger.debug(f"HF cache check failed for {self.repo_id} / {filename}: {e}")

        # Fallback: check direct path (for models downloaded with local_dir=)
        direct = os.path.join(self.local_dir, filename)
        if os.path.exists(direct):
            return direct
        return None


# ------------------------------------------------------------------ #
# Model Registry — single source of truth for all AI model deps
# ------------------------------------------------------------------ #

def _hf_cache_dir() -> str:
    """Default Hugging Face cache directory."""
    return os.environ.get("HF_HOME",
        os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"))


def _insightface_dir() -> str:
    """InsightFace default model root."""
    return os.environ.get("INSIGHTFACE_HOME",
        os.path.join(os.path.expanduser("~"), ".insightface", "models", "buffalo_l"))


def _joytag_dir() -> str:
    return str(Path("data/models/joytag").resolve())


# The canonical list of all models used by the application.
MODEL_REGISTRY: List[ModelInfo] = [
    ModelInfo(
        name="CLIP ViT-L-14 (laion2b)",
        key="clip_vit_l14",
        source="open_clip",
        repo_id="laion/CLIP-ViT-L-14-laion2B-s32B-b82K",
        files=["open_clip_pytorch_model.bin"],
        estimated_size_mb=900,
        local_dir=_hf_cache_dir(),   # open_clip downloads to HF cache
    ),
    ModelInfo(
        name="InsightFace buffalo_l",
        key="insightface_buffalo_l",
        source="insightface",
        repo_id="buffalo_l",
        files=["1k3d68.onnx", "2d106det.onnx", "det_10g.onnx",
               "genderage.onnx", "w600k_r50.onnx"],
        estimated_size_mb=330,
        local_dir=_insightface_dir(),
    ),
    ModelInfo(
        name="Florence-2-base (VLM)",
        key="florence2_base",
        source="huggingface",
        repo_id="microsoft/Florence-2-base",
        files=["model.safetensors", "tokenizer.json"],
        estimated_size_mb=460,
        local_dir=_hf_cache_dir(),
    ),
    ModelInfo(
        name="JoyTag ONNX Tagger",
        key="joytag",
        source="huggingface",
        repo_id="fancyfeast/joytag",
        files=["model.onnx", "top_tags.txt"],
        estimated_size_mb=350,
        local_dir=_joytag_dir(),
    ),
    ModelInfo(
        name="Whisper base (ctranslate2)",
        key="whisper_base",
        source="huggingface",
        repo_id="guillaumekln/faster-whisper-base",
        files=["model.bin", "vocabulary.txt"],
        estimated_size_mb=150,
        local_dir=_hf_cache_dir(),
    ),
]


# ------------------------------------------------------------------ #
# Download Progress Tracking
# ------------------------------------------------------------------ #

@dataclass
class DownloadProgress:
    """Tracks a single in-flight download."""
    model_key: str
    filename: str
    downloaded_bytes: int = 0
    total_bytes: int = 0
    status: str = "pending"   # pending, downloading, completed, failed
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0

    @property
    def percent(self) -> float:
        if self.total_bytes <= 0:
            return 0.0
        return min((self.downloaded_bytes / self.total_bytes) * 100, 100.0)


class ModelManager:
    """
    Provides status and download management for all AI models.

    Usage:
        mm = ModelManager()
        statuses = mm.get_all_status()
        # Trigger download if missing:
        mm.ensure_model("joytag")
    """

    def __init__(self, custom_model_dir: Optional[str] = None):
        """
        Args:
            custom_model_dir: If set, overrides the default local_dir for
                              all models (useful for user-configurable storage).
        """
        self._custom_dir = custom_model_dir
        self._progress: Dict[str, DownloadProgress] = {}
        self._lock = threading.Lock()

    def get_all_status(self) -> List[Dict[str, Any]]:
        """Return status for every registered model."""
        results = []
        for m in MODEL_REGISTRY:
            local_dir = self._resolve_dir(m)
            info = ModelInfo(
                name=m.name, key=m.key, source=m.source,
                repo_id=m.repo_id, files=m.files,
                estimated_size_mb=m.estimated_size_mb,
                local_dir=local_dir
            )
            results.append({
                "key": info.key,
                "name": info.name,
                "source": info.source,
                "repo_id": info.repo_id,
                "is_downloaded": info.is_downloaded,
                "local_size_mb": info.local_size_mb,
                "estimated_size_mb": info.estimated_size_mb,
                "local_dir": info.local_dir,
            })
        return results

    def get_model_status(self, key: str) -> Optional[Dict[str, Any]]:
        """Return status for a single model by key."""
        for s in self.get_all_status():
            if s["key"] == key:
                return s
        return None

    def get_download_progress(self, key: str) -> Optional[Dict[str, Any]]:
        """Get the current download progress, if any."""
        with self._lock:
            prog = self._progress.get(key)
            if not prog:
                return None
            return {
                "model_key": prog.model_key,
                "filename": prog.filename,
                "downloaded_bytes": prog.downloaded_bytes,
                "total_bytes": prog.total_bytes,
                "percent": prog.percent,
                "status": prog.status,
                "error": prog.error,
            }

    def ensure_model(self, key: str) -> bool:
        """
        Download a model if not already present.
        This is a BLOCKING call. For async usage, run in a thread.
        Returns True if model is available after call.
        """
        model = self._find_model(key)
        if not model:
            return False

        local_dir = self._resolve_dir(model)
        info = ModelInfo(
            name=model.name, key=model.key, source=model.source,
            repo_id=model.repo_id, files=model.files,
            estimated_size_mb=model.estimated_size_mb,
            local_dir=local_dir
        )

        if info.is_downloaded:
            return True

        # Source-specific download logic
        if model.source == "huggingface":
            return self._download_hf(model, local_dir)
        elif model.source == "insightface":
            # InsightFace auto-downloads on FaceAnalysis init — just return status
            return info.is_downloaded
        elif model.source == "open_clip":
            # open_clip auto-downloads on create_model_and_transforms — return status
            return info.is_downloaded
        return False

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _find_model(self, key: str) -> Optional[ModelInfo]:
        for m in MODEL_REGISTRY:
            if m.key == key:
                return m
        return None

    def _resolve_dir(self, model: ModelInfo) -> str:
        if self._custom_dir and model.source != "insightface":
            return os.path.join(self._custom_dir, model.key)
        return model.local_dir

    def _download_hf(self, model: ModelInfo, local_dir: str) -> bool:
        """Download from Hugging Face Hub with progress tracking."""
        try:
            from huggingface_hub import hf_hub_download

            os.makedirs(local_dir, exist_ok=True)

            for filename in model.files:
                dest = os.path.join(local_dir, filename)
                if os.path.exists(dest):
                    continue

                prog = DownloadProgress(
                    model_key=model.key,
                    filename=filename,
                    status="downloading",
                    started_at=time.time(),
                )
                with self._lock:
                    self._progress[model.key] = prog

                try:
                    hf_hub_download(
                        repo_id=model.repo_id,
                        filename=filename,
                        local_dir=local_dir,
                    )
                    prog.status = "completed"
                    prog.completed_at = time.time()
                except Exception as e:
                    prog.status = "failed"
                    prog.error = str(e)
                    return False

            return True

        except ImportError:
            logger.error("huggingface_hub not installed — cannot download models.")
            return False
