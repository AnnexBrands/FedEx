# FedEx API SDK for Python

A lightweight, dependency-free Python SDK for FedEx REST APIs.

The SDK handles OAuth token creation and caching, common headers, JSON request
encoding, FedEx error responses, and stable convenience methods for core APIs.
FedEx request schemas are large and change over time, so API methods accept
plain dictionaries that match the official FedEx JSON payloads.

## Install

```bash
pip install -e .
```

## Configure

```bash
export FEDEX_CLIENT_ID="your project API key"
export FEDEX_CLIENT_SECRET="your project secret key"
export FEDEX_ACCOUNT_NUMBER="your FedEx account number"
export FEDEX_ENVIRONMENT="sandbox"  # or production
```

The SDK also accepts the shorter local aliases `FEDEX_CLIENT`,
`FEDEX_SECRET`, and `FEDEX_ACCOUNT`, and can load them from an env file:

```python
client = FedExClient.from_env(env_file="src/.env")
```

Then create a client:

```python
from fedex_sdk import FedExClient

client = FedExClient.from_env()
```

You can also configure it directly:

```python
from fedex_sdk import FedExClient, FedExConfig

client = FedExClient(
    FedExConfig(
        client_id="your project API key",
        client_secret="your project secret key",
        account_number="123456789",
        environment="sandbox",
    )
)
```

## Tracking

```python
from fedex_sdk import FedExClient

with FedExClient.from_env() as fedex:
    response = fedex.track_by_tracking_numbers(
        ["123456789012"],
        include_detailed_scans=True,
    )

print(response.data)
```

## Rates

```python
rate_request = {
    "accountNumber": {"value": "123456789"},
    "requestedShipment": {
        "shipper": {
            "address": {
                "postalCode": "38116",
                "countryCode": "US",
            }
        },
        "recipient": {
            "address": {
                "postalCode": "90210",
                "countryCode": "US",
            }
        },
        "pickupType": "DROPOFF_AT_FEDEX_LOCATION",
        "rateRequestType": ["ACCOUNT", "LIST"],
        "requestedPackageLineItems": [
            {
                "weight": {
                    "units": "LB",
                    "value": 5,
                }
            }
        ],
    },
}

with FedExClient.from_env() as fedex:
    response = fedex.rate_quotes(rate_request)
```

To keep quoted == booked, derive the rate request from the exact payload you
will send to `create_shipment`, and flatten the reply for comparison:

```python
from fedex_sdk import extract_rate_options

with FedExClient.from_env() as fedex:
    response = fedex.rate_from_ship_payload(shipment_payload)          # rate the pinned service
    shopped = fedex.rate_from_ship_payload(shipment_payload, all_services=True)

for option in extract_rate_options(response.data):
    print(option["serviceType"], option["totalNetCharge"], option["transitDays"])
```

## Shipments

```python
with FedExClient.from_env() as fedex:
    response = fedex.create_shipment(shipment_request)
    validation = fedex.validate_shipment(shipment_request)
    cancellation = fedex.cancel_shipment(cancel_request)
```

## Pre-Shipment Trade Documents

FedEx's Trade Documents Upload API uses a document-specific host and a
multipart request with two parts:

- `document`: JSON metadata, such as `workflowName`, `contentType`, and
  `meta.shipDocumentType`
- `attachment`: the commercial invoice PDF/image/document bytes

For a pre-shipment commercial invoice:

```python
from fedex_sdk import COMMERCIAL_INVOICE, FedExClient

with FedExClient.from_env(env_file="src/.env") as fedex:
    upload = fedex.upload_commercial_invoice(
        "commercial-invoice.pdf",
        origin_country_code="US",
        destination_country_code="CA",
        carrier_code="FDXE",
    )

    document_id = fedex.uploaded_document_id(upload)
    reference = fedex.commercial_invoice_reference(
        document_id,
        document_reference="job-123",
        description="Commercial Invoice",
    )

    shipment_payload = fedex.with_pre_shipment_documents(
        shipment_payload,
        [reference],
        requested_document_types=[COMMERCIAL_INVOICE],
    )

    response = fedex.create_shipment(shipment_payload)
```

The resulting shipment payload includes:

```json
{
  "requestedShipment": {
    "shipmentSpecialServices": {
      "specialServiceTypes": ["ELECTRONIC_TRADE_DOCUMENTS"],
      "etdDetail": {
        "attachedDocuments": [
          {
            "documentType": "COMMERCIAL_INVOICE",
            "documentId": "090493e181586308",
            "documentReference": "job-123",
            "description": "Commercial Invoice"
          }
        ],
        "requestedDocumentTypes": ["COMMERCIAL_INVOICE"]
      }
    }
  }
}
```

## Address Validation

```python
payload = {
    "addressesToValidate": [
        {
            "address": {
                "streetLines": ["10 FedEx Pkwy"],
                "city": "Memphis",
                "stateOrProvinceCode": "TN",
                "postalCode": "38115",
                "countryCode": "US",
            }
        }
    ]
}

with FedExClient.from_env() as fedex:
    response = fedex.validate_addresses(payload)
```

Or validate a single Ship-shaped address and get a decision-ready summary:

```python
from fedex_sdk import first_resolved_address

with FedExClient.from_env() as fedex:
    response = fedex.validate_address(
        {"streetLines": ["22 Blyth Hill Rd"], "city": "Toronto",
         "stateOrProvinceCode": "ON", "postalCode": "M4N 3L6", "countryCode": "CA"}
    )

resolved = first_resolved_address(response.data)
print(resolved["classification"], resolved["matched"], resolved["postalCode"])
```

## Locations and Pickups

```python
with FedExClient.from_env() as fedex:
    locations = fedex.find_locations(location_request)
    availability = fedex.pickup_availability(availability_request)
    pickup = fedex.create_pickup(pickup_request)
    cancellation = fedex.cancel_pickup(cancel_pickup_request)
```

Builder-backed conveniences (Express `FDXE` and Ground `FDXG` are separate
pickup networks — match the carrier code to the service being shipped):

```python
from fedex_sdk import extract_pickup_confirmation

with FedExClient.from_env() as fedex:
    availability = fedex.check_pickup_availability(
        {"postalCode": "30062", "countryCode": "US"},
        carriers=["FDXG"], dispatch_date="2026-07-06",
    )
    pickup = fedex.schedule_pickup(
        pickup_contact={"personName": "Navis 23030GA", "phoneNumber": "4049997225"},
        pickup_address={"streetLines": ["1061 Triad Ct"], "city": "Marietta",
                        "stateOrProvinceCode": "GA", "postalCode": "30062", "countryCode": "US"},
        ready_timestamp="2026-07-06T09:00:00Z",
        carrier_code="FDXG", package_count=1, total_weight_lb=7,
    )
    confirmation = extract_pickup_confirmation(pickup.data)
    cancelled = fedex.cancel_scheduled_pickup(
        confirmation_code=confirmation["confirmationCode"],
        scheduled_date="2026-07-06", carrier_code="FDXG",
    )
```

## Generic Requests

For APIs that do not have a named helper yet, call any FedEx endpoint directly:

```python
with FedExClient.from_env() as fedex:
    response = fedex.post("/track/v1/trackingnumbers", payload)
```

## Error Handling

```python
from fedex_sdk import FedExAPIError, FedExValidationError

try:
    FedExClient.from_env().rate_quotes(rate_request)
except FedExValidationError as exc:
    print(exc.status_code, exc.message, exc.transaction_id)
except FedExAPIError as exc:
    print(exc.status_code, exc.message)
```

## Supported Helpers

- `get_access_token(force_refresh=False)`
- `track_by_tracking_numbers(...)`
- `rate_quotes(payload)`
- `rate_from_ship_payload(ship_payload, all_services=False)`
- `create_shipment(payload)`
- `validate_shipment(payload)`
- `cancel_shipment(payload)`
- `validate_addresses(payload)`
- `validate_address(address)`
- `upload_etd_document(document, attachment, ...)`
- `upload_commercial_invoice(attachment, ...)`
- `upload_post_shipment_commercial_invoice(attachment, ...)`
- `commercial_invoice_reference(document_id, ...)`
- `uploaded_document_id(response)`
- `with_pre_shipment_documents(shipment_payload, documents, ...)`
- `find_locations(payload)`
- `pickup_availability(payload)` / `check_pickup_availability(address, ...)`
- `create_pickup(payload)` / `schedule_pickup(...)`
- `cancel_pickup(payload)` / `cancel_scheduled_pickup(...)`
- `get(path, query=...)`, `post(path, payload)`, and `request(...)`

## Development

```bash
python -m unittest
python -m compileall src tests
```

## FedEx Documentation

- FedEx Developer Portal: https://developer.fedex.com/api/en-us/home.html
- OAuth Authorization API: https://developer.fedex.com/api/en-us/catalog/authorization/v1/docs.html
- Tracking API: https://developer.fedex.com/api/en-us/catalog/track/v1/docs.html
- Rates and Transit Times API: https://developer.fedex.com/api/en-us/catalog/rate/v1/docs.html
- Ship API: https://developer.fedex.com/api/en-us/catalog/ship/v1/docs.html
- Address Validation API: https://developer.fedex.com/api/en-us/catalog/address-validation/v1/docs.html
- Locations Search API: https://developer.fedex.com/api/en-us/catalog/locations/v1/docs.html
- Pickup Request API: https://developer.fedex.com/api/en-us/catalog/pickup/v1/docs.html
