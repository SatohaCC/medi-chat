"""Search package-insert text using morphology while excluding product names."""

import asyncio

from backend.application.chat.interfaces.medical_tool import (
    ToolExecutionInput,
    ToolExecutionResult,
)
from backend.application.chat.queries.services.package_insert_tool_result import (
    package_insert_tool_result,
)
from backend.application.retrieval.interfaces.keyword_extractor import KeywordExtractor
from backend.application.retrieval.queries.services.keyword_detection import (
    detect_morphology_criteria,
)
from backend.application.retrieval.queries.services.retrieval_session import (
    EvidenceRetrievalSession,
)


class PackageInsertMorphologyTool:
    name = "package_insert_morphology"
    description = (
        "医薬品名を除いた質問の形態素解析キーワードで電子添文を全文検索します。"
    )
    is_mandatory = True

    def __init__(
        self, session: EvidenceRetrievalSession, extractor: KeywordExtractor
    ) -> None:
        self.session = session
        self.extractor = extractor

    async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
        self.session.ensure_open()
        condition = (
            None
            if self.session.needs_clarification
            else await asyncio.to_thread(
                detect_morphology_criteria,
                self.extractor,
                input_data.message,
                self.session.excluded_terms,
            )
        )
        result = await self.session.retrieve(
            (condition,) if condition is not None else (),
            on_sources=input_data.on_sources,
        )
        return package_insert_tool_result(self.name, result)
