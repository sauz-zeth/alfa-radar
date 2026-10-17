import re
from collections.abc import Iterable, Mapping, Sequence

from pymorphy3 import MorphAnalyzer

_WORD_PATTERN = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


class LemmaIndex:
    def __init__(self) -> None:
        self._morph = MorphAnalyzer()

    def lemmas(self, text: str) -> list[str]:
        words = _WORD_PATTERN.findall(text.lower())
        return [self._morph.parse(word)[0].normal_form for word in words]

    def find_aliases(
        self,
        text_lemmas: Sequence[str],
        aliases_by_entity: Mapping[str, Iterable[str]],
    ) -> list[str]:
        matched: list[str] = []
        for entity, aliases in aliases_by_entity.items():
            for alias in aliases:
                alias_lemmas = self.lemmas(alias)
                if alias_lemmas and _contains_sequence(text_lemmas, alias_lemmas):
                    matched.append(entity)
                    break
        return matched


def _contains_sequence(text: Sequence[str], part: Sequence[str]) -> bool:
    size = len(part)
    if size == 0 or size > len(text):
        return False
    return any(
        list(text[index : index + size]) == list(part) for index in range(len(text) - size + 1)
    )
