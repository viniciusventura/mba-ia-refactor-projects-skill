from datetime import datetime, timezone


def utc_now():
    """UTC atual sem tzinfo, para comparar com os DateTime naive gravados no SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
