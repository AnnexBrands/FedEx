from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Union

Environment = Literal["sandbox", "production"]

SANDBOX_BASE_URL = "https://apis-sandbox.fedex.com"
PRODUCTION_BASE_URL = "https://apis.fedex.com"
SANDBOX_DOCUMENT_BASE_URL = "https://documentapitest.prod.fedex.com/sandbox"
PRODUCTION_DOCUMENT_BASE_URL = "https://documentapi.prod.fedex.com"


@dataclass(frozen=True)
class FedExConfig:
    """Configuration for the FedEx REST API client."""

    client_id: str
    client_secret: str
    account_number: Optional[str] = None
    environment: Environment = "sandbox"
    base_url: Optional[str] = None
    document_base_url: Optional[str] = None
    timeout: float = 30.0
    user_agent: str = "fedex-api-sdk-python/0.1.0"
    grant_type: str = "client_credentials"
    child_key: Optional[str] = None
    child_secret: Optional[str] = None
    token_refresh_margin: int = 60

    @property
    def resolved_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.environment == "production":
            return PRODUCTION_BASE_URL
        return SANDBOX_BASE_URL

    @property
    def resolved_document_base_url(self) -> str:
        if self.document_base_url:
            return self.document_base_url.rstrip("/")
        if self.environment == "production":
            return PRODUCTION_DOCUMENT_BASE_URL
        return SANDBOX_DOCUMENT_BASE_URL

    @classmethod
    def from_env(cls, env_file: Optional[Union[str, os.PathLike[str]]] = None) -> "FedExConfig":
        """Create config from FEDEX_* environment variables."""

        values = _load_env_file(env_file) if env_file else {}

        client_id = _env("FEDEX_CLIENT_ID", "FEDEX_CLIENT", values=values)
        client_secret = _env("FEDEX_CLIENT_SECRET", "FEDEX_SECRET", values=values)
        if not client_id or not client_secret:
            raise ValueError(
                "FEDEX_CLIENT_ID/FEDEX_CLIENT and FEDEX_CLIENT_SECRET/FEDEX_SECRET "
                "are required to build FedExConfig."
            )

        environment = _env("FEDEX_ENVIRONMENT", values=values, default="sandbox").lower()
        if environment not in {"sandbox", "production"}:
            raise ValueError("FEDEX_ENVIRONMENT must be 'sandbox' or 'production'.")

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            account_number=_env("FEDEX_ACCOUNT_NUMBER", "FEDEX_ACCOUNT", values=values),
            environment=environment,  # type: ignore[arg-type]
            base_url=_env("FEDEX_BASE_URL", values=values),
            document_base_url=_env("FEDEX_DOCUMENT_BASE_URL", values=values),
            grant_type=_env("FEDEX_GRANT_TYPE", values=values, default="client_credentials"),
            child_key=_env("FEDEX_CHILD_KEY", values=values),
            child_secret=_env("FEDEX_CHILD_SECRET", values=values),
        )


def _env(*names: str, values: dict[str, str], default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    for name in names:
        value = values.get(name)
        if value:
            return value
    return default


def _load_env_file(env_file: Union[str, os.PathLike[str]]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path(env_file).read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
