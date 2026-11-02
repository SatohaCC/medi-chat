"""Retrieve package-insert sections selected by the Jev intent classifier."""

from backend.application.chat.interfaces.medical_tool import (
    ToolExecutionInput,
    ToolExecutionResult,
)
from backend.application.chat.queries.services.package_insert_tool_result import (
    package_insert_tool_result,
)
from backend.application.retrieval.interfaces.intent_classifier import IntentClassifier
from backend.application.retrieval.queries.models import (
    IntentRequest,
    JevDetectionResult,
)
from backend.application.retrieval.queries.services.intent_detection import (
    detect_jev_criteria,
)
from backend.application.retrieval.queries.services.retrieval_session import (
    EvidenceRetrievalSession,
)


class PackageInsertJevTool:
    name = "package_insert_jev"
    description = "Jevの質問意図判定から電子添文の関連項目を選択して根拠を取得します。"
    is_mandatory = True

    def __init__(
        self, session: EvidenceRetrievalSession, classifier: IntentClassifier
    ) -> None:
        self.session = session
        self.classifier = classifier

    async def execute(self, input_data: ToolExecutionInput) -> ToolExecutionResult:
        self.session.ensure_open()
        detection = (
            JevDetectionResult()
            if self.session.needs_clarification
            else await detect_jev_criteria(
                self.classifier,
                IntentRequest(input_data.message),
                intent_policy=self.session.intent_policy,
            )
        )
        result = await self.session.retrieve(
            detection.search_criteria, jev=detection, on_sources=input_data.on_sources
        )
        return package_insert_tool_result(self.name, result)
