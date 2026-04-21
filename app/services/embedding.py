from pathlib import Path

from gensim.models import KeyedVectors

from app.core.logging import logger


class EmbeddingStore:
    """日本語単語埋め込み (chiVe) を保持するシングルトン。

    モデルファイルは gensim の KeyedVectors 形式 (.kv) を想定。
    """

    def __init__(self) -> None:
        self._kv: KeyedVectors | None = None
        self._meta: str = "unknown"

    def load(self, path: str | None) -> None:
        if not path:
            logger.warning("embedding_skip_no_path")
            return
        p = Path(path)
        if not p.exists():
            logger.warning("embedding_skip_missing", path=str(p))
            return
        logger.info("embedding_loading", path=str(p))
        self._kv = KeyedVectors.load(str(p), mmap="r")
        self._meta = p.stem

    @property
    def kv(self) -> KeyedVectors | None:
        return self._kv

    @property
    def model_name(self) -> str:
        return self._meta

    def is_ready(self) -> bool:
        return self._kv is not None


store = EmbeddingStore()
