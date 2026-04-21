import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import require_api_key
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.related import AnalogyRequest, AnalogyResponse, Meta, RelatedItem
from app.services.embedding import store
from app.services.similarity import ModelNotLoaded, WordNotInVocab, analogy
from app.services.tokenizer import JaTokenizer

router = APIRouter()

_tokenizer: JaTokenizer | None = None


def _tok() -> JaTokenizer:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = JaTokenizer()
    return _tokenizer


def _norm_all(words: list[str]) -> list[str]:
    tok = _tok()
    return [tok.normalize(w).normalized or w for w in words]


@router.post(
    "/analogy",
    response_model=AnalogyResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(get_settings().rate_limit_default)
async def post_analogy(
    request: Request, response: Response, payload: AnalogyRequest
) -> AnalogyResponse:
    t0 = time.perf_counter()
    pos_words = _norm_all(payload.positive)
    neg_words = _norm_all(payload.negative)
    try:
        raw = analogy(
            positive=pos_words,
            negative=neg_words,
            top_k=payload.top_k,
            min_score=payload.min_score,
        )
    except WordNotInVocab as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "word_not_in_vocab", "word": str(e)},
        )
    except ModelNotLoaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "model_not_loaded"},
        )

    elapsed = int((time.perf_counter() - t0) * 1000)
    return AnalogyResponse(
        positive=payload.positive,
        negative=payload.negative,
        results=[RelatedItem(word=r.word, score=r.score) for r in raw],
        meta=Meta(model=store.model_name, cached=False, elapsed_ms=elapsed),
    )
