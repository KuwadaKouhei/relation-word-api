"""hnswlib による近似最近傍検索。

インデックスファイルがあればロードして利用する。存在しない場合は None を保持し、
呼び出し側は gensim の most_similar にフォールバックする。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import hnswlib
except ImportError:
    hnswlib = None  # type: ignore[assignment]

from app.core.logging import logger


class AnnIndex:
    """hnswlib インデックスとラベル配列のペアを保持する。"""

    def __init__(self) -> None:
        self._index: "hnswlib.Index | None" = None
        self._labels: list[str] | None = None
        self._ef: int = 64

    def load(self, index_path: str | None, labels_path: str | None) -> None:
        if hnswlib is None:
            logger.warning("ann_skip_no_hnswlib")
            return
        if not index_path or not labels_path:
            logger.info("ann_skip_no_paths")
            return
        ipath = Path(index_path)
        lpath = Path(labels_path)
        if not ipath.exists() or not lpath.exists():
            logger.info("ann_skip_missing_files", index=str(ipath), labels=str(lpath))
            return

        labels = np.load(str(lpath), allow_pickle=True).tolist()
        dim = 300
        idx = hnswlib.Index(space="cosine", dim=dim)
        idx.load_index(str(ipath))
        idx.set_ef(max(self._ef, 64))
        self._index = idx
        self._labels = labels
        logger.info("ann_loaded", labels=len(labels))

    @property
    def available(self) -> bool:
        return self._index is not None and self._labels is not None

    def query(self, vector: np.ndarray, k: int) -> list[tuple[str, float]]:
        if not self.available:
            raise RuntimeError("ANN index is not loaded")
        assert self._index is not None and self._labels is not None
        ids, dists = self._index.knn_query(vector.reshape(1, -1), k=k)
        results: list[tuple[str, float]] = []
        for i, d in zip(ids[0], dists[0]):
            # cosine space: distance = 1 - similarity
            sim = float(1.0 - d)
            results.append((self._labels[int(i)], sim))
        return results


index = AnnIndex()
