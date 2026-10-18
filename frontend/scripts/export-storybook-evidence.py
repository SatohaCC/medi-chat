"""Export current registered evidence using the production evidence/API mappers.

Run from the project root:
backend/.venv/Scripts/python.exe frontend/scripts/export-storybook-evidence.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.config.database_settings import resolve_database_settings
from backend.config.runtime_environment import load_runtime_environment
from backend.infrastructure.evidence_mapping import build_evidence
from backend.infrastructure.persistence.registration_reader import (
    read_registered_snapshot,
)
from backend.presentation.chat_dto_mapper import evidence_to_api


def main() -> None:
    load_runtime_environment()
    settings = resolve_database_settings()
    snapshot = read_registered_snapshot(settings.index_path)
    if snapshot is None:
        raise ValueError("Current registered data is required")
    documents = {
        document.document_id: document.payload for document in snapshot.documents
    }
    evidence = [
        evidence_to_api(
            build_evidence(unit.payload, documents[unit.document_id], "logic")
        ).model_dump(mode="json")
        for unit in snapshot.units
    ]
    evidence.sort(key=lambda item: (item["document_id"], int(item["section"]["code"])))
    prefixes = {"metgluco": "400093_", "xarelto": "630004_", "calonal": "172190_"}
    groups = {
        name: [item for item in evidence if item["document_id"].startswith(prefix)]
        for name, prefix in prefixes.items()
    }
    keys = {
        1: "warning",
        2: "contraindication",
        3: "composition_property",
        4: "indications",
        5: "indications_precautions",
        6: "dosage",
        7: "dosage_precautions",
        8: "important_precautions",
        9: "specific_populations",
        10: "interactions",
        11: "adverse_reactions",
        13: "overdosage",
        14: "precautions_concerning_use",
        15: "other_precautions",
        16: "pharmacokinetics",
        17: "clinical_studies",
        18: "pharmacology",
        19: "physicochemical",
        20: "handling",
        21: "approval_conditions",
        22: "packaging",
        23: "references",
        24: "inquiries",
        26: "manufacturer",
    }
    examples = {}
    for code, name in keys.items():
        candidates = [
            item
            for item in groups["metgluco"] + evidence
            if item["section"]["code"] == str(code)
        ]
        if not candidates:
            raise ValueError(f"No actual source for section {code}")
        examples[f"section{code}_{name}"] = candidates[0]
    interactions = {
        name: next(item for item in items if item["section"]["code"] == "10")
        for name, items in groups.items()
    }
    exports = {
        "packageInsertMockData": ("Record<string, SourceItem>", examples),
        "realMetglucoEvidence": ("SourceItem[]", groups["metgluco"]),
        "realXareltoEvidence": ("SourceItem[]", groups["xarelto"]),
        "realCalonalEvidence": ("SourceItem[]", groups["calonal"]),
        "realInteractions": ("Record<string, SourceItem>", interactions),
    }
    content = (
        "// Generated from the configured current registration database. Do not edit.\n"
        "// Run: backend/.venv/Scripts/python.exe frontend/scripts/export-storybook-evidence.py\n"
        'import type { SourceItem } from "../model/chat";\n\n'
    )
    for name, (annotation, value) in exports.items():
        content += f"export const {name}: {annotation} = {json.dumps(value, ensure_ascii=False, indent=2)};\n\n"
    target = ROOT / "frontend/features/chat/stories/packageInsertData.ts"
    target.write_text(content, encoding="utf-8")
    print(
        f"Exported {len(examples)} section examples and {sum(map(len, groups.values()))} document units"
    )


if __name__ == "__main__":
    main()
