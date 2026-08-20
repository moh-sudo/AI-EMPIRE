from unittest.mock import MagicMock, patch

from agents.learning import content_transform as ct


def _fake_resolved(*ips: str):
    return [(2, 1, 6, "", (ip, 0)) for ip in ips]


def test_is_safe_url_rejects_non_http_scheme():
    assert ct._is_safe_url("ftp://example.com/file") is False
    assert ct._is_safe_url("file:///etc/passwd") is False


def test_is_safe_url_rejects_url_with_no_hostname():
    assert ct._is_safe_url("http://") is False


def test_is_safe_url_rejects_unresolvable_hostname():
    with patch.object(ct.socket, "getaddrinfo", side_effect=ct.socket.gaierror("nope")):
        assert ct._is_safe_url("http://does-not-resolve.invalid") is False


def test_is_safe_url_rejects_loopback():
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("127.0.0.1")):
        assert ct._is_safe_url("http://localhost:8007/openapi.json") is False


def test_is_safe_url_rejects_rfc1918_private_ranges():
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("192.168.1.1")):
        assert ct._is_safe_url("http://internal.example") is False
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("10.0.0.5")):
        assert ct._is_safe_url("http://internal.example") is False
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("172.16.0.1")):
        assert ct._is_safe_url("http://internal.example") is False


def test_is_safe_url_rejects_link_local_including_cloud_metadata():
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("169.254.169.254")):
        assert ct._is_safe_url("http://metadata.internal") is False


def test_is_safe_url_rejects_if_any_resolved_address_is_unsafe():
    # A hostname resolving to multiple addresses -- one public, one
    # private -- must be rejected entirely, not allowed through on
    # the public one (DNS rebinding-shaped risk).
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("93.184.216.34", "127.0.0.1")):
        assert ct._is_safe_url("http://mixed.example") is False


def test_is_safe_url_accepts_a_genuine_public_address():
    with patch.object(ct.socket, "getaddrinfo", return_value=_fake_resolved("93.184.216.34")):
        assert ct._is_safe_url("https://example.com/article") is True


def test_extract_text_from_url_refuses_unsafe_url_before_ever_calling_trafilatura():
    with (
        patch.object(ct, "_is_safe_url", return_value=False),
        patch.dict("sys.modules", {"trafilatura": MagicMock()}),
    ):
        import trafilatura

        result = ct.extract_text_from_url("http://127.0.0.1:8007/openapi.json")

    assert result["ok"] is False
    assert "Refused to fetch" in result["reason"]
    trafilatura.fetch_url.assert_not_called()


def test_extract_text_from_url_still_works_for_a_safe_url():
    fake_trafilatura = MagicMock()
    fake_trafilatura.fetch_url.return_value = "<html>real page</html>"
    fake_trafilatura.extract.return_value = "real article text"
    with (
        patch.object(ct, "_is_safe_url", return_value=True),
        patch.dict("sys.modules", {"trafilatura": fake_trafilatura}),
    ):
        result = ct.extract_text_from_url("https://example.com/article")

    assert result == {"ok": True, "text": "real article text"}
