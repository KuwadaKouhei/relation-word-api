import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.auth import require_api_key
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.related import (
    BatchEntry,
    BatchRequest,
    BatchResponse,
    Meta,
    RelatedItem,
    RelatedResponse,
)
from app.services import cache
from app.services.embedding import store
from app.services.filters import apply_pos_filter
from app.services.similarity import ModelNotLoaded, WordNotInVocab, most_similar
from app.services.stopwords import DEFAULT_STOPWORDS
from app.services.tokenizer import JaTokenizer

router = APIRouter()

_tokenizer: JaTokenizer | None = None


def _tok() -> JaTokenizer:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = JaTokenizer()
    return _tokenizer


def _parse_pos(pos: str | None) -> set[str] | None:
    if not pos:
        return None
    return {p.strip() for p in pos.split(",") if p.strip()}


async def _related_core(
    word: str,
    top_k: int,
    min_score: float,
    exclude: set[str] | None,
    pos_filter: set[str] | None,
    use_stopwords: bool,
) -> RelatedResponse:
    t0 = time.perf_counter()
    token = _tok().normalize(word)
    normalized = token.normalized or word

    exclude_combined: set[str] = set(exclude or set())
    if use_stopwords:
        exclude_combined |= DEFAULT_STOPWORDS

    # If POS filter is on, fetch extra candidates to compensate for drop-outs.
    fetch_k = top_k * 3 if pos_filter else top_k

    key = cache.make_key(
        "related:v1",
        {
            "word": normalized,
            "top_k": top_k,
            "min_score": min_score,
            "exclude": sorted(exclude_combined),
            "pos": sorted(pos_filter) if pos_filter else [],
            "stopwords": use_stopwords,
        },
    )
    cached = await cache.get(key)
    if cached is not None:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return RelatedResponse(
            query=word,
            results=[RelatedItem(**r) for r in cached["results"]],
            meta=Meta(model=cached["model"], cached=True, elapsed_ms=elapsed),
        )

    try:
        raw = most_similar(
            normalized, top_k=fetch_k, min_score=min_score, exclude=exclude_combined
        )
    except WordNotInVocab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "word_not_in_vocab", "word": word},
        )
    except ModelNotLoaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "model_not_loaded"},
        )

    items = [RelatedItem(word=r.word, score=r.score) for r in raw]
    items = apply_pos_filter(items, pos_filter, _tok())[:top_k]

    model_name = store.model_name
    await cache.set(key, {"results": [r.model_dump() for r in items], "model": model_name})
    elapsed = int((time.perf_counter() - t0) * 1000)
    return RelatedResponse(
        query=word,
        results=items,
        meta=Meta(model=model_name, cached=False, elapsed_ms=elapsed),
    )


@router.get("/related", response_model=RelatedResponse, dependencies=[Depends(require_api_key)])
@limiter.limit(get_settings().rate_limit_default)
async def get_related(
    request: Request,
    response: Response,
    word: str = Query(..., min_length=1, max_length=64),
    top_k: int = Query(10, ge=1, le=100),
    min_score: float = Query(0.5, ge=0.0, le=1.0),
    exclude: str | None = Query(None, description="comma-separated words to exclude"),
    pos: str | None = Query(
        None,
        description="comma-separated POS filter (例: 名詞,動詞,形容詞)",
    ),
    use_stopwords: bool = Query(True, description="apply system default stopwords"),
) -> RelatedResponse:
    exclude_set = {e.strip() for e in exclude.split(",")} if exclude else None
    return await _related_core(
        word, top_k, min_score, exclude_set, _parse_pos(pos), use_stopwords
    )


@router.post(
    "/related/batch",
    response_model=BatchResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(get_settings().rate_limit_default)
async def post_related_batch(
    request: Request, response: Response, payload: BatchRequest
) -> BatchResponse:
    if len(payload.items) > get_settings().batch_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "batch_too_large", "max": get_settings().batch_max},
        )
    entries: list[BatchEntry] = []
    pos_filter = _parse_pos(payload.pos)
    for item in payload.items:
        try:
            res = await _related_core(
                item.word,
                payload.top_k,
                payload.min_score,
                None,
                pos_filter,
                payload.use_stopwords,
            )
            entries.append(
                BatchEntry(query=res.query, results=res.results, error=None)
            )
        except HTTPException as e:
            detail = e.detail if isinstance(e.detail, dict) else {"error": str(e.detail)}
            entries.append(
                BatchEntry(
                    query=item.word,
                    results=[],
                    error=detail.get("error", "unknown"),
                )
            )
    return BatchResponse(entries=entries)
