import logging
import os
from pathlib import Path

from backend.config.dev_logging import DevelopmentAccessLogFilter


def test_access_log_query_is_redacted_before_output(caplog):
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        "%s %s %s %s %s",
        (
            "127.0.0.1:12345",
            "GET",
            "/api/search?query=private-medical-term&token=private-token",
            "1.1",
            200,
        ),
        None,
    )

    assert DevelopmentAccessLogFilter().filter(record)
    rendered = record.getMessage()
    assert rendered == "127.0.0.1:12345 GET /api/search?[REDACTED] 1.1 200"
    assert "private-medical-term" not in rendered
    assert "private-token" not in rendered

    caplog.handler.addFilter(DevelopmentAccessLogFilter())
    logger = logging.getLogger("uvicorn.access")
    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logger.info(
            "%s %s %s %s %s",
            "127.0.0.1:12345",
            "GET",
            "/api/search?query=private-medical-term&token=private-token",
            "1.1",
            200,
        )

    assert "127.0.0.1:12345 GET /api/search?[REDACTED] 1.1 200" in caplog.text
    assert "private-medical-term" not in caplog.text
    assert "private-token" not in caplog.text


def test_websocket_handshake_query_is_redacted():
    record = logging.LogRecord(
        "uvicorn.error",
        logging.INFO,
        "",
        0,
        '%s - "WebSocket %s" [accepted]',
        ("127.0.0.1:12345", "/api/ws?token=private-token"),
        None,
    )

    assert DevelopmentAccessLogFilter().filter(record)
    rendered = record.getMessage()
    assert rendered == '127.0.0.1:12345 - "WebSocket /api/ws?[REDACTED]" [accepted]'
    assert "private-token" not in rendered


def test_requests_without_query_remain_visible():
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        "%s %s %s %s %s",
        ("127.0.0.1:12345", "GET", "/api", "1.1", 200),
        None,
    )

    assert DevelopmentAccessLogFilter().filter(record)
    assert record.getMessage() == "127.0.0.1:12345 GET /api 1.1 200"


def test_uvicorn_file_filter_resolves_relative_exclude_dirs(tmp_path: Path):
    import uvicorn.supervisors.watchfilesreload as wfr
    from uvicorn.config import Config

    sub_dir = tmp_path / "excluded_dir"
    sub_dir.mkdir()
    child_file = sub_dir / "module.py"
    child_file.write_text("x = 1")

    cfg = Config("backend.main:app", reload=True, reload_excludes=[str(sub_dir.name)])
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        file_filter = wfr.FileFilter(cfg)
        assert not file_filter(child_file.resolve())
    finally:
        os.chdir(old_cwd)
