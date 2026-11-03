"""Map retrieval output without changing its evidence or clinical metadata."""

from backend.application.chat.interfaces.medical_tool import ToolExecutionResult
from backend.application.retrieval.queries.models import RetrievalResult


def package_insert_tool_result(
    name: str, result: RetrievalResult
) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool_name=name,
        sources=result.sources,
        intent=result.intent,
        resolved_medicines=result.resolved_medicines,
        needs_clarification=result.needs_clarification,
        notices=result.notices,
        qualifying_intents=result.qualifying_intents,
        jev_response=result.jev_response,
    )
