from datetime import datetime, timezone


def utc_now():
    """UTC atual sem tzinfo, comparável com os datetimes naive gravados no SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
