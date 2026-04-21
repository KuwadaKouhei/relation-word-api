"""chiVe KeyedVectors から hnswlib の ANN インデックスを構築する。

実行:
    py scripts/build_ann_index.py

出力:
    models/chive-1.3-mc5_gensim/chive-1.3-mc5.ann.bin
    models/chive-1.3-mc5_gensim/chive-1.3-mc5.labels.npy
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import hnswlib
import numpy as np
from gensim.models import KeyedVectors


def _pick_models_dir() -> Path:
    """Return models dir. /models (container) if exists, else repo ./models."""
    container = Path("/models")
    if container.is_dir():
        return container
    return Path(__file__).resolve().parent.parent / "models"


MODELS_DIR = Path(os.environ.get("MODELS_DIR") or _pick_models_dir())
KV_PATH = Path(os.environ.get("KV_PATH") or MODELS_DIR / "chive-1.3-mc5_gensim" / "chive-1.3-mc5.kv")
INDEX_PATH = Path(
    os.environ.get("INDEX_PATH")
    or MODELS_DIR / "chive-1.3-mc5_gensim" / "chive-1.3-mc5.ann.bin"
)
LABELS_PATH = Path(
    os.environ.get("LABELS_PATH")
    or MODELS_DIR / "chive-1.3-mc5_gensim" / "chive-1.3-mc5.labels.npy"
)

EF_CONSTRUCTION = 200
M = 16


def main() -> None:
    print(f"[1/4] loading {KV_PATH}")
    kv = KeyedVectors.load(str(KV_PATH), mmap="r")
    n, dim = kv.vectors.shape
    print(f"     vocab={n:,}, dim={dim}")

    print(f"[2/4] building index (M={M}, ef_construction={EF_CONSTRUCTION})")
    idx = hnswlib.Index(space="cosine", dim=dim)
    idx.init_index(max_elements=n, ef_construction=EF_CONSTRUCTION, M=M)

    t0 = time.time()
    batch = 50_000
    for start in range(0, n, batch):
        end = min(start + batch, n)
        idx.add_items(kv.vectors[start:end], np.arange(start, end))
        pct = end / n * 100
        print(f"     {end:>9,}/{n:,} ({pct:5.1f}%) elapsed={time.time()-t0:.0f}s", flush=True)
    idx.set_ef(64)

    print(f"[3/4] saving index to {INDEX_PATH}")
    idx.save_index(str(INDEX_PATH))

    print(f"[4/4] saving labels to {LABELS_PATH}")
    labels = np.array(kv.index_to_key, dtype=object)
    np.save(str(LABELS_PATH), labels, allow_pickle=True)
    print("done.")


if __name__ == "__main__":
    main()
