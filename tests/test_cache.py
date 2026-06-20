from src.cache import ResponseCache


def test_hit_within_ttl():
    clock = {"t": 0.0}
    c = ResponseCache(ttl_seconds=10, now_fn=lambda: clock["t"])
    c.put("k", "v")
    clock["t"] = 5
    assert c.get("k") == "v"


def test_miss_after_ttl():
    clock = {"t": 0.0}
    c = ResponseCache(ttl_seconds=10, now_fn=lambda: clock["t"])
    c.put("k", "v")
    clock["t"] = 11
    assert c.get("k") is None        # never serve past TTL


def test_unknown_key_is_miss():
    assert ResponseCache().get("nope") is None
