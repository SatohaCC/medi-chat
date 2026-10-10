"""TypeSafe SDKと意図判定契約を接続するadapter。"""

import asyncio
import logging
import os

import typesafe_sdk as ts
from package_inserts.catalog_loader import get_package_insert_catalog
from package_inserts.catalog_models import PackageInsertCatalog

from ...application.retrieval.intent_contracts import IntentRequest, IntentResult
from ...domain.json_types import JsonValue
from .jev_intent_mapping import map_jev_intent_result

logger = logging.getLogger(__name__)


class JevIntentClassifier:
    """Jevによる意図判定adapter。"""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        catalog: PackageInsertCatalog | None = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("TYPESAFE_API_KEY")
            or os.environ.get("JEV_API_KEY")
        )
        self._catalog = catalog
        self._client: ts.AsyncTypeSafeClient | None = None
        self._active_calls = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False
        if self.api_key:
            try:
                self._client = ts.AsyncTypeSafeClient(api_key=self.api_key)
            except Exception as exc:
                logger.warning("Failed to initialize TypeSafe client: %s", exc)

    @property
    def is_available(self) -> bool:
        return self._client is not None and not self._closed

    async def classify(self, request: IntentRequest) -> IntentResult:
        client = self._client
        if client is None or self._closed:
            return IntentResult(is_available=False)

        catalog = self._catalog
        if catalog is None:
            catalog = get_package_insert_catalog()
        question = ts.Choice(
            instructions=(
                "ユーザーの質問から、参照すべき医療用医薬品添付文書の項目（セクション）を判定してください。"
            ),
            criteria=catalog.build_classification_criteria(),
        )
        try:
            self._active_calls += 1
            self._idle.clear()
            response = await client.system_one(
                state={"question": request.question},
                questions={"intent": question},
            )
            payload = (
                response.model_dump() if hasattr(response, "model_dump") else response
            )
            raw_response = _json_value(payload) if isinstance(payload, dict) else None
            return map_jev_intent_result(
                raw_response if isinstance(raw_response, dict) else None
            )
        except Exception as exc:
            logger.warning("Jev classify_intent failed: %s", exc)
            return map_jev_intent_result({"error": str(exc)})
        finally:
            self._active_calls -= 1
            if not self._active_calls:
                self._idle.set()

    async def aclose(self) -> None:
        self._closed = True
        await self._idle.wait()
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()


def _json_value(value: object) -> JsonValue:
    """SDKから得たJSON情報を標準Pythonの値だけに変換する。"""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            result[key] = _json_value(item)
        return result
    raise TypeError("TypeSafe response contains a non-JSON value")
