import os

import numpy as np
import pytest
from fastapi.testclient import TestClient
from gensim.models import KeyedVectors

os.environ.setdefault("API_KEYS", "test-key")
os.environ.setdefault("REDIS_URL", "memory://")
os.environ.setdefault("RATE_LIMIT_DEFAULT", "1000/minute")


def _build_kv(words: list[str], dim: int = 8, seed: int = 0) -> KeyedVectors:
    rng = np.random.default_rng(seed)
    kv = KeyedVectors(vector_size=dim)
    vectors = rng.standard_normal((len(words), dim)).astype(np.float32)
    kv.add_vectors(words, vectors)
    return kv


# Larger vocabulary so BFS cascade tests can traverse multiple generations.
_TEST_VOCAB = [
    "猫", "犬", "子猫", "鳥", "魚", "兎", "馬", "牛",
    "ペット", "動物", "毛", "尾", "鳴く", "走る", "飛ぶ",
    "家", "庭", "森", "川", "山",
]


@pytest.fixture
def client(monkeypatch):
    from app.services import embedding as embedding_module

    ja_kv = _build_kv(_TEST_VOCAB, seed=1)

    embedding_module.store._kv = ja_kv
    embedding_module.store._meta = "test-ja"

    from app.main import app

    with TestClient(app) as c:
        yield c

    embedding_module.store._kv = None
    embedding_module.store._meta = "unknown"
