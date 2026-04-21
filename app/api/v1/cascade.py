import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import require_api_key
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.related import (
    CascadeEdge,
    CascadeMeta,
    CascadeNode,
    CascadeRequest,
    CascadeResponse,
    RelatedItem,
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


def _gen_top_k(req: CascadeRequest, gen: int) -> int:
    if req.top_k_per_gen is not None:
        return req.top_k_per_gen[gen - 1]
    return req.top_k


async def _cascade_core(req: CascadeRequest) -> CascadeResponse:
    t0 = time.perf_counter()

    # Validate model availability up-front so 503 is returned before BFS.
    if store.kv is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "model_not_loaded"},
        )

    normalized = _tok().normalize(req.word).normalized or req.word

    if normalized not in store.kv.key_to_index:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "word_not_in_vocab", "word": req.word},
        )

    pos_filter = set(req.pos) if req.pos else None

    key = cache.make_key(
        "cascade:v1",
        {
            "word": normalized,
            "depth": req.depth,
            "top_k": req.top_k,
            "top_k_per_gen": req.top_k_per_gen,
            "min_score": req.min_score,
            "pos": sorted(pos_filter) if pos_filter else [],
            "exclude": sorted(req.exclude),
            "stopwords": req.use_stopwords,
            "max_nodes": req.max_nodes,
        },
    )
    cached = await cache.get(key)
    if cached is not None:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return CascadeResponse(
            query=req.word,
            normalized=normalized,
            depth=req.depth,
            nodes=[CascadeNode(**n) for n in cached["nodes"]],
            edges=[CascadeEdge(**e) for e in cached["edges"]],
            meta=CascadeMeta(
                model=cached["model"],
                cached=True,
                elapsed_ms=elapsed,
                truncated=cached["truncated"],
                total_nodes=cached["total_nodes"],
                generations_reached=cached["generations_reached"],
            ),
        )

    visited: set[str] = {normalized} | set(req.exclude)
    if req.use_stopwords:
        visited |= DEFAULT_STOPWORDS

    nodes: list[CascadeNode] = [
        CascadeNode(
            id=normalized, word=normalized, generation=0, score=1.0, parent=None
        )
    ]
    edges: list[CascadeEdge] = []
    frontier: list[str] = [normalized]
    truncated = False
    generations_reached = 0

    for gen in range(1, req.depth + 1):
        next_frontier: list[str] = []
        gen_k = _gen_top_k(req, gen)
        # multiplier to compensate for POS dropout
        fetch_k = gen_k * 3 if pos_filter else gen_k

        for parent in frontier:
            try:
                raw = most_similar(
                    parent,
                    top_k=fetch_k,
                    min_score=req.min_score,
                    exclude=visited,
                )
            except WordNotInVocab:
                continue
            except ModelNotLoaded:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"error": "model_not_loaded"},
                )

            items = [RelatedItem(word=r.word, score=r.score) for r in raw]
            items = apply_pos_filter(items, pos_filter, _tok())[:gen_k]

            for it in items:
                if it.word in visited:
                    edges.append(
                        CascadeEdge(from_=parent, to=it.word, score=it.score)
                    )
                    continue
                if len(nodes) >= req.max_nodes:
                    truncated = True
                    break
                visited.add(it.word)
                nodes.append(
                    CascadeNode(
                        id=it.word,
                        word=it.word,
                        generation=gen,
                        score=it.score,
                        parent=parent,
                    )
                )
                edges.append(
                    CascadeEdge(from_=parent, to=it.word, score=it.score)
                )
                next_frontier.append(it.word)

            if truncated:
                break

        if not next_frontier and not truncated:
            generations_reached = gen - 1 if gen > 1 else 0
            break

        generations_reached = gen

        if truncated:
            break

        frontier = next_frontier

    model_name = store.model_name

    await cache.set(
        key,
        {
            "nodes": [n.model_dump() for n in nodes],
            "edges": [e.model_dump(by_alias=True) for e in edges],
            "model": model_name,
            "truncated": truncated,
            "total_nodes": len(nodes),
            "generations_reached": generations_reached,
        },
    )
    elapsed = int((time.perf_counter() - t0) * 1000)
    return CascadeResponse(
        query=req.word,
        normalized=normalized,
        depth=req.depth,
        nodes=nodes,
        edges=edges,
        meta=CascadeMeta(
            model=model_name,
            cached=False,
            elapsed_ms=elapsed,
            truncated=truncated,
            total_nodes=len(nodes),
            generations_reached=generations_reached,
        ),
    )


@router.post(
    "/cascade",
    response_model=CascadeResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(get_settings().rate_limit_default)
async def post_cascade(
    request: Request, response: Response, payload: CascadeRequest
) -> CascadeResponse:
    return await _cascade_core(payload)
