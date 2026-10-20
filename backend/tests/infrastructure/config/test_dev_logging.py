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
