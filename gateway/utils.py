import uuid

def is_uuid(s: str) -> bool:
    try:
        uuid.UUID(str(s))
        return True
    except Exception:
        return False
