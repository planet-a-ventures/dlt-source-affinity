import json
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


def print_response(response: Response, *args: Any, **kwargs: Any) -> None:
    """
    Prints the response URL and text for debugging purposes.
    """
    print(f"URL: {response.url}")
    print(f"Response: {response.text}")


def remove_unknown_fields(response: Response, *args: Any, **kwargs: Any) -> None:
    """
    Workaround for https://github.com/planet-a-ventures/dlt-source-affinity/issues/11
    Removes unknown fields from the response.
    This is a workaround for the fact that the API returns unknown fields that are not part of the schema.
    We remove these fields to avoid errors when validating the data.
    TODO: remove this when the API is fixed. ASAP. And because this makes me really sad; again: ASAP.
    """
    if "application/json" in response.headers.get("Content-Type", ""):
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            items = data["data"]
            changed = False
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "entity" in item:
                        entity = item["entity"]
                        if isinstance(entity, dict) and "fields" in entity:
                            fields = entity["fields"]
                            if isinstance(fields, list):
                                to_remove = []
                                for field in fields:
                                    if isinstance(field, dict) and (
                                        field["value"]["type"] == "connections"
                                        or field["value"]["type"] == "note"
                                    ):
                                        to_remove.append(field)
                                        changed = True
                                for field in to_remove:
                                    fields.remove(field)
            if changed:
                response._content = json.dumps(data).encode("utf-8")


hooks = {
    "response": [
        # print_response,
        raise_if_error,
        # TODO: remove this when the API is fixed.
        # Workaround for https://github.com/planet-a-ventures/dlt-source-affinity/issues/11
        remove_unknown_fields,
    ]
}
MAX_PAGE_LIMIT_V1 = 500
MAX_PAGE_LIMIT_V2 = 100
