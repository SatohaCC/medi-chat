"""Compare against a separately reviewed, immutable semantic oracle."""

import copy
import hashlib
import json
import re
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
helpers = runpy.run_path(str(ROOT / "frontend/scripts/semantic-candidate.py"))
SemanticHTML = helpers["SemanticHTML"]


def projection(payload):
    value = copy.deepcopy(payload)
    parser = SemanticHTML()
    parser.feed(value.pop("text"))
    return {"payload": value, "html_events": parser.events}


def assert_semantic(payloads, oracle):
    observed = sorted(
        payloads, key=lambda value: tuple(map(int, value["section"]["code"].split(".")))
    )
    expected = [entry["payload"] for entry in oracle["sections"]]
    assert len({value["section"]["code"] for value in observed}) == len(observed), (
        "duplicate section"
    )
    assert [projection(value) for value in observed] == [
        projection(value) for value in expected
    ], "full semantic mismatch"


def negative_controls(oracle):
    original = [entry["payload"] for entry in oracle["sections"]]
    assert_semantic(original, oracle)
    variants = {}

    def variant(name, mutate):
        altered = copy.deepcopy(original)
        mutate(altered)
        variants[name] = altered

    paragraph = re.search(r"<p>.*?</p>", original[0]["text"]).group()
    variant(
        "body-deletion",
        lambda values: values[0].update(
            text=values[0]["text"].replace(paragraph, "", 1)
        ),
    )
    variant(
        "body-change",
        lambda values: values[0].update(
            text=values[0]["text"].replace("出血", "改変", 1)
        ),
    )
    variant(
        "body-addition",
        lambda values: values[0].update(text=values[0]["text"] + "<p>不許可追加</p>"),
    )
    variant(
        "body-duplication",
        lambda values: values[0].update(text=values[0]["text"] + paragraph),
    )
    paragraphs = re.findall(r"<p>.*?</p>", original[0]["text"])
    variant(
        "body-order",
        lambda values: values[0].update(
            text=values[0]["text"].replace(
                paragraphs[0] + paragraphs[1], paragraphs[1] + paragraphs[0], 1
            )
        ),
    )
    table_index = next(
        i
        for i, value in enumerate(original)
        if any(block["kind"] == "table" for block in value["blocks"])
    )

    def cell(values):
        return next(
            block for block in values[table_index]["blocks"] if block["kind"] == "table"
        )["rows"][0][0]

    variant("cell-value", lambda values: cell(values).update(text="改変cell"))
    variant("cell-grid", lambda values: cell(values).update(column=99))
    variant("cell-rowspan", lambda values: cell(values).update(rowspan=99))
    variant("cell-colspan", lambda values: cell(values).update(colspan=99))
    variant(
        "html-header",
        lambda values: values[table_index].update(
            text=values[table_index]["text"]
            .replace("<td ", "<th ", 1)
            .replace("</td>", "</th>", 1)
        ),
    )
    variant(
        "html-scope",
        lambda values: values[table_index].update(
            text=values[table_index]["text"].replace("<td ", '<td scope="row" ', 1)
        ),
    )
    reference_index = next(i for i, value in enumerate(original) if value["references"])
    variant(
        "reference-target",
        lambda values: values[reference_index]["references"][0].update(
            target_section_code="99"
        ),
    )
    variant(
        "reference-order",
        lambda values: values[reference_index]["references"].reverse(),
    )
    variant("section-deletion", lambda values: values.pop())
    variant(
        "section-duplication", lambda values: values.append(copy.deepcopy(values[0]))
    )
    variant("source-sha", lambda values: values[0].update(source_sha256="0" * 64))
    variant(
        "context",
        lambda values: values[0]["blocks"][0]["context"].update(labels=["違う文脈"]),
    )
    column_index = next(
        i
        for i, value in enumerate(original)
        if any(block.get("columns") for block in value["blocks"])
    )
    variant(
        "columns",
        lambda values: next(
            block for block in values[column_index]["blocks"] if block.get("columns")
        )["columns"].reverse(),
    )
    figure_index = next(
        i
        for i, value in enumerate(original)
        if any(block["kind"] == "figure" for block in value["blocks"])
    )
    variant(
        "figure",
        lambda values: values[figure_index].update(
            blocks=[
                block
                for block in values[figure_index]["blocks"]
                if block["kind"] != "figure"
            ]
        ),
    )
    for name, payloads in variants.items():
        try:
            assert_semantic(payloads, oracle)
        except AssertionError:
            continue
        raise AssertionError(f"Negative control accepted: {name}")
    return {"negative_controls": list(variants), "count": len(variants)}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    mode, fixture, *args = sys.argv[1:]
    oracle = json.loads(Path(fixture).read_text(encoding="utf8"))
    provenance = json.loads(
        Path(fixture)
        .with_name("import-semantic-oracle.provenance.json")
        .read_text(encoding="utf8")
    )
    assert oracle["status"] == "VERIFIED_SEMANTIC_ORACLE"
    assert (
        hashlib.sha256(Path(fixture).read_bytes()).hexdigest()
        == provenance["oracle_sha256"]
    )
    if mode == "controls":
        print(json.dumps(negative_controls(oracle)))
    else:
        observed = helpers["candidate"](Path(args[0]))
        assert observed["source_sha256"] == oracle["source_sha256"], (
            "source SHA mismatch"
        )
        assert_semantic([entry["payload"] for entry in observed["sections"]], oracle)
        print(json.dumps({"sections": len(observed["sections"]), "semantic": "passed"}))
