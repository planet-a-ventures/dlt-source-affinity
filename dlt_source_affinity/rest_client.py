from typing import Any

import dlt
from dlt.sources.helpers.rest_client.auth import BearerTokenAuth, HttpBasicAuth
from dlt.sources.helpers.rest_client.client import RESTClient, Response
from dlt.sources.helpers.rest_client.paginators import (
    JSONLinkPaginator,
    JSONResponseCursorPaginator,
)

from .type_adapters import error_adapter
from .settings import API_BASE, V2_PREFIX
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dlt.sources.helpers.requests.session import Session


def create_session_with_retries(
    total_retries=3,
    backoff_factor=1,
    status_forcelist=(500, 502, 503, 504),
    allowed_methods=("GET", "POST", "PUT", "DELETE"),
    api_base: str = API_BASE,
):
    session = Session(raise_for_status=False)

    # Configure Retry
    retries = Retry(
        total=total_retries,  # Total number of retries
        backoff_factor=backoff_factor,  # Delay between retries: backoff_factor * (2 ** retry_attempt)
        status_forcelist=status_forcelist,  # HTTP status codes to retry on
        allowed_methods=allowed_methods,  # HTTP methods that are retried
        raise_on_status=False,  # Set to False to avoid raising errors on retriable status codes
    )

    # Attach the Retry configuration to the HTTPAdapter
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=1,
        pool_maxsize=100,
    )
    session.mount(api_base, adapter)

    return session


# Create a session with retries
session = create_session_with_retries(total_retries=5, backoff_factor=0.5)


def get_v2_rest_client(
    api_key: str = dlt.secrets["affinity_api_key"],
    api_base: str = API_BASE,
):
    return RESTClient(
        base_url=f"{api_base}{V2_PREFIX}",
        auth=BearerTokenAuth(api_key),
        data_selector="data",
        paginator=JSONLinkPaginator("pagination.nextUrl"),
        session=session,
    )


def get_v1_rest_client(
    api_key: str = dlt.secrets["affinity_api_key"],
    api_base: str = API_BASE,
):
    return RESTClient(
        base_url=api_base,
        auth=HttpBasicAuth("", api_key),
        paginator=JSONResponseCursorPaginator(
            cursor_path="next_page_token", cursor_param="page_token"
        ),
        session=session,
    )


def raise_if_error(response: Response, *args: Any, **kwargs: Any) -> None:
    if response.status_code < 200 or response.status_code >= 300:
        error = error_adapter.validate_json(response.text)
        response.reason = "\n".join([e.message for e in error.errors])
        response.raise_for_status()


hooks = {"response": [raise_if_error]}
MAX_PAGE_LIMIT_V1 = 500
MAX_PAGE_LIMIT_V2 = 100
