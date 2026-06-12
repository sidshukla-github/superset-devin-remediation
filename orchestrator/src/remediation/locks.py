import fcntl
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from remediation.config import settings

logger = logging.getLogger(__name__)

_thread_locks: dict[int, threading.Lock] = {}
_meta_lock = threading.Lock()


def _thread_lock(issue_number: int) -> threading.Lock:
    with _meta_lock:
        if issue_number not in _thread_locks:
            _thread_locks[issue_number] = threading.Lock()
        return _thread_locks[issue_number]


@contextmanager
def issue_remediation_lock(issue_number: int) -> Iterator[bool]:
    """Serialize remediation per issue (in-process + file lock across workers)."""
    thread_lock = _thread_lock(issue_number)
    thread_lock.acquire()
    lock_path = Path(settings.metrics_path).parent / "locks" / f"issue-{issue_number}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open("w")
    acquired = False
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        yield True
    except BlockingIOError:
        logger.info("Issue #%s remediation already in progress; skipping", issue_number)
        yield False
    finally:
        if acquired:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
        thread_lock.release()
