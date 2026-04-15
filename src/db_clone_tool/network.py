"""
Network helpers — currently only host rewriting for Docker.

Users connecting from inside a Docker container expect `localhost` to mean
"the host machine that's running this container", not the container's own
loopback. Docker doesn't bridge those automatically, so we transparently
rewrite loopback addresses to `host.docker.internal` when we detect we're
containerised. Outside Docker this is a no-op.
"""
import socket
from pathlib import Path


_LOOPBACK_HOSTS = {'localhost', '127.0.0.1', '::1', '0.0.0.0'}
_DOCKER_HOST = 'host.docker.internal'


def _is_in_docker() -> bool:
    """Best-effort check — `/.dockerenv` is created by Docker inside the container."""
    return Path('/.dockerenv').exists()


def _docker_host_resolvable() -> bool:
    """Only rewrite if the replacement actually resolves. On Linux Docker
    without `--add-host host-gateway` the name isn't set up, in which case
    rewriting would just swap one failure for another."""
    try:
        socket.gethostbyname(_DOCKER_HOST)
        return True
    except socket.gaierror:
        return False


def resolve_db_host(host: str) -> str:
    """Rewrite loopback hosts to host.docker.internal when running in Docker.

    Users typing 'localhost' in the UI naturally expect to reach DBs running
    on their host machine — matching the behaviour of every other client.
    This makes that work without forcing users to know Docker networking.
    """
    if not host:
        return host
    if host.lower() not in _LOOPBACK_HOSTS:
        return host
    if not _is_in_docker():
        return host
    if not _docker_host_resolvable():
        return host
    return _DOCKER_HOST
