import logging

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
