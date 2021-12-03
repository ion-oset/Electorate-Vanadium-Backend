from typing import Optional, Union

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from vanadium.app.resources import storage as storage_resource
from vanadium.models.nist.vri import (
    Error,
    RequestAcknowledgement,     # VoterRecordsResponse sub-class
    RequestError,
    RequestRejection,           # VoterRecordsResponse sub-class
    RequestSuccess,             # VoterRecordsResponse sub-class
    SuccessAction,
    VoterRecordsRequest,
)
from vanadium.utils import UniqueIds


# --- Routes

_router = APIRouter(prefix = "/voter/registration")

@_router.post(
    "/",
    response_model = Union[RequestSuccess, RequestRejection],
    response_model_exclude_unset = True,
    # response_model_exclude_none = True,
    response_description = "Voter registration response",
    summary = "Initiate a new voter registration request",
)
def voter_registration_request(
    item: VoterRecordsRequest,
    http_response: Response,
    storage = Depends(storage_resource.get_storage),
):
    """Create a new voter registration request.

    Does not really register a voter, only returns responses as if it had.

    **Parameters**:

    `item (VoterRecordsRequest)`: Request data from client.
    The request must include the following fields.
    Other fields are not yet processed.

    - `Form` to indicate which other fields to expect.
    - `GeneratedDate` to define when the request was generated by the client.
    - `Type` *must* be `VoterRequestType.REGISTRATION`.
    - `TransactionId` which can be the ID to use for the voter registration.
       If not set one will be generated.

    `http_response (Response)`: A response to set status codes on.

    **Returns**:

    - `RequestSuccess` on success.
       The voter registration request was successful and a unique ID was
       generated.

        A successful response includes the following fields:

        - `Action` is set to `"registration-created"`.
        - `TransactionId` is the generated unique ID for the request.
           Used in subsequent API calls to track the status of the request.

        **Status Code**: `HTTP 201: Created`.

    - `RequestRejection` on failure
       The voter registration request was unsuccessful.

        An unsuccessful response includes the following fields:

        - `AdditionalDetails` is a list of human readable explanations.
        - `Error` is a list of machine readable codes explaining the failure.
        - `TransactionId` is null.

        **Status Code**: `HTTP 400: Bad Request`.

    **Notes**:

    - Important: `TransactionId` is hijacked to be a unique identifier
      for the voter, in the absence of other voter information.
    - There's considerable debate on what status code to return when
      registration fails because an entity already exists.

      See: ["HTTP response code for POST when resource already exists"](https://stackoverflow.com/q/3825990)

    **Todo**:

    - Add actual voter information using `Subject`.
    - Do not allow setting `TransactionId`.
    - Status code on failure depends on circumstance:
        - A request has already been made and is in progress.
        - A request has already been made and is completed.
    """
    registration_id = storage.insert(item.transaction_id, item)
    if registration_id:
        response = RequestSuccess(
            Action = [
                SuccessAction.REGISTRATION_CREATED,
            ],
            TransactionId = registration_id
        )
        http_response.status_code = status.HTTP_201_CREATED
    else:
        response = RequestRejection(
            AdditionalDetails = [
                "Voter registration request already exists. "
                "The transaction ID is already associated to a pending request."
            ],
            Error = [
                Error(Name = RequestError.IDENTITY_LOOKUP_FAILED),
            ],
            TransactionId = registration_id
        )
        # TODO: Look into this.
        # This isn't right. The request was valid, it's that the action requested
        # doesn't need to be taken.
        http_response.status_code = status.HTTP_400_BAD_REQUEST
    return response


@_router.get(
    "/{transaction_id}",
    response_model = Union[RequestAcknowledgement, RequestRejection],
    response_model_exclude_unset = True,
    response_description = "Voter registration response",
    summary = "Check on the status of a pending voter registration request"
)
def voter_registration_status(
    transaction_id,
    http_response: Response,
    storage = Depends(storage_resource.get_storage),
):
    """Status of voter registration.

    **Parameters**:

    `transaction_id (UUID)`: Voter request ID from the initial transaction.

    `http_response (Response)`: A response to set status codes on.

    **Returns**:

    - `RequestAcknowledgement` on success.
       The matching voter registration was found,

        A successful response includes the following fields:

        - `TransactionId` is the generated unique ID for the transaction.
          It should match the `transaction_id` parameter.

        Note: This record doesn't allow returning any details about the status.

        **Status Code**: `HTTP 200: Success`.

    - `RequestRejection` on failure.
      No matching voter registration was found.

        An unsuccessful response includes the following fields:

        - `AdditionalDetails` is a list of human readable explanations.
        - `Error` is a list of machine readable codes explaining the failure.
        - `TransactionId` is the unique ID that failed.
          It should match the `transaction_id` parameter.

        **Status Code**: `HTTP 404: Not Found`.

    **Notes**:

    - Important: `TransactionId` is hijacked to be a unique identifier
      for the voter, in the absence of other voter information.

    **Todo**:

    - Use `VoterRecordsRequest` to make the request not transaction ID.
    - Do not allow setting `TransactionId`.
    - Allow lookup through via voter information in `Subject`.
    """
    value = storage.lookup(transaction_id)
    if value:
        response = RequestAcknowledgement(
            # There's no way to pass a descriptive message with an Acknowledgement
            # "Transaction request is in process"
            TransactionId = transaction_id
        )
    else:
        response = RequestRejection(
            AdditionalDetails = [
                "Voter registration request not found. "
                "The transaction ID isn't associated with any pending requests."
            ],
            Error = [
                Error(Name = RequestError.IDENTITY_LOOKUP_FAILED)
            ],
            TransactionId = transaction_id
        )
        http_response.status_code = status.HTTP_404_NOT_FOUND
    return response


@_router.put(
    "/{transaction_id}",
    response_model = Union[RequestSuccess, RequestRejection],
    response_model_exclude_unset = True,
    response_description = "Voter registration response",
    summary = "Update a pending voter registration request"
)
def voter_registration_update(
    transaction_id,
    item: VoterRecordsRequest,
    http_response: Response,
    storage = Depends(storage_resource.get_storage),
):
    """Update an existing voter registration.

    **Parameters**:

    `transaction_id (UUID)`: The transaction ID as returned in the initial
    transaction.

    `item (VoterRecordsRequest)`: Request data from client.
    The request must include the following fields.
    Other fields are not processed / ignored.

    - `Form` to indicate which other fields to expect.
    - `GeneratedDate` to define when the request was generated by the client.
    - `Type` *must* be `VoterRequestType.REGISTRATION`.
    - `TransactionId` which can be the ID to use for the voter registration.
       If not set one will be generated.

    `http_response (Response)`: A response to set status codes on.

    **Returns**:

    - `RequestSuccess` on success.
       The voter registration was updated.

        A successful response includes the following fields:

        - `Action` is set to `"registration-updated"`.
        - `TransactionId` is the unique ID for the transaction.
           It should match the `transaction_id` parameter.

        **Status Code**: `HTTP 200: Success`.

    - `RequestRejection` on failure.
       No matching voter registration was found.

        An unsuccessful response includes the following fields:

        - `AdditionalDetails` is a list of human readable explanations.
        - `Error` is a list of machine readable codes explaining the failure.
        - `TransactionId` is the unique ID that failed.
          It should match the `transaction_id` parameter.

        **Status Code**: `HTTP 404: Not Found`.

    **Notes**:

    - Important: `TransactionId` is hijacked to be a unique identifier
      for the voter, in the absence of other voter information.

    **Todo**:

    - Use `VoterRecordsRequest` to make the request not transaction ID.
    - Do not allow setting `TransactionId`.
    - Allow lookup through via voter information in `Subject`.
    """
    value = storage.update(transaction_id, item)
    if value:
        response = RequestSuccess(
            Action = [
                SuccessAction.REGISTRATION_UPDATED,
            ],
            TransactionId = transaction_id
        )
    else:
        response = RequestRejection(
            AdditionalDetails = [
                "Voter registration request not found. "
                "The transaction ID isn't associated with any pending requests."
            ],
            Error = [
                Error(Name = RequestError.IDENTITY_LOOKUP_FAILED)
            ],
            TransactionId = transaction_id
        )
        http_response.status_code = status.HTTP_404_NOT_FOUND
    return response


@_router.delete(
    "/{transaction_id}",
    response_model = Union[RequestSuccess, RequestRejection],
    response_model_exclude_unset = True,
    response_description = "Voter registration response",
    summary = "Cancel a pending voter registration request"
)
def voter_registration_cancel(
    transaction_id,
    http_response: Response,
    storage = Depends(storage_resource.get_storage),
):
    """Delete an existing voter registration.

    **Parameters**:

    `transaction_id (UUID)`: Voter request ID from the initial transaction.

    `http_response (Response)`: A response to set status codes on.

    **Returns**:

    - `RequestSuccess` on success.
       The voter registration was deleted.

        A successful response includes the following fields:

        - `Action` is set to `"registration-cancelled"`.
        - `TransactionId` is the unique ID for the transaction.
           It should match the `transaction_id` parameter.

        **Status Code**: `HTTP 200: Success`.

    - `RequestRejection` on failure.
       No matching voter registration was found.

        An unsuccessful response includes the following fields:

        - `AdditionalDetails` is a list of human readable explanations.
        - `Error` is a list of machine readable codes explaining the failure.
        - `TransactionId` is the unique ID that failed.
          It should match the `transaction_id` parameter.

        **Status Code**: `HTTP 404: Not Found`.

    **Notes**:

    - Important: `TransactionId` is hijacked to be a unique identifier
      for the voter, in the absence of other voter information.`

    **Todo**:

    - Use `VoterRecordsRequest` to make the request not transaction ID.
    - Do not allow setting `TransactionId`.
    - Allow lookup through via voter information in `Subject`.
    """
    value = storage.remove(transaction_id)
    if value:
        response = RequestSuccess(
            Action = [
                SuccessAction.REGISTRATION_CANCELLED,
            ],
            TransactionId = transaction_id
        )
    else:
        response = RequestRejection(
            AdditionalDetails = [
                "Voter registration request not found. "
                "The transaction ID isn't associated with any pending requests."
            ],
            Error = [
                Error(Name = RequestError.IDENTITY_LOOKUP_FAILED)
            ],
            TransactionId = transaction_id
        )
        http_response.status_code = status.HTTP_404_NOT_FOUND
    return response


# --- Router

_routers = [
    _router
]

def router():
    return _router