from lib.script.tool_dispatcher.dispatcher import _normalize_url_arg


def test_browser_tool_accepts_only_regular_public_http_urls():
    assert _normalize_url_arg("example.com/a?q=1") == "https://example.com/a?q=1"
    assert _normalize_url_arg("www.example.com") == "https://www.example.com"
    assert _normalize_url_arg("//example.com/path") == "https://example.com/path"
    assert _normalize_url_arg("HTTP://example.com/path") == "http://example.com/path"


def test_browser_tool_rejects_active_or_local_protocol_targets():
    rejected = [
        "file:///C:/Windows/win.ini",
        "javascript:alert(1)",
        "data:text/html,hello",
        "ftp://example.com/file",
        "http://127.0.0.1:8080/admin",
        "http://[::1]/",
        "http://192.168.1.10/",
        "http://localhost/",
        "http://printer.local/",
        "http://intranet/",
        "https://user:password@example.com/",
        "https://example.com\\@evil.example/",
        "https://example.com/a b",
    ]
    for raw in rejected:
        assert _normalize_url_arg(raw) == "", raw
