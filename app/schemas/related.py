from pydantic import BaseModel, Field, model_validator


class RelatedItem(BaseModel):
    word: str
    score: float
    pos: str | None = None


class Meta(BaseModel):
    model: str
    cached: bool
    elapsed_ms: int


class RelatedResponse(BaseModel):
    query: str
    results: list[RelatedItem]
    meta: Meta


class BatchItem(BaseModel):
    word: str


class BatchRequest(BaseModel):
    items: list[BatchItem] = Field(..., max_length=50)
    top_k: int = 10
    min_score: float = 0.5
    pos: str | None = None
    use_stopwords: bool = True


class BatchEntry(BaseModel):
    query: str
    results: list[RelatedItem]
    error: str | None = None


class BatchResponse(BaseModel):
    entries: list[BatchEntry]


class SimilarityResponse(BaseModel):
    word1: str
    word2: str
    score: float


class AnalogyRequest(BaseModel):
    positive: list[str] = Field(..., min_length=1, max_length=5)
    negative: list[str] = Field(default_factory=list, max_length=5)
    top_k: int = 10
    min_score: float = 0.5


class AnalogyResponse(BaseModel):
    positive: list[str]
    negative: list[str]
    results: list[RelatedItem]
    meta: Meta


class CascadeRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=64)
    depth: int = Field(2, ge=1, le=4)
    top_k: int = Field(5, ge=1, le=20)
    top_k_per_gen: list[int] | None = Field(
        default=None,
        description="世代別件数。長さは depth と一致させる。未指定時は top_k を全世代に適用",
    )
    min_score: float = Field(0.5, ge=0.0, le=1.0)
    pos: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list, max_length=100)
    use_stopwords: bool = True
    max_nodes: int = Field(200, ge=10, le=500)

    @model_validator(mode="after")
    def _validate_top_k_per_gen(self) -> "CascadeRequest":
        if self.top_k_per_gen is not None:
            if len(self.top_k_per_gen) != self.depth:
                raise ValueError(
                    f"top_k_per_gen must have length equal to depth ({self.depth}), "
                    f"got {len(self.top_k_per_gen)}"
                )
            for i, k in enumerate(self.top_k_per_gen):
                if not (1 <= k <= 20):
                    raise ValueError(
                        f"top_k_per_gen[{i}] must be between 1 and 20, got {k}"
                    )
        return self


class CascadeNode(BaseModel):
    id: str
    word: str
    generation: int
    score: float
    parent: str | None = None


class CascadeEdge(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    score: float

    model_config = {"populate_by_name": True}


class CascadeMeta(Meta):
    truncated: bool = False
    total_nodes: int
    generations_reached: int


class CascadeResponse(BaseModel):
    query: str
    normalized: str
    depth: int
    nodes: list[CascadeNode]
    edges: list[CascadeEdge]
    meta: CascadeMeta
