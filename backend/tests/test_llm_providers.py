"""SDK境界をfakeに置き換え、通常応答・代替応答・再試行を検証する。"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, call

import pytest
from backend.application.chat.answer_stream import stream_answer
from backend.infrastructure.llm import gemini_provider, mock_response, openai_provider
from backend.infrastructure.llm.provider_factory import create_llm_provider

MESSAGES = [
    {"role": "system", "content": "[根拠 1] 記載A\n[根拠 2] 記載B"},
    {"role": "user", "content": "前の質問"},
    {"role": "assistant", "content": "前の回答"},
    {"role": "user", "content": "最新の質問"},
]


class RecordingLLMProvider:
    """純粋な会話とモデルを記録し、決めた文字列チャンクを返すport Fake。"""

    def __init__(self) -> None:
        self.calls: list[tuple[list[dict[str, str]], str | None]] = []

    async def stream_response(
        self, messages: list[dict[str, str]], model: str | None = None
    ) -> AsyncIterator[str]:
        self.calls.append((deepcopy(messages), model))
        yield "先頭"
        yield "末尾"


def install_sdk_fake(
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    outcomes: list[list[str | BaseException]],
) -> list[dict[str, Any]]:
    """通信先だけを置き換え、provider本体と共通の代替応答は実際に動かす。"""
    calls: list[dict[str, Any]] = []
    responses = iter(outcomes)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def chunks(
        values: list[str | BaseException],
    ) -> AsyncIterator[SimpleNamespace]:
        for value in values:
            if provider_name == "gemini":
                assert client.aio.aclose.await_count == 0
                assert client.close.call_count == 0
            else:
                assert client.close.await_count == 0
            if isinstance(value, BaseException):
                raise value
            if provider_name == "openai":
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content=value))]
                )
            else:
                yield SimpleNamespace(text=value)

    if provider_name == "openai":

        async def create(**kwargs: Any) -> AsyncIterator[SimpleNamespace]:
            calls.append(kwargs)
            return chunks(next(responses))

        client = SimpleNamespace(
            close=AsyncMock(),
            chat=SimpleNamespace(completions=SimpleNamespace(create=create)),
        )
        monkeypatch.setattr(openai_provider, "AsyncOpenAI", lambda **kwargs: client)
    else:

        def create_chat(**kwargs: Any) -> SimpleNamespace:
            assert client.aio.aclose.await_count == 0, "client closed before retry"
            assert client.close.call_count == 0, "sync client closed before retry"
            calls.append(kwargs)
            values = next(responses)

            async def send_message_stream(
                message: str,
            ) -> AsyncIterator[SimpleNamespace]:
                kwargs["message"] = message
                return chunks(values)

            return SimpleNamespace(send_message_stream=send_message_stream)

        client = SimpleNamespace(
            close=Mock(),
            aio=SimpleNamespace(
                aclose=AsyncMock(), chats=SimpleNamespace(create=create_chat)
            ),
        )
        monkeypatch.setattr(
            gemini_provider, "genai", SimpleNamespace(Client=lambda **kwargs: client)
        )
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["openai", "gemini"])
async def test_SDKの応答チャンクとモデル指定を維持する(
    monkeypatch: pytest.MonkeyPatch, provider_name: str
) -> None:
    calls = install_sdk_fake(monkeypatch, provider_name, [["先頭", "末尾"]])
    provider = create_llm_provider(provider_name)
    messages = deepcopy(MESSAGES)
    fake = RecordingLLMProvider()
    output = [
        chunk async for chunk in stream_answer(provider, messages, model="test-model")
    ]
    fake_output = [
        chunk async for chunk in stream_answer(fake, messages, model="test-model")
    ]
    assert output == fake_output == ["先頭", "末尾"]
    assert all(type(chunk) is str for chunk in output + fake_output)
    assert fake.calls == [(MESSAGES, "test-model")]
    assert len(calls) == 1
    assert calls[0]["model"] == "test-model"
    if provider_name == "openai":
        assert calls[0]["messages"] == MESSAGES
    else:
        assert calls[0]["message"] == "最新の質問"
        assert len(calls[0]["history"]) == 2
        assert [turn.role for turn in calls[0]["history"]] == ["user", "model"]
        assert [turn.parts[0].text for turn in calls[0]["history"]] == [
            "前の質問",
            "前の回答",
        ]
        assert calls[0]["config"].system_instruction == MESSAGES[0]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_name", "label", "api_name", "key_name"),
    [
        ("openai", "OpenAI", "OpenAI", "OPENAI_API_KEY"),
        ("gemini", "Gemini", "Google Gemini", "GEMINI_API_KEY"),
    ],
)
async def test_未設定時の代替応答は最新発言と根拠件数を維持する(
    monkeypatch: pytest.MonkeyPatch,
    provider_name: str,
    label: str,
    api_name: str,
    key_name: str,
) -> None:
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.setenv(key, "")
    monkeypatch.setattr(mock_response.asyncio, "sleep", AsyncMock())
    provider = create_llm_provider(provider_name)
    output = "".join(
        [
            chunk
            async for chunk in provider.stream_response(MESSAGES, model="test-model")
        ]
    )
    assert output == (
        f"【{label} (test-model) モック対話】\n\n"
        "（添付文書の根拠: 2件を受信）\n\n"
        "APIキーがまだ設定されていません。受信メッセージ: 「最新の質問」\n\n"
        f"`.env.local` または環境変数に `{key_name}` を設定すると、実際の{api_name} APIとリアルタイムで対話できます。"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_name", "detail", "expected"),
    [
        ("openai", "failed", "\n[OpenAI API エラー (test-model): failed]"),
        ("gemini", "failed", "\n[Gemini API エラー: failed]"),
        ("openai", "429 insufficient_quota", "クレジット残高不足エラー"),
        ("gemini", "429 RESOURCE_EXHAUSTED", "利用制限（クォータ上限）エラー"),
    ],
)
async def test_通信失敗は既存のエラー表示に変換する(
    monkeypatch: pytest.MonkeyPatch, provider_name: str, detail: str, expected: str
) -> None:
    calls = install_sdk_fake(monkeypatch, provider_name, [[RuntimeError(detail)]])
    provider = create_llm_provider(provider_name)
    output = [
        chunk async for chunk in provider.stream_response(MESSAGES, model="test-model")
    ]
    assert len(output) == 1
    if detail == "failed":
        assert output == [expected]
    else:
        assert expected in output[0]
        assert "test-model" in output[0]
        assert detail in output[0]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_Geminiの一時障害は出力前だけ再試行する(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = install_sdk_fake(
        monkeypatch, "gemini", [[RuntimeError("503 UNAVAILABLE")], ["成功"]]
    )
    sleep = AsyncMock()
    monkeypatch.setattr(gemini_provider.asyncio, "sleep", sleep)
    provider = create_llm_provider("gemini")
    output = [
        chunk async for chunk in provider.stream_response(MESSAGES, model="test-model")
    ]
    assert output == ["成功"]
    assert len(calls) == 2
    assert sleep.await_args_list == [call(1.0)]


@pytest.mark.asyncio
async def test_Geminiの一時障害が続く場合は三回で終了する(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = install_sdk_fake(
        monkeypatch, "gemini", [[RuntimeError("503 UNAVAILABLE")] for _ in range(3)]
    )
    sleep = AsyncMock()
    monkeypatch.setattr(gemini_provider.asyncio, "sleep", sleep)
    provider = create_llm_provider("gemini")
    output = [
        chunk async for chunk in provider.stream_response(MESSAGES, model="test-model")
    ]
    assert output == ["\n[Gemini API エラー: 503 UNAVAILABLE]"]
    assert len(calls) == 3
    assert sleep.await_args_list == [call(1.0), call(2.0)]


@pytest.mark.asyncio
async def test_Geminiの出力途中で失敗しても再送しない(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = install_sdk_fake(
        monkeypatch, "gemini", [["途中まで", RuntimeError("503 UNAVAILABLE")]]
    )
    sleep = AsyncMock()
    monkeypatch.setattr(gemini_provider.asyncio, "sleep", sleep)
    provider = create_llm_provider("gemini")
    output = [
        chunk async for chunk in provider.stream_response(MESSAGES, model="test-model")
    ]
    assert output == ["途中まで", "\n[Gemini API ストリームエラー: 503 UNAVAILABLE]"]
    assert len(calls) == 1
    sleep.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", ["openai", "gemini"])
async def test_キャンセルは応答テキストに変換しない(
    monkeypatch: pytest.MonkeyPatch, provider_name: str
) -> None:
    calls = install_sdk_fake(monkeypatch, provider_name, [[asyncio.CancelledError()]])
    provider = create_llm_provider(provider_name)
    with pytest.raises(asyncio.CancelledError):
        _ = [chunk async for chunk in provider.stream_response(MESSAGES)]
    assert len(calls) == 1
