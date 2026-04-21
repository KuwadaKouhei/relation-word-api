from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.auth import require_api_key
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.schemas.related import SimilarityResponse
from app.services.similarity import ModelNotLoaded, WordNotInVocab, cosine_similarity
from app.services.tokenizer import JaTokenizer

router = APIRouter()

_tokenizer: JaTokenizer | None = None


def _normalize(word: str) -> str:
    global _tokenizer
    if _tokenizer is None:
        _tokenizer = JaTokenizer()
    return _tokenizer.normalize(word).normalized or word


@router.get(
    "/similarity",
    response_model=SimilarityResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(get_settings().rate_limit_default)
async def get_similarity(
    request: Request,
    response: Response,
    word1: str = Query(..., min_length=1, max_length=64),
    word2: str = Query(..., min_length=1, max_length=64),
) -> SimilarityResponse:
    w1 = _normalize(word1)
    w2 = _normalize(word2)
    try:
        score = cosine_similarity(w1, w2)
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
    return SimilarityResponse(word1=word1, word2=word2, score=score)
