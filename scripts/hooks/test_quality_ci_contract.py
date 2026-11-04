from copy import deepcopy
from pathlib import Path

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/postgres-contracts.yml"


def frontend_contract_errors(workflow_text: str) -> list[str]:
    workflow = yaml.safe_load(workflow_text)
    jobs = workflow.get("jobs") if isinstance(workflow, dict) else None
    if not isinstance(jobs, dict):
        return ["workflow has no jobs mapping"]
    job = jobs.get("frontend-quality")
    if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
        return ["frontend-quality has no steps list"]

    steps = job["steps"]

    def find_step(predicate):
        return next(
            (
                index
                for index, step in enumerate(steps)
                if isinstance(step, dict) and predicate(step)
            ),
            None,
        )

    order = [
        (
            "checkout",
            find_step(
                lambda step: str(step.get("uses", "")).startswith("actions/checkout@")
            ),
        ),
        (
            "Node setup",
            find_step(
                lambda step: str(step.get("uses", "")).startswith("actions/setup-node@")
            ),
        ),
        (
            "uv setup",
            find_step(
                lambda step: str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
            ),
        ),
        (
            "pnpm install",
            find_step(
                lambda step: (
                    step.get("run", "").strip() == "pnpm install --frozen-lockfile"
                )
            ),
        ),
        (
            "uv sync",
            find_step(
                lambda step: (
                    step.get("run", "").strip() == "uv sync --project backend --locked"
                )
            ),
        ),
        (
            "frontend quality",
            find_step(
                lambda step: step.get("run", "").strip() == "pnpm quality:frontend"
            ),
        ),
        (
            "production build",
            find_step(
                lambda step: (
                    step.get("run", "").strip() == "pnpm --filter frontend build"
                )
            ),
        ),
    ]
    errors = [
        f"frontend-quality is missing {name}" for name, index in order if index is None
    ]
    positions = [index for _, index in order if index is not None]
    if len(positions) == len(order) and positions != sorted(positions):
        errors.append(
            "frontend runtime setup and dependency sync must precede its quality and build checks"
        )

    postgres_job = jobs.get("postgres-contracts")
    postgres_commands = (
        [
            str(step.get("run", ""))
            for step in postgres_job.get("steps", [])
            if isinstance(step, dict)
        ]
        if isinstance(postgres_job, dict)
        else []
    )
    for required in (
        "pnpm quality:backend",
        "pnpm quality:scripts",
        "pnpm test:postgres -q",
    ):
        if not any(command.strip() == required for command in postgres_commands):
            errors.append(f"postgres-contracts is missing {required}")
    return errors


def test_frontend_ci_declares_python_bridge_runtime_before_quality() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert frontend_contract_errors(workflow) == []


def test_ci_contract_rejects_missing_python_setup_or_late_dependency_sync() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["frontend-quality"]["steps"]
    without_uv = deepcopy(workflow)
    without_uv["jobs"]["frontend-quality"]["steps"] = [
        step for step in steps if step.get("uses") != "astral-sh/setup-uv@v7"
    ]
    assert any(
        "missing uv setup" in error
        for error in frontend_contract_errors(yaml.safe_dump(without_uv))
    )

    late_sync = deepcopy(workflow)
    frontend_steps = late_sync["jobs"]["frontend-quality"]["steps"]
    sync = next(
        step
        for step in frontend_steps
        if step.get("run") == "uv sync --project backend --locked"
    )
    frontend_steps.remove(sync)
    quality_index = next(
        i
        for i, step in enumerate(frontend_steps)
        if step.get("run") == "pnpm quality:frontend"
    )
    frontend_steps.insert(quality_index + 1, sync)
    assert any(
        "must precede" in error
        for error in frontend_contract_errors(yaml.safe_dump(late_sync))
    )
