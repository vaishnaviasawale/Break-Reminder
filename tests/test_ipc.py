import socket

import pytest

from break_reminder import ipc


@pytest.fixture
def fallback(tmp_path, monkeypatch):
    path = tmp_path / "fallback" / "break-reminder.sock"
    monkeypatch.setattr(ipc, "fallback_socket_file", lambda: path)
    return path


def test_listen_uses_primary_when_it_works(tmp_path, fallback):
    primary = tmp_path / "run" / "br.sock"
    logs = []

    server, path = ipc.listen(primary, lambda *a, **k: logs.append(a))
    server.close()

    assert path == primary
    assert logs == []


def test_listen_falls_back_when_primary_cannot_be_bound(tmp_path, fallback):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("")
    logs = []

    server, path = ipc.listen(
        blocker / "br.sock",
        lambda message, level: logs.append(message),
        attempts=1,
    )
    server.close()

    assert path == fallback
    assert len(logs) == 1
    assert "not-a-directory" in logs[0]


def test_listen_falls_back_when_primary_path_is_too_long(tmp_path, fallback):
    primary = tmp_path / ("x" * 120) / "br.sock"

    server, path = ipc.listen(primary, lambda *a, **k: None, attempts=1)
    server.close()

    assert path == fallback


def test_listen_retries_then_raises(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("")
    monkeypatch.setattr(
        ipc, "fallback_socket_file", lambda: blocker / "fb.sock"
    )
    sleeps = []
    monkeypatch.setattr(ipc.time, "sleep", sleeps.append)

    with pytest.raises(OSError):
        ipc.listen(
            blocker / "br.sock",
            lambda *a, **k: None,
            attempts=3,
            retry_seconds=5,
        )

    assert sleeps == [5, 5]


def test_listen_recovers_on_a_later_attempt(tmp_path, fallback, monkeypatch):
    primary = tmp_path / "br.sock"
    real_bind = ipc._bind
    calls = []

    def flaky_bind(path):
        calls.append(path)
        if len(calls) <= 2:
            raise OSError("transient")
        return real_bind(path)

    monkeypatch.setattr(ipc, "_bind", flaky_bind)
    monkeypatch.setattr(ipc.time, "sleep", lambda s: None)

    server, path = ipc.listen(primary, lambda *a, **k: None, attempts=2)
    server.close()

    assert path == primary
    assert len(calls) == 3


def test_connect_reaches_listener_on_fallback(tmp_path, fallback):
    fallback.parent.mkdir()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(fallback))
    server.listen(1)

    with ipc.connect(tmp_path / "missing.sock") as sock:
        sock.sendall(b"show")

    connection, _ = server.accept()
    assert connection.recv(10) == b"show"
    connection.close()
    server.close()


def test_connect_raises_when_nothing_listens(tmp_path, fallback):
    with pytest.raises(OSError):
        ipc.connect(tmp_path / "missing.sock")
