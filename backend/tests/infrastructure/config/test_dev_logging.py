import logging

import pytest
from backend.config.dev_logging import DevelopmentProbeFilter


@pytest.mark.parametrize("status", [200, 401])
def test_local_supervisor_probe_is_quiet(status):
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        "%s %s %s %s %s",
        ("127.0.0.1:12345", "GET", "/api?__medi_chat_dev_monitor=1", "1.1", status),
        None,
    )
    assert not DevelopmentProbeFilter().filter(record)


@pytest.mark.parametrize(
    "client,method,target,status",
    [
        ("127.0.0.1:12345", "GET", "/api", 401),
        ("127.0.0.1:12345", "GET", "/api?__medi_chat_dev_monitor=1", 500),
        ("127.0.0.1:12345", "POST", "/api?__medi_chat_dev_monitor=1", 401),
        ("192.0.2.1:12345", "GET", "/api?__medi_chat_dev_monitor=1", 401),
        ("127.0.0.1:12345", "GET", "/api/chat", 200),
    ],
)
def test_other_requests_remain_visible(client, method, target, status):
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        "",
        0,
        "%s %s %s %s %s",
        (client, method, target, "1.1", status),
        None,
    )
    assert DevelopmentProbeFilter().filter(record)


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

    assert DevelopmentProbeFilter().filter(record)
    rendered = record.getMessage()
    assert rendered == "127.0.0.1:12345 GET /api/search?[REDACTED] 1.1 200"
    assert "private-medical-term" not in rendered
    assert "private-token" not in rendered

    caplog.handler.addFilter(DevelopmentProbeFilter())
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
