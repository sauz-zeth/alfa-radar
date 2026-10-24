"""Offline ML stubs for the news pipeline.

``PostClassifier`` is the seam for ruBERT categories and e5 embeddings. The stub is
deterministic and network-free: categories come from a keyword lexicon and the
embedding is a hashed bag of words. Replace ``get_classifier`` with a real model
without touching any pipeline branch.
"""

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from hashlib import blake2b
from typing import Protocol

EMBEDDING_DIM = 64
_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)

# Stems are matched as substrings against the normalized title + text.
LEXICON: dict[int, tuple[str, ...]] = {
    1: ("ключев", "ставк", "цб", "дкп", "монетарн"),
    2: ("курс", "валют", "рубл", "юан", "доллар", "евро"),
    3: ("санкц", "экспортн контроль", "комплаенс", "параллельн импорт"),
    4: ("пошлин", "тамож", "квот", "еаэс", "тариф"),
    5: ("налог", "фнс", "нк рф", "ндс", "ндфл", "прибыл"),
    6: ("фсбу", "бухуч", "отчётност", "отчетност", "аудит"),
    7: ("корпоратив", "m&a", "банкрот", "акционер", "реорганизац"),
    8: ("трудов", "тк рф", "зарплат", "кадр", "мигрант", "охрана труда"),
    9: ("господдерж", "субсиди", "грант", "льготн кредит", "промзаклад"),
    10: ("жкх", "тариф", "электроэнерг", "газ", "тепло", "коммунал"),
    11: ("госзакуп", "44-фз", "223-фз", "тендер", "нацрежим"),
    12: ("геополит", "вто", "брикс", "торговая война", "миров", "санкц"),
    13: ("инфляц", "потреб", "спрос", "розниц", "доход", "зарплат"),
    14: ("строит", "недвижим", "ипотек", "сро", "аренд"),
    15: ("металл", "сталь", "прокат", "руда", "уголь", "лом"),
    16: ("нефт", "газ", "тэк", "опек", "нефтепереработ"),
    17: ("хим", "удобрен", "полимер", "сырь"),
    18: ("апк", "урожай", "зерн", "продовольств", "сельск"),
    19: ("машиностро", "станк", "оборудован", "локализац", "промышленн"),
    20: ("логист", "перевоз", "ржд", "порт", "склад", "тариф"),
    21: ("авто", "утильсбор", "автокредит", "запчаст"),
    22: ("ритейл", "маркетплейс", "e-commerce", "торговл", "онлайн"),
    23: ("банк", "финтех", "платеж", "цифров рубл", "эквайринг", "кредитован"),
    24: ("страхов", "осаго", "каско", "выплат"),
    25: ("it", "ии", "телеком", "кибербез", "данн"),
    26: ("образован", "edtech", "обучен", "аттестац"),
    27: ("фарм", "лекарств", "здравоохран", "жнвлп", "медицин"),
    28: ("туризм", "тур", "гостиниц", "авиасообщен", "безвиз"),
    29: ("текстил", "одежд", "мебел", "маркировк", "потребтовар"),
    30: ("реклам", "медиа", "маркетинг", "продвижен", "диджитал"),
}


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("ё", "е").split())


@dataclass(frozen=True)
class Classification:
    categories: list[int]
    embedding: list[float]


class PostClassifier(Protocol):
    async def classify(self, title: str, text: str) -> Classification: ...

    def embed(self, text: str) -> list[float]: ...


class StubPostClassifier:
    provider_name = "stub"

    async def classify(self, title: str, text: str) -> Classification:
        return Classification(categories=self.categories(title, text), embedding=self.embed(text))

    def categories(self, title: str, text: str) -> list[int]:
        haystack = normalize(f"{title} {text}")
        scores: dict[int, int] = {}
        for category_id, stems in LEXICON.items():
            hits = sum(1 for stem in stems if stem in haystack)
            if hits:
                scores[category_id] = hits
        if not scores:
            return []
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [category_id for category_id, _ in ranked[:5]]

    def embed(self, text: str) -> list[float]:
        # shortcut: hashed bag-of-words is enough for the demo; swap for e5 when ML lands.
        vector = [0.0] * EMBEDDING_DIM
        for token in _TOKEN_RE.findall(normalize(text)):
            digest = blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, "big")
            index = value % EMBEDDING_DIM
            sign = 1.0 if value & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 6) for value in vector]


@lru_cache
def get_classifier() -> PostClassifier:
    return StubPostClassifier()


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    width = len(vectors[0])
    sums = [0.0] * width
    for vector in vectors:
        for index, value in enumerate(vector):
            if index < width:
                sums[index] += value
    norm = math.sqrt(sum(value * value for value in sums))
    if norm == 0:
        return sums
    return [value / norm for value in sums]
