"""DomainとApplicationの定義からフロント用の表示データを生成・照合する。"""

import argparse
import json

from backend.application.retrieval.queries.policies.standard import (
    DEFAULT_INTENT_POLICY,
    DEFAULT_RETRIEVAL_POLICY,
)
from backend.domain.attachment.value_objects import STANDARD_SECTION_TAXONOMY
from backend.project_paths import PROJECT_ROOT


def guide_payloads() -> dict[str, list[dict[str, object]]]:
    titles = {
        section.code.value: section.title.value
        for section in STANDARD_SECTION_TAXONOMY.sections
    }
    return {
        "logicRules.json": [
            {
                "priority": intent.keyword_priority.value,
                "keywords": [keyword.text.value for keyword in intent.keywords],
                "sections": [
                    {"code": code.value, "title": titles[code.value]}
                    for code in intent.section_codes
                ],
            }
            for intent in DEFAULT_INTENT_POLICY.keyword_intents
            if intent.keyword_priority is not None
        ],
        "alwaysSections.json": [
            {"code": code.value, "title": titles[code.value]}
            for code in DEFAULT_RETRIEVAL_POLICY.always_retrieved_sections
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = PROJECT_ROOT / "frontend" / "features" / "search-guide"
    for name, payload in guide_payloads().items():
        path = root / name
        current = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        )
        if current == payload:
            continue
        if args.check:
            raise SystemExit(f"Regenerate search guide: {name}")
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
