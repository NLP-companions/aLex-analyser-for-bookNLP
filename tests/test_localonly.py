"""Only requests for this computer are answered, and changes only when they come from the analyser's own page (alex/localonly.py)."""
from __future__ import annotations

HOST = "127.0.0.1:8766"
CHANGE = ("/api/settings", {"conv_gap": 30})        # a request that changes something


def change(client, **headers):
    """Make the change request with the given headers (the Host is the analyser's own unless given)."""
    headers.setdefault("host", HOST)
    return client.post(CHANGE[0], json=CHANGE[1], headers=headers)


def conv_gap(client):
    """The conversation gap now in the settings."""
    return client.get("/api/library", headers={"host": HOST}).json()["settings"]["conv_gap"]


def test_the_page_and_the_data_are_served_to_127_0_0_1_and_localhost_with_or_without_a_port(client):
    for host in ("127.0.0.1", "127.0.0.1:8766", "localhost", "localhost:8766"):
        assert client.get("/", headers={"host": host}).status_code == 200, host
        assert client.get("/api/library", headers={"host": host}).status_code == 200, host


def test_another_name_for_this_computer_is_refused_whatever_the_method(client):
    """DNS rebinding: a page on evil.example made to resolve to 127.0.0.1 still sends its own name in Host."""
    for host in ("evil.example", "evil.example:8766", "127.0.0.1.evil.example", "127.0.0.1:8766@evil.example", "127.0.0.1:abc", "[::1]:8766", ""):
        assert client.get("/api/library", headers={"host": host}).status_code == 403, host
        assert client.post(CHANGE[0], json=CHANGE[1], headers={"host": host}).status_code == 403, host
    assert "127.0.0.1 or localhost" in client.get("/", headers={"host": "evil.example"}).json()["detail"]


def test_a_change_asked_for_by_another_web_page_is_refused_and_does_nothing(client):
    before = conv_gap(client)
    for origin in ("https://evil.example", "http://evil.example", "null", "http://localhost:8765",         # another site, a sandboxed page, another program here
                   "http://127.0.0.1:9999", "https://127.0.0.1:8766", "http://localhost:8766"):             # another port, https, another spelling of our host
        r = change(client, origin=origin)
        assert r.status_code == 403 and "another web page" in r.json()["detail"], origin
    assert conv_gap(client) == before


def test_a_change_from_our_own_page_or_from_a_script_goes_through(client):
    assert change(client, origin=f"http://{HOST}").status_code == 200                # the browser's own page: Origin is the server itself
    assert conv_gap(client) == 30
    CHANGE[1]["conv_gap"] = 31
    try:
        assert change(client).status_code == 200                                   # no Origin: curl or a script, not a web page
    finally:
        CHANGE[1]["conv_gap"] = 30
    assert conv_gap(client) == 31


def test_reading_is_not_refused_for_its_origin(client):
    """Reading changes nothing, and without permission headers a foreign page can't read the answer anyway."""
    r = client.get("/api/library", headers={"host": HOST, "origin": "https://evil.example"})
    assert r.status_code == 200 and "access-control-allow-origin" not in r.headers


def test_a_port_that_is_taken_is_noticed_before_the_server_starts():
    """Starting twice used to open the browser on the first instance and then fail with a socket error; now the start-up says so."""
    import socket
    from alex.app import port_in_use
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        port = s.getsockname()[1]
        assert port_in_use(port)
    assert not port_in_use(port)                                    # closed again


def test_reading_the_books_at_start_up_says_how_far_it_is(lib, monkeypatch, capsys):
    """The first start parses every book, which takes minutes for many novels: the terminal says so instead of staying silent."""
    import time
    from alex.app import warm_with_notes

    def slow_warm(progress=None):
        for done in (1, 2):
            time.sleep(0.12)
            progress(done, 2)

    monkeypatch.setattr(lib, "warm", slow_warm)
    warm_with_notes(lib, every=0.05)
    out = capsys.readouterr().out
    assert "still reading your books for the first time" in out and "all 2 books read" in out


TUNNEL = "abc-def.trycloudflare.com"       # a name given with --allow-host, as a Cloudflare quick tunnel forwards it


def tunnel_client(lib):
    """A client for an aLex started with `--allow-host abc-def.trycloudflare.com`."""
    from fastapi.testclient import TestClient
    from alex import app as app_module
    return TestClient(app_module.build_app(lib, allow_hosts=[TUNNEL]), base_url="http://127.0.0.1", raise_server_exceptions=False)


def test_an_allowed_host_is_answered_and_its_own_page_may_change_things(lib):
    """A demo through a tunnel: the tunnel's name is answered, and the page it serves (over https) counts as our own."""
    client = tunnel_client(lib)
    for host in (TUNNEL, TUNNEL.upper(), f"{TUNNEL}:443", HOST):                              # the local names still work too
        assert client.get("/api/library", headers={"host": host}).status_code == 200, host
    for origin in (f"https://{TUNNEL}", f"http://{TUNNEL}"):
        assert change(client, host=TUNNEL, origin=origin).status_code == 200, origin
    assert conv_gap(client) == 30


def test_an_allowed_host_opens_nothing_else(lib):
    """Only that exact name, and only changes from its own page; without --allow-host it is refused as before."""
    client = tunnel_client(lib)
    for host in ("other.trycloudflare.com", f"x.{TUNNEL}", f"{TUNNEL}.evil.example", f"{TUNNEL}:abc"):
        assert client.get("/api/library", headers={"host": host}).status_code == 403, host
    for origin in ("https://evil.example", "https://other.trycloudflare.com", f"https://{TUNNEL}:8443", "null"):
        assert change(client, host=TUNNEL, origin=origin).status_code == 403, origin
    assert change(client, origin=f"https://{HOST}").status_code == 403          # https is accepted only for an allowed name, not for this computer
    from fastapi.testclient import TestClient
    from alex import app as app_module
    plain = TestClient(app_module.build_app(lib), base_url="http://127.0.0.1", raise_server_exceptions=False)
    assert plain.get("/api/library", headers={"host": TUNNEL}).status_code == 403


def test_allow_host_takes_a_name_or_a_pasted_url_and_nothing_else():
    import pytest
    from alex.localonly import host_name
    assert host_name("abc-def.trycloudflare.com") == "abc-def.trycloudflare.com"
    assert host_name("  HTTPS://Abc-Def.TryCloudflare.com/ ") == "abc-def.trycloudflare.com"          # pasted from cloudflared's output
    for bad in ("", "*.trycloudflare.com", "abc.trycloudflare.com:443", "https://abc.trycloudflare.com/path", "a b.com", "-abc.com",
                "localhost", "127.0.0.1", "http://localhost/"):
        with pytest.raises(ValueError):
            host_name(bad)
