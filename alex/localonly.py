"""Keep the analyser's web server for you alone: refuse requests that other web pages could make through your browser.

aLex listens on 127.0.0.1, so no other computer can reach it. But *your browser* can reach it, and a web page you happen to have open
in another tab can make the browser do so. Two checks close that gap (both are about the request's headers, which a web page can't forge):

* **Host.** A page on another domain can be tricked ("DNS rebinding") into reaching 127.0.0.1 under its own domain name; the request then
  names that domain in `Host`. Only `127.0.0.1` and `localhost` are answered.
* **Origin.** A page on another site can make your browser *send* a request that changes something (a POST), even if it can't read the
  answer. Browsers say where such a request comes from in `Origin`, so a request that changes something, and names an origin other than
  this very server (same host *and* port, so another program on your computer doesn't count either), is refused. Requests with no
  `Origin` (scripts, `curl`) are fine: only a browser can be used against you this way.

Reading requests (GET) change nothing in aLex, and the answers carry no permission for other sites to read them, so they need only the Host check.

**Extra hosts** (`alex --allow-host NAME`, off by default) are for showing aLex to someone else through a tunnel (e.g. Cloudflare's), which
forwards requests for a public name such as `abc.trycloudflare.com` to this computer. That name is then answered too, and a change from a
page at `http://NAME` or `https://NAME` (the tunnel serves https) counts as our own page. Each name must be given exactly: no wildcards.
"""
from __future__ import annotations

import re

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

LOCAL_HOSTS = ("127.0.0.1", "localhost")
READING = ("GET", "HEAD", "OPTIONS")        # methods that change nothing
HOST_NAME = re.compile(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*")


def host_name(text: str) -> str:
    """The host name in `text` for `--allow-host`, lower-cased: a bare name, or a URL pasted as is (`https://abc.trycloudflare.com/`).
    Raises `ValueError` for anything else (a port, a path, a wildcard, an empty name, or a local name, which is always answered anyway)."""
    name = re.sub(r"^[a-z]+://", "", text.strip().lower()).rstrip("/")
    if not HOST_NAME.fullmatch(name) or len(name) > 253:
        raise ValueError(f"“{text}” is not a host name (give it like abc.trycloudflare.com: no port, path or wildcard).")
    if name in LOCAL_HOSTS:
        raise ValueError(f"“{text}” is always answered; --allow-host is for another name.")
    return name


class LocalOnly:
    """ASGI middleware: answer only requests addressed to this computer (`hosts`) or to one of the `extra_hosts` (see the module notes) and,
    for those that change something, sent by our own page."""

    def __init__(self, app, hosts=LOCAL_HOSTS, extra_hosts=()):
        self.app = app
        self.hosts = tuple(hosts)
        self.extra_hosts = tuple(h.lower() for h in extra_hosts)

    async def __call__(self, scope, receive, send):
        """Pass the request on, or refuse it with 403 and a message the interface can show."""
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            host = headers.get("host", "")
            origin = headers.get("origin")
            name, _, port = host.partition(":")
            extra = name.lower() in self.extra_hosts
            if not (name in self.hosts or extra) or not (port == "" or port.isdigit()):
                return await self._refuse(scope, receive, send, "aLex only answers requests addressed to 127.0.0.1 or localhost.")
            ours = (f"http://{host}", f"https://{host}") if extra else (f"http://{host}",)     # a tunnel serves https
            if scope["method"] not in READING and origin is not None and origin.lower() not in (o.lower() for o in ours):
                return await self._refuse(scope, receive, send, "aLex refused a change requested by another web page.")
        await self.app(scope, receive, send)

    @staticmethod
    async def _refuse(scope, receive, send, message):
        """Send the 403 reply."""
        await JSONResponse({"detail": message}, status_code=403)(scope, receive, send)
