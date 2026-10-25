"""PG-044～047: real HTTP/PG timings and resources on an owned test schema.

Run from root with explicit TEST_DATABASE_URL/TEST_RUNTIME_DATABASE_URL.
External Jev/LLM are fixed; Janome, import, persistence and retrieval are real.
"""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
from contextlib import suppress
from pathlib import Path

import httpx
import psutil
from backend.infrastructure.cli.manage_postgres import load_inputs
from backend.infrastructure.persistence.registration.postgres_registration_publisher import (
    PostgresRegistrationPublisher,
)
from backend.infrastructure.persistence.schemas import attachment_tables as tables
from backend.infrastructure.pmda_xml.pmda_artifact_encoder import PmdaArtifactEncoder
from backend.infrastructure.pmda_xml.pmda_xml_decoder import PmdaXmlDecoder
from backend.tests.support.generation_os_server import main_server
from backend.tests.support.paths import PROJECT_ROOT
from backend.tests.support.postgres_fixtures import owned_postgres_engines
from backend.tests.support.registration_oracles import source
from sqlalchemy import select, text

SOURCE_BYTES = 10 * 1024 * 1024
RSS_BUDGET = 512 * 1024 * 1024
CODES = {"A": "7777777A0000", "B": "7777777A0001"}


def events(directory, pid=None):
    result = []
    for path in directory.glob("metrics-*.log"):
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue  # A native writer may still be finishing the last log line.
            if pid is None or value["pid"] == pid:
                result.append(value)
    return sorted(result, key=lambda item: item["time"])


def database_metrics(engine, schema):
    with engine.connect() as connection:
        lsn = connection.execute(text("SELECT pg_current_wal_lsn()::text")).scalar_one()
        relations = connection.execute(
            text(
                "SELECT c.relname, pg_total_relation_size(c.oid) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=:schema AND c.relkind IN ('r','p') ORDER BY c.relname"
            ),
            {"schema": schema},
        ).all()
    return {
        "wal_lsn": lsn,
        "schema_bytes": sum(row[1] for row in relations),
        "relations": dict(relations),
    }


def lsn_value(value):
    high, low = value.split("/")
    return (int(high, 16) << 32) + int(low, 16)


def waiting_writers(engine, pids):
    with engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT count(DISTINCT pid) FROM pg_locks WHERE pid=ANY(:pids) AND NOT granted"
            ),
            {"pids": list(pids)},
        ).scalar_one()


class Sampler:
    def __init__(self, pid, baseline, engine, directory):
        self.process = psutil.Process(pid)
        self.baseline = baseline
        self.engine = engine
        self.directory = directory
        self.peak = baseline
        self.os_peak = baseline
        self.cpu_s = 0.0
        self.database_samples = []
        self.issues = []
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self.run, name="owned-performance-sampler"
        )

    def start(self):
        self.initial_cpu = sum(self.process.cpu_times()[:2])
        self.thread.start()

    def run(self):
        next_database = 0.0
        while not self.stop_event.is_set():
            try:
                memory = self.process.memory_info()
                self.peak = max(self.peak, memory.rss)
                self.os_peak = max(
                    self.os_peak, getattr(memory, "peak_wset", memory.rss)
                )
                if time.monotonic() >= next_database:
                    pids = {
                        value["backend_pid"]
                        for value in events(self.directory)
                        if "backend_pid" in value
                    }
                    ready = self.directory / "maintenance-ready.json"
                    if ready.exists():
                        with suppress(json.JSONDecodeError):
                            pids.add(json.loads(ready.read_text())["backend_pid"])
                    with self.engine.connect() as connection:
                        rows = (
                            connection.execute(
                                text(
                                    "SELECT pid, state, wait_event_type, wait_event, EXTRACT(epoch FROM clock_timestamp()-xact_start)::float age_s FROM pg_stat_activity WHERE pid=ANY(:pids)"
                                ),
                                {"pids": list(pids)},
                            )
                            .mappings()
                            .all()
                        )
                        waiting = waiting_writers(self.engine, pids)
                    self.database_samples.append(
                        {
                            "time": time.time(),
                            "backends": [dict(row) for row in rows],
                            "waiting_pids": waiting,
                        }
                    )
                    next_database = time.monotonic() + 0.05
            except Exception as error:
                self.issues.append(type(error).__name__)
            self.stop_event.wait(0.01)

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=15)
        if self.thread.is_alive():
            raise RuntimeError("Owned sampler did not finish")
        memory = self.process.memory_info()
        self.peak = max(self.peak, memory.rss)
        self.os_peak = max(self.os_peak, getattr(memory, "peak_wset", memory.rss))
        self.cpu_s = sum(self.process.cpu_times()[:2]) - self.initial_cpu


def performance_source(name, sequence, *, padded=True):
    year, month = 2027 + (sequence - 1) // 12, (sequence - 1) % 12 + 1
    raw = source(
        f"テスト性能{name}本文 {sequence}",
        (CODES[name],),
        doc=f"perf_{name}",
        revised_at=f"{year:04}-{month:02}",
    )
    raw = raw.replace("製品A".encode(), f"テスト性能薬{name}".encode())
    return b" " * (SOURCE_BYTES - len(raw)) + raw if padded else raw


async def wait_until(predicate, *, timeout=20):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise RuntimeError("Owned performance barrier timed out")
        await asyncio.sleep(0.01)


async def registration(client, raw, label, batch=None):
    headers = {"x-perf-sample": label}
    if batch:
        headers["x-perf-batch"] = batch
    started = time.perf_counter()
    response = await client.post(
        "/api/attachment-imports",
        headers=headers,
        files={"file": ("テスト性能.xml", raw, "application/xml")},
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 201, "Measurement must publish a new valid version"
    payload = response.json()
    assert payload["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert payload["validation_status"] == "pass"
    assert payload["reused"] is False
    return {
        "operation": "register",
        "label": label,
        "request_s": elapsed,
        "source_bytes": len(raw),
        "source_sha256": payload["source_sha256"],
        "generation_id": payload["generation_id"],
    }


async def search(client, label):
    started = time.perf_counter()
    response = await client.get(
        "/api/search", params={"q": "副作用"}, headers={"x-perf-sample": label}
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 200 and response.json()["items"]
    return {
        "operation": "search",
        "label": label,
        "request_s": elapsed,
        "result_count": len(response.json()["items"]),
    }


async def chat(client, name, label, batch, permitted_hashes):
    started = time.perf_counter()
    response = await client.post(
        "/api/chat",
        headers={"x-perf-sample": label, "x-perf-batch": batch},
        json={
            "message": f"テスト性能薬{name}の警告",
            "product_yj_codes": [CODES[name]],
        },
    )
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sources"]) == 1
    item = payload["sources"][0]
    assert item["product_yj_codes"] == [CODES[name]]
    assert item["unit_id"] in {
        f"000001_perf_{name}:{digest}:1" for digest in permitted_hashes
    }
    return {
        "operation": "chat_retrieval",
        "label": label,
        "request_s": elapsed,
        "unit_id": item["unit_id"],
        "fixed_llm": True,
    }


async def measure(identifier, phase, action, engine, schema, directory, pid, baseline):
    before = database_metrics(engine, schema)
    sampler = Sampler(pid, baseline, engine, directory)
    started = time.time()
    sampler.start()
    try:
        operations = await action()
    finally:
        sampler.close()
    ended = time.time()
    after = database_metrics(engine, schema)
    observed = [
        value for value in events(directory, pid) if started <= value["time"] <= ended
    ]

    def maximum(kind):
        return max(
            (value["duration_s"] for value in observed if value["kind"] == kind),
            default=0,
        )

    pool = [value for value in observed if value["kind"] in {"checkout", "checkin"}]
    reads = [value for value in observed if value["kind"] == "sql_read"]
    if identifier.endswith("-search"):
        assert reads and not {"source", "content"}.intersection(
            column for value in reads for column in value["columns"]
        ), "Search must not fetch original/figure bytea"
    assert pool and pool[-1]["checkedout"] == 0, (
        f"Request completion must release its borrowed connections: {started=} {ended=} {pool=}"
    )
    assert not sampler.issues, "Resource sampling must not silently omit errors"
    assert sampler.database_samples, "Actual PG lock/transaction samples are required"
    return {
        "id": identifier,
        "phase": phase,
        "operations": operations,
        "start": started,
        "end": ended,
        "pid": pid,
        "readiness_baseline_rss_bytes": baseline,
        "sampled_peak_rss_bytes": sampler.peak,
        "os_process_peak_rss_bytes": sampler.os_peak,
        "additional_rss_upper_bound_bytes": max(0, sampler.os_peak - baseline),
        "backend_cpu_s": sampler.cpu_s,
        "decode_s": [
            value["duration_s"] for value in observed if value["kind"] == "decode"
        ],
        "database_insert_s": [
            value for value in observed if value["kind"] == "sql_insert"
        ],
        "database_reads": reads,
        "selected_rows": sum(value["rows"] for value in reads),
        "selected_result_bytes": sum(value["result_bytes"] for value in reads),
        "database_before": before,
        "database_after": after,
        "database_growth_bytes": after["schema_bytes"] - before["schema_bytes"],
        "cluster_wal_generated_bytes": lsn_value(after["wal_lsn"])
        - lsn_value(before["wal_lsn"]),
        "pool_checkedout_peak": max(value["checkedout"] for value in pool),
        "pool_checkedout_after": pool[-1]["checkedout"],
        "pool_overflow_capacity_excess_peak": max(
            0, max((value.get("overflow", 0) for value in pool), default=0)
        ),
        "connection_acquire_upper_bound_s": maximum("connection_acquire"),
        "transaction_until_pool_return_upper_bound_s": maximum("transaction_returned"),
        "read_materialize_scope_upper_bound_s": maximum("read_scope_closed"),
        "publication_lock_acquire_s": maximum("publication_lock_acquire"),
        "publication_lock_until_pool_return_upper_bound_s": maximum(
            "publication_lock_returned"
        ),
        "database_samples": sampler.database_samples,
    }


async def load(
    client, directory, pid, old_hashes, raws, engine, schema, *, maintenance
):
    batch = "maintenance" if maintenance else "load"
    maintenance_child = None
    log = None
    started = time.time()
    tasks = []
    try:
        if maintenance:
            log = (directory / "maintenance-process.log").open("w", encoding="utf-8")
            maintenance_child = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "backend.tests.support.postgres_performance_maintenance",
                ],
                cwd=PROJECT_ROOT,
                env={
                    **os.environ,
                    "PG_WORKER_SCHEMA": schema,
                    "PG_PERF_DIRECTORY": str(directory),
                },
                stdout=log,
                stderr=log,
            )
            await wait_until(lambda: (directory / "maintenance-ready.json").exists())
        tasks = [
            asyncio.create_task(
                registration(client, raws[name], f"{batch}-register-{name}", batch)
            )
            for name in ("A", "B")
        ]
        tasks += [
            asyncio.create_task(
                chat(
                    client,
                    name,
                    f"{batch}-chat-{name}",
                    batch,
                    {old_hashes[name]}
                    if maintenance
                    else {old_hashes[name], hashlib.sha256(raws[name]).hexdigest()},
                )
            )
            for name in ("A", "B")
        ]
        await wait_until(
            lambda: (
                len(
                    [
                        value
                        for value in events(directory, pid)
                        if value["kind"] == "barrier_waiting"
                        and value.get("batch") == batch
                        and value["time"] >= started
                    ]
                )
                == 4
            )
        )
        if maintenance:
            (directory / "release-maintenance-worker").touch()
            await wait_until(lambda: (directory / "maintenance-lock-held").exists())
        (directory / f"release-{batch}").touch()
        if maintenance:
            writer_pids = set()
            deadline = time.monotonic() + 15
            while len(writer_pids) < 2 or waiting_writers(engine, writer_pids) < 2:
                writer_pids = {
                    value["backend_pid"]
                    for value in events(directory, pid)
                    if value["kind"] == "publication_lock_wait_start"
                    and value["time"] >= started
                }
                assert time.monotonic() < deadline, (
                    "Both real writers must wait behind the maintenance lock"
                )
                await asyncio.sleep(0.01)
            assert all(task.done() for task in tasks[2:]), (
                "Both MVCC chat reads must finish while maintenance holds the publication lock"
            )
            (directory / "maintenance-topology-observed.json").write_text(
                json.dumps(
                    {
                        "observed_at": time.time(),
                        "waiting_writer_pids": sorted(writer_pids),
                        "actual_waiting_count": waiting_writers(engine, writer_pids),
                        "both_chat_tasks_completed_while_lock_held": True,
                    }
                ),
                encoding="utf-8",
            )
            (directory / "release-maintenance-lock").touch()
        results = await asyncio.gather(*tasks)
        if maintenance_child is not None:
            await asyncio.to_thread(maintenance_child.wait, 15)
            assert maintenance_child.returncode == 0
        return results
    finally:
        releases = [f"release-{batch}"]
        if maintenance:
            releases += ["release-maintenance-worker", "release-maintenance-lock"]
        for name in releases:
            (directory / name).touch()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if maintenance_child is not None and maintenance_child.poll() is None:
            maintenance_child.terminate()
            maintenance_child.wait(timeout=15)
        if log is not None:
            log.close()


def metadata(engine):
    with engine.connect() as connection:
        database = (
            connection.execute(
                text(
                    "SELECT version() version, current_setting('server_version_num') server_version_num, current_setting('max_connections') max_connections, current_setting('shared_buffers') shared_buffers, current_setting('work_mem') work_mem, current_setting('statement_timeout') statement_timeout, current_setting('lock_timeout') lock_timeout, current_setting('idle_in_transaction_session_timeout') idle_in_transaction_timeout, current_setting('server_encoding') server_encoding"
                )
            )
            .mappings()
            .one()
        )
        collation = connection.execute(
            text(
                "SELECT to_jsonb(d)->>'datcollate',to_jsonb(d)->>'datlocprovider' FROM pg_database d WHERE datname=current_database()"
            )
        ).one()
    files = (
        "backend/infrastructure/persistence/postgres_runtime.py",
        "backend/infrastructure/persistence/postgres_registration.py",
        "backend/infrastructure/persistence/postgres_engine.py",
        "backend/infrastructure/persistence/postgres_schema.py",
        "backend/tests/support/measure_postgres.py",
        "backend/tests/support/postgres_performance_server.py",
        "backend/uv.lock",
    )
    return {
        "database": dict(database),
        "database_collation": list(collation),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu": psutil.cpu_count(),
        "physical_cpu": psutil.cpu_count(logical=False),
        "host_ram_bytes": psutil.virtual_memory().total,
        "pool_size": 5,
        "max_overflow": 0,
        "pool_timeout_s": 10,
        "connect_timeout_s": 10,
        "read_workers": 4,
        "import_workers": 2,
        "uvicorn_workers": 1,
        "http_measurement_timeout_s": 60,
        "uvicorn_keepalive_timeout_s": 5,
        "cold_definition": "new backend process after readiness; PostgreSQL/OS caches are not flushed",
        "warm_definition": "same process after a new 10MiB publication; every registration is 201, never receipt replay",
        "morphology": "production Janome initialized before readiness baseline",
        "external_doubles": "Jev unavailable; constant LLM only. HTTP/PG/local detection are real; no API interception",
        "rss_definition": "OS lifetime peak_wset on Windows minus same-process post-readiness RSS; upper bound includes earlier peaks. Other OS uses polled RSS.",
        "timing_definition": "HTTP search/registration and materialize scopes; chat includes constant local LLM as a conservative upper bound, not external generation time",
        "measurement_overhead": "10ms RSS polling; about50ms PG stats polling; native engine events append test metrics logs",
        "wal_definition": "cluster LSN delta over isolated test workload; background/unrelated cluster WAL is not attributed exclusively to the schema",
        "source_files_sha256": {
            name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
            for name in files
        },
        "budgets": {
            "search_s": 2,
            "new_10mib_registration_s": 30,
            "additional_rss_bytes": RSS_BUDGET,
        },
    }


async def run(output, samples):
    records = []
    old_hashes = {}
    sequence = 1
    with owned_postgres_engines() as (owner, observer, schema):
        initial = load_inputs(PROJECT_ROOT / "data/pmda/originals")
        assert len(initial) == 7 and sum(len(item.figures) for item in initial) == 60
        publisher = PostgresRegistrationPublisher(owner, encoder=PmdaArtifactEncoder())
        publisher.publish_inputs(initial, initial=True)
        for name in ("A", "B"):
            raw = performance_source(name, 1, padded=False).replace(
                b"2027-01", b"2026-10"
            )
            publisher.publish(PmdaXmlDecoder().decode(raw), raw)
            old_hashes[name] = hashlib.sha256(raw).hexdigest()
        details = metadata(observer)
        details["process_start_to_ready_s"] = []
        details["initial_originals"] = [
            {
                "sha256": hashlib.sha256(item.source).hexdigest(),
                "bytes": len(item.source),
                "figures": len(item.figures),
            }
            for item in initial
        ]
        for iteration in range(samples):
            directory = output / f"process-{iteration + 1}"
            directory.mkdir()
            launch_started = time.perf_counter()
            with main_server(schema, directory, performance=True) as (health, child, _):
                details["process_start_to_ready_s"].append(
                    time.perf_counter() - launch_started
                )
                ready = [
                    value for value in events(directory) if value["kind"] == "ready"
                ]
                assert len(ready) == 1
                backend_pid = ready[0]["pid"]
                assert backend_pid == child.pid or child.pid in {
                    item.pid for item in psutil.Process(backend_pid).parents()
                }
                baseline = psutil.Process(backend_pid).memory_info().rss
                async with httpx.AsyncClient(
                    base_url=str(health.base_url), timeout=60
                ) as client:
                    for phase in ("cold", "warm"):
                        label = f"{phase}-{iteration + 1}"

                        async def search_action(label=label):
                            return [await search(client, label + "-search")]

                        records.append(
                            await measure(
                                label + "-search",
                                phase,
                                search_action,
                                observer,
                                schema,
                                directory,
                                backend_pid,
                                baseline,
                            )
                        )
                        raw = performance_source("A", sequence)
                        sequence += 1

                        async def register_action(raw=raw, label=label):
                            return [
                                await registration(client, raw, label + "-register")
                            ]

                        records.append(
                            await measure(
                                label + "-register",
                                phase,
                                register_action,
                                observer,
                                schema,
                                directory,
                                backend_pid,
                                baseline,
                            )
                        )
                        old_hashes["A"] = hashlib.sha256(raw).hexdigest()
                    if iteration == samples - 1:
                        for maintenance in (False, True):
                            raws = {}
                            for name in ("A", "B"):
                                raws[name] = performance_source(name, sequence)
                                sequence += 1

                            async def load_action(
                                directory=directory,
                                raws=raws,
                                maintenance=maintenance,
                                backend_pid=backend_pid,
                            ):
                                return await load(
                                    client,
                                    directory,
                                    backend_pid,
                                    old_hashes,
                                    raws,
                                    observer,
                                    schema,
                                    maintenance=maintenance,
                                )

                            label = (
                                "maintenance-topology"
                                if maintenance
                                else "concurrent-2-register-2-chat"
                            )
                            records.append(
                                await measure(
                                    label,
                                    label,
                                    load_action,
                                    observer,
                                    schema,
                                    directory,
                                    backend_pid,
                                    baseline,
                                )
                            )
                            old_hashes.update(
                                {
                                    name: hashlib.sha256(raw).hexdigest()
                                    for name, raw in raws.items()
                                }
                            )
                assert any(
                    value.get("morphology") == "JanomeKeywordExtractor"
                    for value in events(directory, backend_pid)
                )
        with observer.connect() as connection:
            active = dict(
                connection.execute(
                    select(
                        tables.active.c.yj_code, tables.receipts.c.source_sha256
                    ).join(
                        tables.receipts,
                        tables.receipts.c.version_id == tables.active.c.version_id,
                    )
                ).all()
            )
        assert {code: active[code] for code in CODES.values()} == {
            CODES[name]: digest for name, digest in old_hashes.items()
        }
        publisher.maintenance.cleanup()
        publisher.maintenance.cleanup()
        with owner.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            before_vacuum = database_metrics(observer, schema)
            vacuum_started = time.perf_counter()
            for table in tables.metadata.sorted_tables:
                connection.execute(text(f'VACUUM (ANALYZE) "{schema}"."{table.name}"'))
            vacuum_s = time.perf_counter() - vacuum_started
            estimates = (
                connection.execute(
                    text(
                        "SELECT relname,n_live_tup,n_dead_tup,last_vacuum,last_analyze FROM pg_stat_all_tables WHERE schemaname=:schema ORDER BY relname"
                    ),
                    {"schema": schema},
                )
                .mappings()
                .all()
            )
        details["dedicated_schema_vacuum"] = {
            "duration_s": vacuum_s,
            "before": before_vacuum,
            "after": database_metrics(observer, schema),
            "row_estimates": [
                {
                    key: str(value) if key.startswith("last_") else value
                    for key, value in row.items()
                }
                for row in estimates
            ],
            "note": "Ordinary VACUUM ANALYZE only on this created test UUID schema; physical shrink is not required. MVCC old/new visibility while deletion is independently tested in PG023.",
        }
    return details, records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=3)
    args = parser.parse_args()
    if args.samples < 3:
        parser.error("At least three cold and warm samples are required")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    details, records = asyncio.run(run(output, args.samples))
    violations = []
    for record in records:
        if record["additional_rss_upper_bound_bytes"] > RSS_BUDGET:
            violations.append(record["id"] + ":RSS")
        if (
            record["pool_checkedout_peak"] > 5
            or record["pool_checkedout_after"] != 0
            or record["pool_overflow_capacity_excess_peak"]
        ):
            violations.append(record["id"] + ":pool")
        if record["read_materialize_scope_upper_bound_s"] > 2:
            violations.append(record["id"] + ":retrieval")
        for operation in record["operations"]:
            limit = 30 if operation["operation"] == "register" else 2
            if operation["request_s"] > limit:
                violations.append(operation["label"] + ":latency")
            if (
                operation["operation"] == "register"
                and operation["source_bytes"] != SOURCE_BYTES
            ):
                violations.append(operation["label"] + ":input_bytes")
    summary = {}
    for phase in ("cold", "warm"):
        for operation in ("search", "register"):
            values = [
                item["request_s"]
                for record in records
                if record["phase"] == phase
                for item in record["operations"]
                if item["operation"] == operation
            ]
            summary[f"{phase}_{operation}"] = {
                "all_s": values,
                "median_s": statistics.median(values),
                "max_s": max(values),
            }
    result = {
        "status": "failed" if violations else "passed",
        "metadata": details,
        "summary": summary,
        "samples": records,
        "violations": violations,
    }
    (output / "measurements.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        "# PG-044～047 real PostgreSQL measurements",
        "",
        "Status: " + result["status"],
        "",
        "| Case | All seconds | Median | Max |",
        "|---|---|---|---|",
    ]
    for key, value in summary.items():
        lines.append(
            f"| {key} | {value['all_s']} | {value['median_s']:.4f} | {value['max_s']:.4f} |"
        )
    lines.extend(
        [
            "",
            "Complete samples, RSS baseline/peak, DB/WAL deltas, pool/lock/transaction observations and effective hardware/settings are in measurements.json and process metrics logs.",
            "",
            "Cold means process cold after readiness; database/OS caches were not flushed. Source input is valid 10MiB XML with whitespace padding. Jev/LLM are explicit doubles; actual Janome/HTTP/PG are used. No original files or existing database were replaced. Only the created test UUID schema was reclaimed.",
            "",
            "Violations: " + json.dumps(violations),
        ]
    )
    (output / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "samples": len(records),
                "violations": violations,
            }
        )
    )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
