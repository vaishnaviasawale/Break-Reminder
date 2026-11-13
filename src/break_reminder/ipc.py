import os
import socket
import tempfile
import time
from pathlib import Path


BIND_ATTEMPTS = 3
BIND_RETRY_SECONDS = 1


def fallback_socket_file():
    # Used when the primary path can't be bound (unwritable directory, path
    # longer than the ~107 byte AF_UNIX limit). The GUI and the CLI both
    # derive it the same way, so they agree without talking to each other.
    return (
        Path(tempfile.gettempdir())
        / f"break-reminder-{os.getuid()}"
        / "break-reminder.sock"
    )


def socket_candidates(primary):
    return [primary, fallback_socket_file()]


def _prepare_directory(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    # The fallback lives in a shared temp directory, so make sure nobody
    # else created it first.
    info = path.parent.stat()
    if path.parent == fallback_socket_file().parent and (
        info.st_uid != os.getuid()
    ):
        raise OSError(f"{path.parent} is owned by another user")


def _bind(path):
    _prepare_directory(path)
    path.unlink(missing_ok=True)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(str(path))
        server.listen(1)
    except OSError:
        server.close()
        raise

    return server


def listen(primary, log, attempts=None, retry_seconds=None):
    # Tries each candidate path in turn, retrying the whole list to ride
    # out transient errors. Returns (server, path), or raises the last
    # OSError once everything has failed.
    attempts = BIND_ATTEMPTS if attempts is None else attempts
    retry_seconds = BIND_RETRY_SECONDS if retry_seconds is None else retry_seconds
    last_error = None

    for attempt in range(attempts):
        for path in socket_candidates(primary):
            try:
                return _bind(path), path
            except OSError as error:
                last_error = error
                log(f"Could not listen on {path}: {error}", level="WARNING")

        if attempt < attempts - 1:
            time.sleep(retry_seconds)

    raise last_error


# Reply the GUI sends once it has received a command.
ACK = b"ok"


def connect(primary, timeout=None):
    # Returns a connected socket from the first candidate that accepts.
    last_error = None

    for path in socket_candidates(primary):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            if timeout is not None:
                sock.settimeout(timeout)
            sock.connect(str(path))
            return sock
        except OSError as error:
            sock.close()
            last_error = error

    raise last_error
