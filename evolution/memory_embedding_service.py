"""Authenticated host-side embeddings for dependency-free memory MCP clients."""

from __future__ import annotations

import atexit
import json
import os
import secrets
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from evolution.semantic_embeddings import EmbeddingConfigurationError, embed_texts

MEMORY_EMBEDDING_ENDPOINT_ENV = "SKILLFLOW_MEMORY_EMBEDDING_ENDPOINT"
MEMORY_EMBEDDING_TOKEN_ENV = "SKILLFLOW_MEMORY_EMBEDDING_TOKEN"
MEMORY_EMBEDDING_MODEL_ENV = "SKILLFLOW_MEMORY_EMBEDDING_MODEL"
MEMORY_EMBEDDING_DISABLED_ENV = "SKILLFLOW_MEMORY_EMBEDDING_DISABLED"


@dataclass(frozen=True)
class MemoryEmbeddingRuntime:
    endpoint: str
    token: str
    model_name: str

    @property
    def container_env(self) -> dict[str, str]:
        return {
            MEMORY_EMBEDDING_ENDPOINT_ENV: self.endpoint,
            MEMORY_EMBEDDING_TOKEN_ENV: self.token,
        }


class _EmbeddingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], token: str, model_name: str) -> None:
        super().__init__(address, _EmbeddingHandler)
        self.auth_token = token
        self.model_name = model_name
        self.encode_lock = threading.Lock()


class _EmbeddingHandler(BaseHTTPRequestHandler):
    server: _EmbeddingHTTPServer

    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _json_response(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/embed":
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        supplied = self.headers.get("Authorization", "")
        if not secrets.compare_digest(supplied, f"Bearer {self.server.auth_token}"):
            self._json_response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 256_000:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid_body"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
            text = str(payload.get("text") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            text = ""
        if not text:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "empty_text"})
            return
        with self.server.encode_lock:
            vector = embed_texts([text], model_name=self.server.model_name)[0]
        self._json_response(
            HTTPStatus.OK,
            {"model": self.server.model_name, "embedding": vector.tolist()},
        )


_runtime_lock = threading.Lock()
_runtime: MemoryEmbeddingRuntime | None = None
_server: _EmbeddingHTTPServer | None = None
_thread: threading.Thread | None = None


def memory_embedding_model_name() -> str:
    return (
        os.environ.get(MEMORY_EMBEDDING_MODEL_ENV, "").strip()
        or os.environ.get("SKILLFLOW_EMBEDDING_MODEL", "").strip()
        or "all-MiniLM-L6-v2"
    )


def ensure_memory_embedding_service(model_name: str | None = None) -> MemoryEmbeddingRuntime | None:
    """Start one local embedding service and return container-facing settings."""
    global _runtime, _server, _thread
    if os.environ.get(MEMORY_EMBEDDING_DISABLED_ENV, "").strip() == "1":
        return None
    with _runtime_lock:
        if _runtime is not None:
            return _runtime if not model_name or _runtime.model_name == model_name else None
        model_name = model_name or memory_embedding_model_name()
        try:
            # Fail before publishing an endpoint. This also warms the model for
            # the first task-side query.
            embed_texts(["memory retrieval readiness"], model_name=model_name)
        except EmbeddingConfigurationError:
            return None
        token = secrets.token_urlsafe(32)
        bind_host = os.environ.get("SKILLFLOW_MEMORY_EMBEDDING_BIND", "0.0.0.0")
        try:
            server = _EmbeddingHTTPServer((bind_host, 0), token, model_name)
        except OSError:
            # Restricted CI/sandbox environments may forbid listening sockets.
            # The MCP server will advertise and use its strict lexical fallback.
            return None
        port = int(server.server_address[1])
        thread = threading.Thread(
            target=server.serve_forever,
            name="skillflow-memory-embeddings",
            daemon=True,
        )
        thread.start()
        runtime = MemoryEmbeddingRuntime(
            endpoint=f"http://host.docker.internal:{port}/embed",
            token=token,
            model_name=model_name,
        )
        os.environ.update(runtime.container_env)
        _server = server
        _thread = thread
        _runtime = runtime
        return runtime


def _shutdown_memory_embedding_service() -> None:
    global _runtime, _server, _thread
    if _server is not None:
        _server.shutdown()
        _server.server_close()
    _runtime = None
    _server = None
    _thread = None


atexit.register(_shutdown_memory_embedding_service)
