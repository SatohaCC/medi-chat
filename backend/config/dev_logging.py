"""Keep local supervisor probes out of development access logs only."""

import logging


class DevelopmentProbeFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) == 5:
            client, method, target, _version, status = args
            if (
                isinstance(client, str)
                and client.startswith(("127.0.0.1:", "[::1]:", "::1:"))
                and method == "GET"
                and target == "/api?__medi_chat_dev_monitor=1"
                and str(status) in {"200", "401"}
            ):
                return False
        return True
