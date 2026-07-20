from __future__ import annotations

from collections.abc import Callable
import hashlib
import math
import re
from typing import Any

_MODEL_CACHE: dict[tuple[str, str, int], Any] = {}


class EmbeddingClient:
    """Deterministic local embedding client used when no external provider is configured."""

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        return self._normalize(vector)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class LocalBGEEmbeddingClient:
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-zh-v1.5",
        device: str = "cuda",
        batch_size: int = 2,
        max_length: int = 1024,
        model_loader: Callable[[str, str], Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self._uses_default_loader = model_loader is None
        self._model_loader = model_loader or self._load_transformers_model
        self._model: Any | None = None

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=False,
            show_progress_bar=False,
        )
        return [list(vector) for vector in vectors]

    def _get_model(self):
        if self._model is None:
            cache_key = (self.model_name, self.device, self.max_length)
            if self._uses_default_loader and cache_key in _MODEL_CACHE:
                self._model = _MODEL_CACHE[cache_key]
                return self._model
            self._model = self._model_loader(self.model_name, self.device)
            if self.max_length:
                max_supported = getattr(self._model, "max_supported_seq_length", None)
                self._model.max_seq_length = (
                    min(self.max_length, max_supported) if max_supported else self.max_length
                )
            if self._uses_default_loader:
                _MODEL_CACHE[cache_key] = self._model
        return self._model

    def _load_transformers_model(self, model_name: str, device: str):
        try:
            import torch
            import torch.nn.functional as functional
            from transformers import AutoModel, AutoTokenizer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "transformers and torch are required for EMBEDDING_PROVIDER=local. "
                "Install project dependencies with `pip install -e .[dev]`."
            ) from exc

        resolved_device = device
        if device == "cuda" and not torch.cuda.is_available():
            resolved_device = "cpu"

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name).to(resolved_device)
        model.eval()
        max_supported_seq_length = int(getattr(model.config, "max_position_embeddings", 512))

        class TransformersEmbeddingModel:
            def __init__(self) -> None:
                self.max_supported_seq_length = max_supported_seq_length
                self.max_seq_length = max_supported_seq_length

            def encode(
                self,
                texts: list[str],
                *,
                batch_size: int,
                normalize_embeddings: bool,
                convert_to_numpy: bool,
                show_progress_bar: bool,
            ) -> list[list[float]]:
                del convert_to_numpy, show_progress_bar
                vectors: list[list[float]] = []
                for start in range(0, len(texts), batch_size):
                    batch = texts[start : start + batch_size]
                    encoded = tokenizer(
                        batch,
                        padding=True,
                        truncation=True,
                        max_length=self.max_seq_length,
                        return_tensors="pt",
                    )
                    encoded = {key: value.to(resolved_device) for key, value in encoded.items()}
                    with torch.no_grad():
                        output = model(**encoded)
                    embeddings = output.last_hidden_state[:, 0]
                    if normalize_embeddings:
                        embeddings = functional.normalize(embeddings, p=2, dim=1)
                    vectors.extend(embeddings.cpu().tolist())
                return vectors

        return TransformersEmbeddingModel()


def build_embedding_client(
    *,
    provider: str,
    dimension: int,
    model_name: str = "",
    device: str = "cuda",
    batch_size: int = 2,
    max_length: int = 1024,
):
    if provider == "local":
        return LocalBGEEmbeddingClient(
            model_name=model_name or "BAAI/bge-small-zh-v1.5",
            device=device,
            batch_size=batch_size,
            max_length=max_length,
        )
    return EmbeddingClient(dimension=dimension)
