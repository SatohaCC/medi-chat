"""純粋な回答と会話から、添付文書に基づくLLM入力を作る。"""

from collections.abc import Sequence

from backend.application.chat.queries.models import (
    AnswerPromptPolicy,
    ChatMessage,
    ChatResponse,
)
from backend.application.medicine.queries.models import ResolvedMedicine
from backend.application.retrieval.queries.models import Evidence


def _escape_attr(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_answer_system_prompt(
    sources: list[Evidence],
    resolved_medicines: list[ResolvedMedicine],
    intent: str,
    qualifying_intents: list[str] | None = None,
    *,
    answer_prompt_policy: AnswerPromptPolicy,
) -> str:
    """取得された添付文書ソース、薬剤情報、インテントに基づいてグラウンディングシステムプロンプトを構築する"""
    medicine_lines = []
    for med in resolved_medicines:
        yj = ", ".join(med.yj_codes)
        brands = ", ".join(med.brand_names)
        medicine_lines.append(
            f"- {med.generic_name} (販売名: {brands}) [YJコード: {yj}]"
        )

    grouped_docs: dict[tuple[str, str, str, str, str], list[tuple[int, Evidence]]] = {}
    for i, s in enumerate(sources, 1):
        product_name = s.product_name.value if s.product_name is not None else ""
        yj_codes = ", ".join(code.value for code in s.product_yj_codes)
        revision = (
            " / ".join(
                str(value)
                for key in ("source_label", "year_month", "version")
                if (value := s.document_revision.get(key)) not in (None, "")
            )
            or "不明"
        )
        url = s.url.value if s.url is not None else "不明"
        key = (s.document_id.value, product_name, yj_codes, revision, url)
        grouped_docs.setdefault(key, []).append((i, s))

    doc_blocks = []
    for (_, product_name, yj_codes, revision, url), items in grouped_docs.items():
        evidence_blocks = []
        for i, s in items:
            sec_code = s.section.get("code", "")
            sec_title = s.section.get("title", "")
            sec_name = f"{sec_code} {sec_title}".strip()
            details: list[str] = []
            if s.columns:
                details.extend(
                    f"{column.title}: {s.columns[column.id]}"
                    for column in answer_prompt_policy.interaction_columns
                    if s.columns.get(column.id)
                )
            if not details and s.excerpt.value:
                details.append(s.excerpt.value)
            content_text = "\n".join(details)
            if content_text:
                indented = "\n".join(
                    f"      {line}" for line in content_text.splitlines()
                )
                evidence_blocks.append(
                    f'    <evidence id="{i}" unit_id="{_escape_attr(s.unit_id.value)}" section="{_escape_attr(sec_name)}">\n'
                    f"{indented}\n"
                    f"    </evidence>"
                )
            else:
                evidence_blocks.append(
                    f'    <evidence id="{i}" unit_id="{_escape_attr(s.unit_id.value)}" section="{_escape_attr(sec_name)}" />'
                )
        evidences_text = "\n".join(evidence_blocks)
        doc_blocks.append(
            f'  <package_insert product="{_escape_attr(product_name)}" yj_code="{_escape_attr(yj_codes)}" revision="{_escape_attr(revision)}" url="{_escape_attr(url)}">\n'
            f"{evidences_text}\n"
            f"  </package_insert>"
        )

    sources_text = (
        "<provided_package_inserts>\n"
        + "\n".join(doc_blocks)
        + "\n</provided_package_inserts>"
        if doc_blocks
        else "（該当する記載は見つかりませんでした）"
    )

    multi_rule = ""
    if qualifying_intents and len(qualifying_intents) > 1:
        labels = [
            f"{answer_prompt_policy.intent_display_name(k)} ({k})"
            for k in qualifying_intents
        ]
        intent_display = f"複合項目（マルチセクション）: {' + '.join(labels)}"
        multi_rule = "6. " + answer_prompt_policy.multiple_intents_template
    else:
        label = answer_prompt_policy.intent_display_name(intent)
        intent_display = f"{label} ({intent})" if label != intent else intent

    specific_rule = ""
    guidance = answer_prompt_policy.answer_guidance_for_intent(
        intent, len(resolved_medicines)
    )
    if guidance:
        rule_num = "7" if multi_rule else "6"
        specific_rule = f"{rule_num}. {guidance}"

    return (
        "あなたは薬剤師向けの電子添文検索支援アシスタントです。\n"
        "添付文書の記載を短く整理し、検索結果と照合しやすい回答を作成してください。\n"
        "以下の【ルール】を厳格に守って回答してください。\n\n"
        "【ルール】\n"
        "1. 必ず以下の【提供された添付文書情報】に記載された内容のみを根拠として回答してください。\n"
        "2. 提供された情報に明確な記載がない内容を推測して回答してはいけません。記載がない場合は「今回取得した根拠では確認できません」と明確に回答してください。\n"
        f"3. 回答の際には、根拠となった項目名・項目番号（例: {answer_prompt_policy.citation_examples_text()} など）や医薬品名を引用してわかりやすく説明してください。\n"
        "4. 添付文書に書かれている事実と、そこから判断できない点を分けて説明してください。\n"
        "5. 回答には、使用した根拠の改訂情報と出典URLを明記してください。\n"
        + multi_rule
        + specific_rule
        + f"\n【質問種別】\n{intent_display}\n\n"
        "【対象医薬品】\n"
        + ("\n".join(medicine_lines) if medicine_lines else "（指定なし）")
        + "\n\n【提供された添付文書情報】\n"
        + sources_text
    )


def build_answer_messages(
    reply: ChatResponse,
    conversation: Sequence[ChatMessage],
    *,
    answer_prompt_policy: AnswerPromptPolicy,
) -> list[dict[str, str]]:
    """取得結果を会話履歴に反映した、LLM送信用メッセージを構築する"""
    system_prompt = build_answer_system_prompt(
        reply.sources,
        reply.resolved_medicines,
        reply.intent,
        qualifying_intents=list(reply.qualifying_intents),
        answer_prompt_policy=answer_prompt_policy,
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(
        {"role": message.role, "content": message.content}
        for message in conversation
        if message.role != "system"
    )
    return messages
