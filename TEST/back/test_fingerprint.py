# TEST/back/test_fingerprint.py
from app.services.ingest import fingerprint, normalize_message


def test_normalize_replaces_variable_parts() -> None:
    msg = "Timeout  10.0.0.5:5432 after 3000 ms id=3f2a1b4c-1111-2222-3333-444455556666"
    assert normalize_message(msg) == "timeout <ip> after <n> ms id=<uuid>"


def test_fingerprint_groups_similar_messages() -> None:
    a = fingerprint("api", "HTTP 503 GET /orders/12")
    b = fingerprint("api", "http 503 get /orders/77")
    assert a == b and len(a) == 64
    assert fingerprint("nginx", "HTTP 503 GET /orders/12") != a
    assert fingerprint("api", "disk full") != a
