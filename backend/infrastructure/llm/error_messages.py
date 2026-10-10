"""LLM通信の失敗を、既存のチャット表示文に変換する。"""

from __future__ import annotations

from .provider_errors import LLMRequestError


def format_llm_error(error: LLMRequestError) -> str:
    detail = str(error)
    if error.provider_name == "openai":
        if "insufficient_quota" in detail or "credit_balance_exhausted" in detail:
            return (
                "\n⚠️ **OpenAI API クレジット残高不足エラー（429 insufficient_quota）**\n\n"
                "設定された OpenAI API キーのクレジット残高が切れています（0円）。\n\n"
                f"モデル: `{error.model}`\n\n"
                "ご利用を再開するには、OpenAI 課金設定からクレジットを追加してください:\n"
                "https://platform.openai.com/settings/organization/billing\n\n"
                f"詳細: {detail}"
            )
        return f"\n[OpenAI API エラー ({error.model}): {detail}]"
    if error.stream_started:
        return f"\n[Gemini API ストリームエラー: {detail}]"
    if "429" in detail or "RESOURCE_EXHAUSTED" in detail:
        return (
            "\n⚠️ **Google Gemini API 利用制限（クォータ上限）エラー**\n\n"
            f"`{error.model}` の無料枠リクエスト制限（1日あたり20リクエストの上限）に達しました。\n\n"
            "Google AI Studio の利用制限によるものです。制限が解除されるまでしばらくお待ちいただくか、従量課金設定をご確認ください。\n\n"
            f"詳細: {detail}"
        )
    return f"\n[Gemini API エラー: {detail}]"
