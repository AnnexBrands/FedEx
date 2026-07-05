"""Python SDK for FedEx REST APIs."""

from .addresses import (
    build_address_validation_request,
    extract_resolved_addresses,
    first_resolved_address,
)
from .client import FedExClient
from .config import Environment, FedExConfig
from .documents import (
    COMMERCIAL_INVOICE,
    ELECTRONIC_TRADE_DOCUMENTS,
    POSTSHIPMENT_WORKFLOW,
    PRESHIPMENT_WORKFLOW,
    attach_pre_shipment_documents,
    build_etd_document,
    extract_uploaded_document_id,
    uploaded_document_reference,
)
from .errors import (
    FedExAPIError,
    FedExAuthenticationError,
    FedExError,
    FedExRateLimitError,
    FedExValidationError,
)
from .models import AccessToken, FedExResponse
from .pickups import (
    build_pickup_availability_request,
    build_pickup_cancel_request,
    build_pickup_request,
    extract_pickup_confirmation,
)
from .rates import (
    build_rate_request,
    extract_rate_options,
    rate_request_from_ship_payload,
)

__all__ = [
    "AccessToken",
    "COMMERCIAL_INVOICE",
    "ELECTRONIC_TRADE_DOCUMENTS",
    "Environment",
    "FedExAPIError",
    "FedExAuthenticationError",
    "FedExClient",
    "FedExConfig",
    "FedExError",
    "FedExRateLimitError",
    "FedExResponse",
    "FedExValidationError",
    "POSTSHIPMENT_WORKFLOW",
    "PRESHIPMENT_WORKFLOW",
    "attach_pre_shipment_documents",
    "build_address_validation_request",
    "build_etd_document",
    "build_pickup_availability_request",
    "build_pickup_cancel_request",
    "build_pickup_request",
    "build_rate_request",
    "extract_pickup_confirmation",
    "extract_rate_options",
    "extract_resolved_addresses",
    "first_resolved_address",
    "rate_request_from_ship_payload",
    "extract_uploaded_document_id",
    "uploaded_document_reference",
]

__version__ = "0.1.0"
