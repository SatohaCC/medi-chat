"""TC124–129: 承認済み質問文法と純粋選択規則。"""

import pytest
from backend.domain.medicine.identifiers import YjCode
from backend.domain.retrieval.product_identity import (
    ProductIdentityReason,
    product_identity_reason,
    recognize_product_questions,
)

X = frozenset({YjCode("3339003F5020")})
A = frozenset({YjCode("3961008F1022")})


@pytest.mark.parametrize(
    "message",
    [
        "アマリールの効能は？",
        " アマリールは何に効く? ",
        "アマリールの副作用を教えてください",
    ],
)
def test_tc124_direct_conflict(message):
    questions = recognize_product_questions(message, ("アマリール",))
    assert tuple(tuple(n.value for n in q.names) for q in questions) == (
        ("アマリール",),
    )
    assert product_identity_reason(((A,),), X) == ProductIdentityReason.CONFLICT
    assert product_identity_reason(((A,),), A) is None


ITRA = frozenset({YjCode("6290004M1029"), YjCode("6290004M1070")})


@pytest.mark.parametrize(
    "message,names",
    [
        (
            "イグザレルトとイトラコナゾールの飲み合わせ",
            ("イグザレルト", "イトラコナゾール"),
        ),
        (
            "イトラコナゾールとイグザレルトの併用は可能ですか",
            ("イトラコナゾール", "イグザレルト"),
        ),
    ],
)
def test_tc125_known_pair_missing(message, names):
    assert tuple(
        tuple(n.value for n in q.names)
        for q in recognize_product_questions(message, ())
    ) == (names,)
    assert (
        product_identity_reason(((X, ITRA),), X) == ProductIdentityReason.PAIR_REQUIRED
    )
    assert (
        product_identity_reason(((ITRA, X),), X) == ProductIdentityReason.PAIR_REQUIRED
    )


def test_tc126_unknown_counterpart():
    assert tuple(
        tuple(n.value for n in q.names)
        for q in recognize_product_questions(
            "イグザレルトと未知薬の併用は可能ですか", ()
        )
    ) == (("イグザレルト", "未知薬"),)
    assert (
        product_identity_reason(((X, frozenset()),), X)
        == ProductIdentityReason.UNRESOLVED
    )


@pytest.mark.parametrize(
    "message,expected",
    [
        ("「アマリールの効能」", ()),
        ("『イグザレルトと未知薬の併用』", ()),
        ("“アマリールの効能”", ()),
        ('"アマリールの効能"', ()),
        ("背景：アマリールの効能", ()),
        ("記録：アマリールの効能。イグザレルトの副作用を教えて", (("イグザレルト",),)),
        ("過去：アマリールの効能", ()),
        ("以前、アマリールの効能", ()),
        ("例：アマリールの効能", ()),
        ("イグザレルトと未知薬は併用しない", ()),
        ("アマリールの効能ではなく", ()),
        ("イグザレルトと未知薬の併用ではない", ()),
        ("イグザレルトと未知薬を一緒に飲む", ()),
        ("AとBとCの併用", ()),
        ("「アマリールの効能", ()),
        ("アマ「引用」リールの効能", ()),
        (
            "イトラコナゾールカプセル５０ｍｇ「ＳＷ」の効能",
            (("イトラコナゾールカプセル５０ｍｇ「ＳＷ」",),),
        ),
        ("「アマリールの効能。副作用」\nイグザレルトの副作用？", (("イグザレルト",),)),
    ],
)
def test_tc127_fixed_grammar_and_exclusions(message, expected):
    aliases = ("アマリール", "イグザレルト", "イトラコナゾールカプセル５０ｍｇ「ＳＷ」")
    assert (
        tuple(
            tuple(n.value for n in q.names)
            for q in recognize_product_questions(message, aliases)
        )
        == expected
    )


@pytest.mark.parametrize(
    "questions,expected",
    [
        (((A,), (X, frozenset())), ProductIdentityReason.CONFLICT),
        (((X, frozenset()), (X, ITRA)), ProductIdentityReason.UNRESOLVED),
        (((X, ITRA), (X, frozenset())), ProductIdentityReason.UNRESOLVED),
    ],
)
def test_tc128_priority_independent_of_clause_order(questions, expected):
    assert product_identity_reason(questions, X) == expected


@pytest.mark.parametrize(
    "selected",
    [
        X | frozenset({YjCode("6290004M1029")}),
        X | frozenset({YjCode("6290004M1070")}),
        X | ITRA,
    ],
)
def test_tc129_generic_slot_any_alternative_suffices(selected):
    assert product_identity_reason(((X, ITRA),), selected) is None


def test_tc129_specific_brand_is_not_an_alternative():
    specific = frozenset({YjCode("6290004M1029")})
    assert (
        product_identity_reason(
            ((X, specific),), X | frozenset({YjCode("6290004M1070")})
        )
        == ProductIdentityReason.PAIR_REQUIRED
    )


@pytest.mark.parametrize("names", [(), ("",), ("A", "B", "C"), ["A"]])
def test_tc127_question_value_is_always_valid(names):
    from backend.domain.foundation.exceptions import DomainValidationError
    from backend.domain.retrieval.product_identity import ProductQuestion

    with pytest.raises(DomainValidationError):
        ProductQuestion(names)


def test_tc127_brand_quote_protection_uses_existing_normalization():
    questions = recognize_product_questions(
        "イトラコナゾールカプセル50mg「SW」の効能",
        ("イトラコナゾールカプセル５０ｍｇ「ＳＷ」",),
    )
    assert tuple(tuple(n.value for n in q.names) for q in questions) == (
        ("イトラコナゾールカプセル50mg「SW」",),
    )
