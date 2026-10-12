"""TC124–132/133/134: 固定全文期待、copy実REST/WS、SDK無通信。"""

import pytest
from backend.application.chat.answer_preparation import prepare_reply
from backend.application.chat.answer_question import answer_question
from backend.application.chat.chat_models import ChatMessage
from backend.application.chat.stream_reply import stream_reply
from backend.infrastructure.package_insert_definitions.loader import (
    get_package_insert_definitions,
)
from backend.tests.test_product_identity_retrieval import (
    Classifier,
    EvidenceReader,
    Keywords,
    Medicines,
    X,
)

CONFIRMATIONS = {
    "product_identity_conflict": (
        "質問の医薬品名と選択されたYJコードが一致していません。対象製品を確認し、YJコードを選択し直してください。",
        "質問の名称をもとに、選択されたYJコードを変更していません。",
    ),
    "pair_yj_codes_required": (
        "飲み合わせを確認する両方の医薬品のYJコードを選択してください。",
        "比較相手のYJコードを名称から自動補完していません。",
    ),
    "unresolved_counterpart": (
        "比較相手の医薬品を同定できません。相手の名称とYJコードを確認してください。",
        "比較相手を同定するまで、併用可否は回答できません。",
    ),
    "product_code_lookup": (
        "指定されたYJコードのすべてに対応する電子添文が、現在の検索データにありません。",
        "検索対象の構造化データに登録されているYJコードを指定してください。",
    ),
}
CASES = [
    ("アマリールの効能は？", [X], "product_identity_conflict"),
    ("イグザレルトとイトラコナゾールの飲み合わせ", [X], "pair_yj_codes_required"),
    ("イグザレルトと未知薬の併用は可能ですか", [X], "unresolved_counterpart"),
    (
        "アマリールの効能。イグザレルトと未知薬の併用",
        [X, "999999999999"],
        "product_code_lookup",
    ),
    ("アマリールの効能。イグザレルトと未知薬の併用", [X], "product_identity_conflict"),
    (
        "イグザレルトとイトラコナゾールの併用。イグザレルトと未知薬の併用",
        [X],
        "unresolved_counterpart",
    ),
]


class GenerationSpy:
    def __init__(self):
        self.factory_calls = 0
        self.stream_calls = 0

    def factory(self, name):
        self.factory_calls += 1
        return self

    async def stream_response(self, messages, model=None):
        self.stream_calls += 1
        raise AssertionError("fixed clarification cannot generate")
        yield "unreachable"


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["prepare", "answer", "stream"])
@pytest.mark.parametrize("message,codes,strategy", CASES)
async def test_fixed_reason_full_text_priority_and_generation_zero(
    entry, message, codes, strategy
):
    reader = EvidenceReader(True)
    provider = GenerationSpy()
    conversation = [
        ChatMessage("assistant", "アマリールの効能"),
        ChatMessage("user", message),
    ]

    async def prepare():
        return await prepare_reply(
            conversation,
            codes,
            medicine_reader=Medicines(),
            evidence_reader=reader,
            intent_classifier=Classifier(),
            keyword_extractor=Keywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
        )

    if entry == "answer":
        reply = await answer_question(
            conversation,
            codes,
            medicine_reader=Medicines(),
            evidence_reader=reader,
            intent_classifier=Classifier(),
            keyword_extractor=Keywords(),
            intent_policy=get_package_insert_definitions().intent_policy,
            answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
            provider_factory=provider.factory,
            provider_name=None,
            model_name=None,
        )
    else:
        reply = await prepare()
    assert reply.answer == CONFIRMATIONS[strategy][0] and reply.notices == [
        CONFIRMATIONS[strategy][1]
    ]
    assert (
        reply.retrieval_strategy == strategy
        and reply.needs_clarification
        and reply.sources == []
    )
    assert reply.intent == "interaction" and reply.jev_response == {"fixed": True}
    assert [code for m in reply.resolved_medicines for code in m.yj_codes] == [X]
    if entry == "stream":
        assert [
            chunk
            async for chunk in stream_reply(
                reply,
                conversation,
                answer_prompt_policy=get_package_insert_definitions().answer_prompt_policy,
                provider_factory=provider.factory,
                provider_name=None,
                model_name=None,
            )
        ] == [CONFIRMATIONS[strategy][0]]
    assert (
        reader.calls == []
        and provider.factory_calls == 0
        and provider.stream_calls == 0
    )
