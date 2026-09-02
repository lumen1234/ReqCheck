"""Combined ASGI application for the Flask UI/API and Streamable HTTP MCP."""

import contextlib
import os
from urllib.parse import urlsplit

from asgiref.wsgi import WsgiToAsgi
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route

from app import app as flask_app
from app.mcp_server import mcp


def _transport_security() -> TransportSecuritySettings:
    public_url = urlsplit(flask_app.config["PUBLIC_BASE_URL"])
    allowed_hosts = ["localhost:*", "127.0.0.1:*", "[::1]:*"]
    allowed_origins = ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]
    if public_url.netloc:
        allowed_hosts.append(public_url.netloc)
        allowed_origins.append(f"{public_url.scheme}://{public_url.netloc}")
    allowed_hosts.extend(
        value.strip() for value in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if value.strip()
    )
    allowed_origins.extend(
        value.strip() for value in os.environ.get("MCP_ALLOWED_ORIGINS", "").split(",") if value.strip()
    )
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=list(dict.fromkeys(allowed_hosts)),
        allowed_origins=list(dict.fromkeys(allowed_origins)),
    )


mcp_http_app = mcp.streamable_http_app(
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    transport_security=_transport_security(),
    host="0.0.0.0",
)


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield


application = Starlette(
    routes=[
        Route("/mcp", endpoint=lambda _: RedirectResponse("/mcp/", status_code=307)),
        Mount("/mcp", app=mcp_http_app, name="mcp"),
        Mount("/", app=WsgiToAsgi(flask_app), name="flask"),
    ],
    lifespan=lifespan,
)
