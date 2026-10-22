"""Test-only native metrics and barrier; exposes no additional HTTP route."""

import asyncio
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from backend.tests.support.postgres_application_server import (
    create_server as base_server,
)
from sqlalchemy import event
from sqlalchemy.pool import QueuePool


def create_server():
    app = base_server(real_morphology=True)
    directory = Path(os.environ["PG_PERF_DIRECTORY"])
    mutex = threading.Lock()
    target = directory / f"metrics-{os.getpid()}.log"

    def emit(kind, **values):
        record = {"time": time.time(), "kind": kind, "pid": os.getpid(), **values}
        with mutex, target.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record) + "\n")

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application):
            engine = application.state.database_engine
            runtime = application.state.generation_runtime
            assert isinstance(engine.pool, QueuePool)
            transactions = {}
            queries = {}
            sql_started = {}
            locks = {}
            original_connect = engine.connect
            original_acquire = runtime.acquire
            service = application.state.attachment_import_service
            original_decode = service.decoder.decode

            def measured_decode(source, *, original_filename="source.xml"):
                started = time.perf_counter()
                try:
                    return original_decode(source, original_filename=original_filename)
                finally:
                    emit(
                        "decode",
                        duration_s=time.perf_counter() - started,
                        source_bytes=len(source),
                    )

            def measured_connect():
                started = time.perf_counter()
                try:
                    return original_connect()
                finally:
                    emit("connection_acquire", duration_s=time.perf_counter() - started)

            @asynccontextmanager
            async def measured_acquire():
                started = time.perf_counter()
                try:
                    async with original_acquire() as snapshot:
                        yield snapshot
                finally:
                    emit("read_scope_closed", duration_s=time.perf_counter() - started)

            def checkout(driver, record, proxy):
                emit(
                    "checkout",
                    backend_pid=driver.info.backend_pid,
                    checkedout=engine.pool.checkedout(),
                    overflow=engine.pool.overflow(),
                )

            def checkin(driver, record):
                if driver is not None:
                    identity = driver.info.backend_pid
                    started = transactions.pop(identity, None)
                    if started is not None:
                        emit(
                            "transaction_returned",
                            backend_pid=identity,
                            duration_s=time.perf_counter() - started,
                        )
                    locked = locks.pop(identity, None)
                    if locked is not None:
                        emit(
                            "publication_lock_returned",
                            backend_pid=identity,
                            duration_s=time.perf_counter() - locked,
                        )
                    emit(
                        "checkin",
                        backend_pid=identity,
                        checkedout=max(0, engine.pool.checkedout() - 1),
                    )

            def begin(connection):
                transactions[
                    connection.connection.driver_connection.info.backend_pid
                ] = time.perf_counter()

            def before(connection, cursor, statement, parameters, context, executemany):
                sql_started[id(context)] = time.perf_counter()
                if "FOR UPDATE" in statement.upper():
                    queries[id(context)] = time.perf_counter()
                    emit(
                        "publication_lock_wait_start",
                        backend_pid=connection.connection.driver_connection.info.backend_pid,
                    )

            def after(connection, cursor, statement, parameters, context, executemany):
                sql_time = time.perf_counter() - sql_started.pop(id(context))
                result = cursor.pgresult
                if (
                    statement.lstrip().upper().startswith("SELECT")
                    and result is not None
                ):
                    emit(
                        "sql_read",
                        duration_s=sql_time,
                        columns=[
                            result.fname(i).decode() for i in range(result.nfields)
                        ],
                        rows=result.ntuples,
                        result_bytes=sum(
                            len(result.get_value(row, column) or b"")
                            for row in range(result.ntuples)
                            for column in range(result.nfields)
                        ),
                    )
                elif statement.lstrip().upper().startswith("INSERT"):
                    emit(
                        "sql_insert",
                        duration_s=sql_time,
                        table=str(context.compiled.statement.table.name)
                        if context.compiled is not None
                        and hasattr(context.compiled.statement, "table")
                        else "unknown",
                        rows=cursor.rowcount,
                    )
                started = queries.pop(id(context), None)
                if started is not None:
                    identity = connection.connection.driver_connection.info.backend_pid
                    locks[identity] = time.perf_counter()
                    emit(
                        "publication_lock_acquire",
                        backend_pid=identity,
                        duration_s=time.perf_counter() - started,
                    )

            listeners = (
                ("checkout", checkout),
                ("checkin", checkin),
                ("begin", begin),
                ("before_cursor_execute", before),
                ("after_cursor_execute", after),
            )
            for name, callback in listeners:
                event.listen(engine, name, callback)
            engine.connect = measured_connect
            runtime.acquire = measured_acquire
            service.decoder.decode = measured_decode
            try:
                morphology = type(
                    application.state.chat_service._app_service.keyword_extractor
                ).__name__
                assert morphology == "JanomeKeywordExtractor"
                emit("ready", morphology=morphology)
                yield
            finally:
                emit("stopped", checkedout=engine.pool.checkedout())
                runtime.acquire = original_acquire
                service.decoder.decode = original_decode
                engine.connect = original_connect
                for name, callback in listeners:
                    event.remove(engine, name, callback)

    app.router.lifespan_context = lifespan

    @app.middleware("http")
    async def observe_request(request, call_next):
        label = request.headers.get("x-perf-sample", "unmeasured")
        emit("request_start", label=label)
        batch = request.headers.get("x-perf-batch")
        if batch:
            assert batch in {"load", "maintenance"}
            emit("barrier_waiting", label=label, batch=batch)
            release = directory / f"release-{batch}"
            while not release.exists():
                await asyncio.sleep(0.002)
        started = time.perf_counter()
        response = await call_next(request)
        emit(
            "request_complete",
            label=label,
            duration_s=time.perf_counter() - started,
            status=response.status_code,
        )
        return response

    return app
