"""Offline sentence-transformer embeddings for semantic capability grouping."""

from __future__ import annotations

from functools import lru_cache

import numpy as np


class EmbeddingConfigurationError(RuntimeError):
    """Raised when semantic grouping has no usable local model configured."""


@lru_cache(maxsize=4)
def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except (ImportError, ModuleNotFoundError) as exc:
        raise EmbeddingConfigurationError(
            "sentence-transformers is unavailable in the active interpreter; "
            "run SkillFlow with `uv run python ...` after `uv sync`"
        ) from exc
    try:
        # Evolution runs must be reproducible and must not depend on an implicit
        # Hugging Face download. The configured model must already be cached or
        # point to a local directory.
        model = SentenceTransformer(model_name, device="cpu", local_files_only=True)
    except Exception as exc:
        raise EmbeddingConfigurationError(
            f"embedding model {model_name!r} is not available locally; cache it during setup "
            "or set SKILLFLOW_EMBEDDING_MODEL to a local sentence-transformer directory"
        ) from exc
    model.eval()
    return model


def embed_texts(texts: list[str], *, model_name: str | None = None) -> np.ndarray:
    """Encode texts with a locally available, normalized sentence-transformer model."""
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    selected_model = model_name or "all-MiniLM-L6-v2"
    vectors = _load_model(selected_model).encode(
        texts,
        batch_size=16,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    result = np.asarray(vectors, dtype=np.float32)
    if result.ndim != 2 or result.shape[0] != len(texts):
        raise EmbeddingConfigurationError("Embedding model returned an invalid matrix")
    return result
