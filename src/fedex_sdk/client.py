from __future__ import annotations

import json
import time
import uuid
from threading import RLock
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Union
from urllib.parse import urlencode

from .config import FedExConfig
from .documents import (
    COMMERCIAL_INVOICE,
    FileSource,
    POSTSHIPMENT_WORKFLOW,
    PRESHIPMENT_WORKFLOW,
    attach_pre_shipment_documents,
    build_etd_document,
    extract_uploaded_document_id,
    read_upload_attachment,
    uploaded_document_reference,
)
from .errors import (
    FedExAPIError,
    FedExAuthenticationError,
    FedExRateLimitError,
    FedExValidationError,
)
from .models import AccessToken, FedExResponse
from .multipart import encode_multipart_form_data
from .transport import HttpResponse, Transport, UrlLibTransport

JsonObject = Mapping[str, Any]


class FedExClient:
    """Synchronous client for FedEx REST APIs.

    FedEx API schemas are large and evolve over time, so SDK methods accept
    dictionaries matching FedEx's request bodies and return parsed JSON.
    """

    def __init__(
        self,
        config: FedExConfig,
        *,
        transport: Optional[Transport] = None,
    ) -> None:
        self.config = config
        self._transport = transport or UrlLibTransport()
        self._token: Optional[AccessToken] = None
        self._lock = RLock()

    @classmethod
    def from_env(
        cls,
        *,
        env_file: Optional[str] = None,
        transport: Optional[Transport] = None,
    ) -> "FedExClient":
        return cls(FedExConfig.from_env(env_file=env_file), transport=transport)

    def __enter__(self) -> "FedExClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._transport.close()

    def get_access_token(self, *, force_refresh: bool = False) -> AccessToken:
        """Return a cached OAuth access token, refreshing when needed."""

        with self._lock:
            now = time.time()
            if (
                not force_refresh
                and self._token
                and not self._token.is_expired(now, self.config.token_refresh_margin)
            ):
                return self._token

            data: MutableMapping[str, str] = {
                "grant_type": self.config.grant_type,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
            }
            if self.config.child_key:
                data["child_key"] = self.config.child_key
            if self.config.child_secret:
                data["child_secret"] = self.config.child_secret

            response = self._send(
                "POST",
                "/oauth/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                body=urlencode(data).encode("utf-8"),
            )
            payload = self._parse_response(response)
            if not isinstance(payload, Mapping) or "access_token" not in payload:
                raise FedExAuthenticationError(
                    "FedEx OAuth response did not include an access token.",
                    status_code=response.status_code,
                    response=payload,
                    headers=response.headers,
                    transaction_id=self._transaction_id(response.headers),
                )

            expires_in = int(payload.get("expires_in", 3600))
            self._token = AccessToken(
                value=str(payload["access_token"]),
                token_type=str(payload.get("token_type", "bearer")),
                expires_at=time.time() + expires_in,
                scope=str(payload["scope"]) if payload.get("scope") else None,
            )
            return self._token

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[JsonObject] = None,
        query: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        authenticated: bool = True,
        transaction_id: Optional[str] = None,
        locale: Optional[str] = None,
        body: Optional[bytes] = None,
    ) -> FedExResponse:
        """Send a request to any FedEx REST endpoint."""

        if json_body is not None and body is not None:
            raise ValueError("Pass either json_body or body, not both.")

        request_headers: MutableMapping[str, str] = {
            "Accept": "application/json",
            "User-Agent": self.config.user_agent,
            "Content-Type": "application/json",
            "x-customer-transaction-id": transaction_id or str(uuid.uuid4()),
        }
        if locale:
            request_headers["X-locale"] = locale
        if headers:
            request_headers.update(headers)
        if authenticated:
            token = self.get_access_token()
            request_headers["Authorization"] = f"Bearer {token.value}"

        if json_body is not None:
            body = json.dumps(json_body, separators=(",", ":")).encode("utf-8")

        response = self._send(
            method,
            path,
            query=query,
            headers=request_headers,
            body=body,
        )
        data = self._parse_response(response)
        return FedExResponse(
            data=data,
            status_code=response.status_code,
            headers=response.headers,
            transaction_id=self._transaction_id(response.headers),
        )

    def post(
        self,
        path: str,
        payload: JsonObject,
        **kwargs: Any,
    ) -> FedExResponse:
        return self.request("POST", path, json_body=payload, **kwargs)

    def get(
        self,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> FedExResponse:
        return self.request("GET", path, query=query, **kwargs)

    def track_by_tracking_numbers(
        self,
        tracking_numbers: Sequence[str],
        *,
        include_detailed_scans: bool = False,
        **kwargs: Any,
    ) -> FedExResponse:
        payload = {
            "includeDetailedScans": include_detailed_scans,
            "trackingInfo": [
                {"trackingNumberInfo": {"trackingNumber": tracking_number}}
                for tracking_number in tracking_numbers
            ],
        }
        return self.post("/track/v1/trackingnumbers", payload, **kwargs)

    def rate_quotes(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/rate/v1/rates/quotes", payload, **kwargs)

    def create_shipment(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/ship/v1/shipments", payload, **kwargs)

    def validate_shipment(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/ship/v1/shipments/validate", payload, **kwargs)

    def cancel_shipment(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/ship/v1/shipments/cancel", payload, **kwargs)

    def validate_addresses(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/address/v1/addresses/resolve", payload, **kwargs)

    def find_locations(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/location/v1/locations", payload, **kwargs)

    def pickup_availability(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/pickup/v1/pickups/availabilities", payload, **kwargs)

    def create_pickup(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/pickup/v1/pickups", payload, **kwargs)

    def cancel_pickup(self, payload: JsonObject, **kwargs: Any) -> FedExResponse:
        return self.post("/pickup/v1/pickups/cancel", payload, **kwargs)

    def upload_etd_document(
        self,
        document: JsonObject,
        attachment: FileSource,
        *,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> FedExResponse:
        """Upload a FedEx electronic trade document using multipart/form-data."""

        part = read_upload_attachment(
            attachment,
            filename=filename,
            content_type=content_type or str(document.get("contentType", "")) or None,
        )
        document_payload = json.dumps(dict(document), separators=(",", ":"))
        body, multipart_content_type = encode_multipart_form_data(
            fields=[("document", document_payload, "application/json")],
            files=[("attachment", part.filename, part.content, part.content_type)],
        )
        return self.request(
            "POST",
            f"{self.config.resolved_document_base_url}/documents/v1/etds/upload",
            headers={"Content-Type": multipart_content_type},
            body=body,
            **kwargs,
        )

    def upload_commercial_invoice(
        self,
        attachment: FileSource,
        *,
        origin_country_code: str,
        destination_country_code: str,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        workflow_name: str = PRESHIPMENT_WORKFLOW,
        carrier_code: Optional[str] = None,
        form_code: Optional[str] = None,
        tracking_number: Optional[str] = None,
        shipment_date: Optional[str] = None,
        origin_location_code: Optional[str] = None,
        destination_location_code: Optional[str] = None,
        extra_meta: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> FedExResponse:
        """Upload a commercial invoice for pre- or post-shipment ETD."""

        part = read_upload_attachment(
            attachment,
            filename=filename,
            content_type=content_type,
        )
        document = build_etd_document(
            filename=part.filename,
            content_type=part.content_type,
            origin_country_code=origin_country_code,
            destination_country_code=destination_country_code,
            ship_document_type=COMMERCIAL_INVOICE,
            workflow_name=workflow_name,
            carrier_code=carrier_code,
            form_code=form_code,
            tracking_number=tracking_number,
            shipment_date=shipment_date,
            origin_location_code=origin_location_code,
            destination_location_code=destination_location_code,
            extra_meta=extra_meta,
        )
        return self.upload_etd_document(
            document,
            part.content,
            filename=part.filename,
            content_type=part.content_type,
            **kwargs,
        )

    def upload_post_shipment_commercial_invoice(
        self,
        attachment: FileSource,
        *,
        origin_country_code: str,
        destination_country_code: str,
        tracking_number: str,
        shipment_date: str,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        carrier_code: str = "FDXE",
        **kwargs: Any,
    ) -> FedExResponse:
        return self.upload_commercial_invoice(
            attachment,
            origin_country_code=origin_country_code,
            destination_country_code=destination_country_code,
            tracking_number=tracking_number,
            shipment_date=shipment_date,
            filename=filename,
            content_type=content_type,
            carrier_code=carrier_code,
            workflow_name=POSTSHIPMENT_WORKFLOW,
            **kwargs,
        )

    def commercial_invoice_reference(
        self,
        document_id: str,
        *,
        document_reference: Optional[str] = None,
        description: Optional[str] = "Commercial Invoice",
    ) -> dict[str, str]:
        return uploaded_document_reference(
            document_id=document_id,
            document_type=COMMERCIAL_INVOICE,
            document_reference=document_reference,
            description=description,
        )

    def uploaded_document_id(self, response: Union[FedExResponse, Any]) -> Optional[str]:
        data = response.data if isinstance(response, FedExResponse) else response
        return extract_uploaded_document_id(data)

    def with_pre_shipment_documents(
        self,
        shipment_payload: JsonObject,
        documents: list[Mapping[str, Any]],
        *,
        requested_document_types: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return attach_pre_shipment_documents(
            shipment_payload,
            documents,
            requested_document_types=requested_document_types,
        )

    def _send(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        body: Optional[bytes],
        query: Optional[Mapping[str, Any]] = None,
    ) -> HttpResponse:
        url = self._build_url(path, query)
        response = self._transport.request(
            method.upper(),
            url,
            headers=headers,
            body=body,
            timeout=self.config.timeout,
        )
        if response.status_code >= 400:
            payload = self._safe_json(response)
            message = self._error_message(payload) or f"FedEx API error {response.status_code}."
            error_type = FedExAPIError
            if response.status_code in {400, 422}:
                error_type = FedExValidationError
            elif response.status_code in {401, 403}:
                error_type = FedExAuthenticationError
            elif response.status_code == 429:
                error_type = FedExRateLimitError
            raise error_type(
                message,
                status_code=response.status_code,
                response=payload,
                headers=response.headers,
                transaction_id=self._transaction_id(response.headers),
            )
        return response

    def _build_url(self, path: str, query: Optional[Mapping[str, Any]]) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            base = path
        else:
            base = f"{self.config.resolved_base_url}/{path.lstrip('/')}"
        if not query:
            return base
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}{urlencode(query, doseq=True)}"

    def _parse_response(self, response: HttpResponse) -> Any:
        if not response.text:
            return None
        content_type = self._header(response.headers, "content-type") or ""
        if "json" in content_type.lower():
            return response.json()
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

    def _safe_json(self, response: HttpResponse) -> Any:
        try:
            return self._parse_response(response)
        except json.JSONDecodeError:
            return response.text

    def _error_message(self, payload: Any) -> Optional[str]:
        if isinstance(payload, Mapping):
            errors = payload.get("errors")
            if isinstance(errors, Sequence) and not isinstance(errors, (str, bytes)):
                messages = []
                for item in errors:
                    if isinstance(item, Mapping):
                        code = item.get("code")
                        message = item.get("message")
                        messages.append(
                            f"{code}: {message}" if code and message else str(message or code)
                        )
                messages = [message for message in messages if message]
                if messages:
                    return "; ".join(messages)
            for key in ("message", "error_description", "error"):
                value = payload.get(key)
                if value:
                    return str(value)
        return None

    def _transaction_id(self, headers: Mapping[str, str]) -> Optional[str]:
        return self._header(headers, "x-customer-transaction-id") or self._header(
            headers, "x-fedex-transaction-id"
        )

    def _header(self, headers: Mapping[str, str], name: str) -> Optional[str]:
        for key, value in headers.items():
            if key.lower() == name.lower():
                return value
        return None
