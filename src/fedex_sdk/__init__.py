"""Python SDK for FedEx REST APIs."""

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
    "build_etd_document",
    "extract_uploaded_document_id",
    "uploaded_document_reference",
]

__version__ = "0.1.0"
