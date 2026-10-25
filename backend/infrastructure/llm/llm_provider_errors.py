"""SDKの失敗を表示形式から独立して伝える、LLM境界の例外。"""

from __future__ import annotations


class LLMUnavailableError(RuntimeError):
    def __init__(self, provider_name: str, model: str) -> None:
        self.provider_name = provider_name
        self.model = model
        super().__init__(f"{provider_name} is not configured")


class LLMRequestError(RuntimeError):
    def __init__(
        self,
        provider_name: str,
        model: str,
        cause: Exception,
        *,
        stream_started: bool = False,
    ) -> None:
        self.provider_name = provider_name
        self.model = model
        self.stream_started = stream_started
        super().__init__(str(cause))
