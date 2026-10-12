"""質問対象と明示選択製品の純粋整合規則。"""

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from ..foundation.exceptions import DomainValidationError
from ..foundation.primitives.primitives import BaseString
from ..medicine.identifiers import YjCode


class ProductIdentityReason(StrEnum):
    CONFLICT = "product_identity_conflict"
    UNRESOLVED = "unresolved_counterpart"
    PAIR_REQUIRED = "pair_yj_codes_required"


@dataclass(frozen=True, slots=True)
class QuestionProductName(BaseString):
    """文法が認識した名前スロット。候補解決はapplicationが所有する。"""

    def _normalize(self, value: object) -> str:
        if not isinstance(value, str):
            raise DomainValidationError("question product name requires str")
        return value.strip()


@dataclass(frozen=True, slots=True)
class ProductQuestion:
    names: tuple[QuestionProductName, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.names, tuple)
            or len(self.names) not in (1, 2)
            or any(
                not isinstance(name, QuestionProductName) or not name.value.strip()
                for name in self.names
            )
        ):
            raise DomainValidationError(
                "product question requires one or two nonempty typed names"
            )


def recognize_product_questions(
    message: str, known_aliases: tuple[str, ...]
) -> tuple[ProductQuestion, ...]:
    normalized_chars = []
    original_positions = []
    for position, char in enumerate(message):
        for normalized_char in unicodedata.normalize("NFKC", char).casefold():
            normalized_chars.append(normalized_char)
            original_positions.append(position)
    normalized_message = "".join(normalized_chars)
    protected = set()
    for alias in known_aliases:
        normalized_alias = unicodedata.normalize("NFKC", alias).casefold()
        if not normalized_alias:
            continue
        start = normalized_message.find(normalized_alias)
        while start >= 0:
            protected.update(original_positions[start : start + len(normalized_alias)])
            start = normalized_message.find(normalized_alias, start + 1)
    clauses = []
    current = []
    quote_end = None
    blocked = False
    pairs = {"「": "」", "『": "』", "“": "”", '"': '"'}
    for index, char in enumerate(message):
        if quote_end:
            if char == quote_end:
                quote_end = None
            continue
        if char in pairs and index not in protected:
            quote_end = pairs[char]
            blocked = True
            continue
        if char in "。\n":
            if not blocked:
                clauses.append("".join(current))
            current = []
            blocked = False
        else:
            current.append(char)
    if not blocked and quote_end is None:
        clauses.append("".join(current))
    questions = []
    for clause in clauses:
        text = clause.strip().rstrip("？?").strip()
        if text.startswith(("背景：", "記録：", "過去：", "以前、", "例：")):
            continue
        pair = re.fullmatch(
            r"([^と]+)と([^と]+)の(?:飲み合わせ|併用)(?:を教えてください|を教えて|は可能ですか|は)?",
            text,
        )
        if pair and all(part.strip() for part in (pair[1], pair[2])):
            questions.append(
                ProductQuestion(
                    (
                        QuestionProductName(pair[1].strip()),
                        QuestionProductName(pair[2].strip()),
                    )
                )
            )
            continue
        match = re.fullmatch(
            r"([^と]+?)の(?:効能効果|効能|効果|副作用|飲み合わせ|併用)(?:は何ですか|を教えてください|を教えて|は)?",
            text,
        )
        if match is None:
            match = re.fullmatch(r"([^と]+?)は何に効く", text)
        if match and match[1].strip():
            questions.append(ProductQuestion((QuestionProductName(match[1].strip()),)))
    return tuple(questions)


def product_identity_reason(
    questions: tuple[tuple[frozenset[YjCode], ...], ...], selected: frozenset[YjCode]
) -> ProductIdentityReason | None:
    if any(
        len(question) == 1 and question[0] and not question[0] & selected
        for question in questions
    ):
        return ProductIdentityReason.CONFLICT
    if any(
        len(question) == 2 and any(not codes for codes in question)
        for question in questions
    ):
        return ProductIdentityReason.UNRESOLVED
    if any(
        len(question) == 2 and any(not codes & selected for codes in question)
        for question in questions
    ):
        return ProductIdentityReason.PAIR_REQUIRED
    return None
