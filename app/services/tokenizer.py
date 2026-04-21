from dataclasses import dataclass

try:
    from sudachipy import dictionary as _sudachi_dict
    from sudachipy import tokenizer as _sudachi_tok
except ImportError:
    _sudachi_dict = None
    _sudachi_tok = None


@dataclass(frozen=True)
class Token:
    surface: str
    normalized: str
    pos: str | None


class JaTokenizer:
    def __init__(self) -> None:
        if _sudachi_dict is None:
            raise RuntimeError("sudachipy is not installed")
        self._tok = _sudachi_dict.Dictionary().create()
        self._mode = _sudachi_tok.Tokenizer.SplitMode.C

    def normalize(self, word: str) -> Token:
        morphs = self._tok.tokenize(word, self._mode)
        if not morphs:
            return Token(surface=word, normalized=word, pos=None)
        m = morphs[0]
        return Token(
            surface=m.surface(),
            normalized=m.normalized_form(),
            pos=m.part_of_speech()[0],
        )

    def pos_of(self, word: str) -> str | None:
        """単語の代表的な品詞 (例: 名詞, 動詞, 形容詞) を返す。"""
        morphs = self._tok.tokenize(word, self._mode)
        if not morphs:
            return None
        return morphs[0].part_of_speech()[0]
