from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from threading import Lock
from typing import Dict, Optional, Any

@dataclass
class RefreshStatus:
    status: str # idle, running, done, or error
    processed: int = 0
    total: int = 0
    percent: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    message: Optional[str] = None

_status_by_uri: Dict[str, RefreshStatus] = {}
_lock = Lock()

def _now_iso_format() -> str:
    """Return the current UTC time in ISO format."""
    return datetime.now(UTC).isoformat() + "Z"

def start_refresh(s3_uri: str, total: int) -> None:
    """
    Starts the Meilisearch index refresh process, locking to one thread.

    Parameters
    ----------
        s3_uri : str
            The S3 bucket full URI. Formatted as: `"s3://bucket/prefix"`.
        total : int
            The total number of object to index.
    """
    with _lock:
        _status_by_uri[s3_uri] = RefreshStatus(
            status="running",
            processed=0,
            total=total,
            percent=0,
            started_at=_now_iso_format()
        )

def increment_processed(s3_uri: str, count: int = 1) -> None:
    """
    Increment progress under locked thread.
    
    Parameters
    ----------
        s3_uri : str
            The S3 bucket full URI. Formatted as: `"s3://bucket/prefix"`.
        count : int
            The total number of objects that were indexed, default is 1.
    """
    with _lock:
        status = _status_by_uri.get(s3_uri)
        if not status:
            return
        status.processed += count
        if status.total > 0:
            status.percent = int((status.processed / status.total) * 100)

def finish_refresh(s3_uri: str) -> None:
    """
    Marks thread-locked Meilisearch refresh process as "done".

    Parameters
    ----------
        s3_uri : str
            The S3 bucket full URI. Formatted as: `"s3://bucket/prefix"`.
    """
    with _lock:
        status = _status_by_uri.get(s3_uri)
        if not status:
            return
        status.status = "done"
        status.finished_at = _now_iso_format()
        status.percent = 100 if status.total > 0 else 0

def fail_refresh(s3_uri: str, message: str) -> None:
    """
    In event of failure, mark refresh as a failure with a message.

    Parameters
    ----------
        s3_uri : str
            The S3 bucket full URI. Formatted as: `"s3://bucket/prefix"`.
        message : str
            The message to include with the failed index refresh state.
    """
    with _lock:
        status = _status_by_uri.get(s3_uri) or RefreshStatus(status="error")
        status.status = "error"
        status.message = message
        status.finished_at = _now_iso_format()
        # incase new RefreshStatus object created
        _status_by_uri[s3_uri] = status

def get_status(s3_uri: str) -> Dict[str, Any]:
    """
    Returns the current Meilisearch refresh status as a dictionary.

    Parameters
    ----------
        s3_uri : str
            The S3 bucket full URI. Formatted as: `"s3://bucket/prefix"`.
    """
    with _lock:
        status = _status_by_uri.get(s3_uri)
        if not status:
            return {
                "status": 
                "idle", 
                "processed": 0, 
                "total": 0, 
                "percent": 0
            }
        return asdict(status)
