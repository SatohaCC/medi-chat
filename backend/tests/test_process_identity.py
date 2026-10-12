"""Process-start ownership must work without procfs and fail safely."""

import subprocess
import sys
from types import SimpleNamespace

import pytest
from backend.infrastructure.persistence import process_identity as subject


class MissingProcess(Exception):
    pass


class DeniedProcess(Exception):
    pass


def posix_backend(
    monkeypatch,
    *,
    platform="darwin",
    status="running",
    birth=1700000000.125,
    error=None,
):
    calls = []

    def process(pid):
        calls.append(pid)
        if error is not None:
            raise error
        return SimpleNamespace(status=lambda: status, create_time=lambda: birth)

    monkeypatch.setattr(subject, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setitem(
        sys.modules,
        "psutil",
        SimpleNamespace(
            Process=process,
            STATUS_ZOMBIE="zombie",
            STATUS_DEAD="dead",
            NoSuchProcess=MissingProcess,
            AccessDenied=DeniedProcess,
        ),
    )
    return calls


@pytest.mark.parametrize("platform", ["darwin", "freebsd14", "openbsd7"])
def test_non_linux_posix_process_has_stable_start_identity(monkeypatch, platform):
    calls = posix_backend(monkeypatch, platform=platform)
    assert subject.process_identity(1234) == "posix:1700000000.125"
    assert subject.process_identity(1234) == "posix:1700000000.125"
    assert calls == [1234, 1234]


def test_reused_posix_pid_has_a_different_identity(monkeypatch):
    posix_backend(monkeypatch)
    old = subject.process_identity(1234)
    posix_backend(monkeypatch, birth=1700000000.625)
    assert subject.process_identity(1234) == "posix:1700000000.625"
    assert subject.process_identity(1234) != old


@pytest.mark.parametrize("status", ["zombie", "dead"])
def test_terminated_posix_process_is_not_live(monkeypatch, status):
    posix_backend(monkeypatch, status=status)
    assert subject.process_identity(1234) is None


def test_missing_posix_process_is_not_live(monkeypatch):
    calls = posix_backend(monkeypatch, error=MissingProcess())
    assert subject.process_identity(1234) is None
    assert calls == [1234]


def test_access_denied_is_not_reported_as_a_dead_owner(monkeypatch):
    posix_backend(monkeypatch, error=DeniedProcess())
    with pytest.raises(OSError, match="identity cannot be established"):
        subject.process_identity(1234)


def test_linux_stat_identity_format_is_preserved(monkeypatch):
    monkeypatch.setattr(subject, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        subject.Path,
        "read_text",
        lambda self: "1234 (worker (child)) S " + "0 " * 18 + "456789 0",
    )
    assert subject.process_identity(1234) == "456789"


def test_linux_zombie_is_not_live(monkeypatch):
    monkeypatch.setattr(subject, "os", SimpleNamespace(name="posix"))
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        subject.Path,
        "read_text",
        lambda self: "1234 (worker) Z " + "0 " * 18 + "456789 0",
    )
    assert subject.process_identity(1234) is None


def test_native_fallback_identifies_a_live_child_and_its_exit():
    with subprocess.Popen(
        [sys.executable, "-c", "import sys; sys.stdin.read()"],
        stdin=subprocess.PIPE,
    ) as child:
        try:
            identity = subject._posix_process_identity(child.pid)
            assert identity is not None
            assert subject._posix_process_identity(child.pid) == identity
        finally:
            child.terminate()
            child.wait(timeout=5)
    assert subject._posix_process_identity(child.pid) is None
