from app.schemas.related import RelatedItem
from app.services.tokenizer import JaTokenizer


def apply_pos_filter(
    items: list[RelatedItem],
    pos_filter: set[str] | None,
    tokenizer: JaTokenizer,
) -> list[RelatedItem]:
    """単語の品詞を Sudachi で判定し、pos_filter に含まれる品詞のみ残す。

    pos_filter が空/None の場合は items をそのまま返す。
    残す単語には判定した品詞を `pos` フィールドに書き込む。
    """
    if not pos_filter:
        return items
    kept: list[RelatedItem] = []
    for it in items:
        p = tokenizer.pos_of(it.word)
        if p in pos_filter:
            kept.append(RelatedItem(word=it.word, score=it.score, pos=p))
    return kept
