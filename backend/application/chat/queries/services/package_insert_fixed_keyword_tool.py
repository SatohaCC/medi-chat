"""Resolve package-insert sections from the configured fixed clinical terms."""

import asyncio

from backend.application.chat.interfaces.medical_tool import (
    ToolExecutionInput,
    ToolExecutionResult,
)
from backend.application.chat.queries.services.package_insert_tool_result import (
    package_insert_tool_result,
)
from backend.application.retrieval.queries.policies.selection import (
    detect_fixed_keyword_criteria,
)
from backend.application.retrieval.queries.services.retrieval_session import (
    EvidenceRetrievalSession,
)


class PackageInsertFixedKeywordTool:
    name = "package_insert_fixed_keyword"
    description = "固定された医療キーワードと項目対応から電子添文の根拠を取得します。"
    is_mandatory = True

    def __init__(self, session: EvidenceRetrievalSession) -> None:
        self.session = session

    async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
        self.session.ensure_open()
        criteria = (
            ()
            if self.session.needs_clarification
            else await asyncio.to_thread(
                detect_fixed_keyword_criteria,
                input_data.message,
                self.session.intent_policy,
            )
        )
        result = await self.session.retrieve(criteria, on_sources=input_data.on_sources)
        return package_insert_tool_result(self.name, result)
