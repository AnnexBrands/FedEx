from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Optional, Protocol


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    text: str

    def json(self) -> object:
        if not self.text:
            return None
        return json.loads(self.text)


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> HttpResponse:
        ...

    def close(self) -> None:
        ...


class UrlLibTransport:
    """Small urllib-based transport to keep the SDK dependency-free."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> HttpResponse:
        req = urllib.request.Request(
            url=url,
            data=body,
            headers=dict(headers),
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
                return HttpResponse(
                    status_code=response.status,
                    headers=dict(response.headers.items()),
                    text=payload,
                )
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8")
            return HttpResponse(
                status_code=exc.code,
                headers=dict(exc.headers.items()),
                text=payload,
            )

    def close(self) -> None:
        return None
