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
from dlt.sources.helpers.requests.session import Session


# Share a session (and thus pool) between all rest clients
session: Session = None


def get_v2_rest_client(
    api_key: str = dlt.secrets["affinity_api_key"],
    api_base: str = API_BASE,
):
    global session
    client = RESTClient(
        base_url=f"{api_base}{V2_PREFIX}",
        auth=BearerTokenAuth(api_key),
        data_selector="data",
        paginator=JSONLinkPaginator("pagination.nextUrl"),
        session=session,
    )
    if not session:
        session = client.session
    return client


def get_v1_rest_client(
    api_key: str = dlt.secrets["affinity_api_key"],
    api_base: str = API_BASE,
):
    global session
    client = RESTClient(
        base_url=api_base,
        auth=HttpBasicAuth("", api_key),
        paginator=JSONResponseCursorPaginator(
            cursor_path="next_page_token", cursor_param="page_token"
        ),
        session=session,
    )
    if not session:
        session = client.session
    return client


def raise_if_error(response: Response, *args: Any, **kwargs: Any) -> None:
    if response.status_code < 200 or response.status_code >= 300:
        error = error_adapter.validate_json(response.text)
        response.reason = "\n".join([e.message for e in error.errors])
        response.raise_for_status()


hooks = {"response": [raise_if_error]}
MAX_PAGE_LIMIT_V1 = 500
MAX_PAGE_LIMIT_V2 = 100
