from dataclasses import dataclass

from app.services.ann import index as ann_index
from app.services.embedding import store


class WordNotInVocab(Exception):
    pass


class ModelNotLoaded(Exception):
    pass


@dataclass(frozen=True)
class RelatedWord:
    word: str
    score: float


def most_similar(
    word: str,
    top_k: int,
    min_score: float,
    exclude: set[str] | None = None,
) -> list[RelatedWord]:
    kv = store.kv
    if kv is None:
        raise ModelNotLoaded("embedding model is not loaded")
    if word not in kv.key_to_index:
        raise WordNotInVocab(word)

    exclude_set = {word} | (exclude or set())
    raw: list[tuple[str, float]]
    # extra margin because we filter some out afterwards
    fetch_k = top_k + len(exclude_set)

    if ann_index.available:
        vector = kv[word]
        raw = ann_index.query(vector, k=fetch_k)
    else:
        raw = kv.most_similar(word, topn=fetch_k)

    results: list[RelatedWord] = []
    for w, score in raw:
        if w in exclude_set:
            continue
        if score < min_score:
            continue
        results.append(RelatedWord(word=w, score=float(score)))
        if len(results) >= top_k:
            break
    return results


def analogy(
    positive: list[str],
    negative: list[str],
    top_k: int,
    min_score: float,
) -> list[RelatedWord]:
    kv = store.kv
    if kv is None:
        raise ModelNotLoaded("embedding model is not loaded")
    for w in [*positive, *negative]:
        if w not in kv.key_to_index:
            raise WordNotInVocab(w)

    exclude = set(positive) | set(negative)
    raw = kv.most_similar(positive=positive, negative=negative, topn=top_k + len(exclude))
    results: list[RelatedWord] = []
    for w, score in raw:
        if w in exclude:
            continue
        if score < min_score:
            continue
        results.append(RelatedWord(word=w, score=float(score)))
        if len(results) >= top_k:
            break
    return results


def cosine_similarity(word1: str, word2: str) -> float:
    kv = store.kv
    if kv is None:
        raise ModelNotLoaded("embedding model is not loaded")
    if word1 not in kv.key_to_index:
        raise WordNotInVocab(word1)
    if word2 not in kv.key_to_index:
        raise WordNotInVocab(word2)
    return float(kv.similarity(word1, word2))
