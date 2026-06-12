import certifi
import httpx

from remediation.config import settings


def tls_verify() -> bool | str:
    return certifi.where() if settings.http_ssl_verify else False


def http_client(timeout: int = 30) -> httpx.Client:
    return httpx.Client(timeout=timeout, verify=tls_verify())
