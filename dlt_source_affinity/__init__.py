"""A source loading entities and lists from Affinity CRM (affinity.co)"""

from copy import deepcopy
from dataclasses import field
from enum import StrEnum
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence
import logging
import dlt
from dlt.common.typing import TDataItem
from dlt.sources import DltResource
from dlt.extract.items import DataItemWithMeta
from dlt.common.logger import is_logging
from dlt.common.schema.typing import TTableReferenceParam
from dlt.common.libs.pydantic import DltConfig
from pydantic_flatten_rootmodel import flatten_root_model
from pydantic import TypeAdapter
from pydantic.fields import FieldInfo
from .rest_client import (
    get_v1_rest_client,
    get_v2_rest_client,
    hooks,
    MAX_PAGE_LIMIT_V1,
    MAX_PAGE_LIMIT_V2,
)
from .type_adapters import note_adapter, list_adapter
from .model.v1 import Note, InteractionTypeToLiteral
from .model.v2 import *
from .helpers import ListReference, generate_list_entries_path


if is_logging():
    # ignore https://github.com/dlt-hub/dlt/blob/268768f78bd7ea7b2df8ca0722faa72d4d4614c5/dlt/extract/hints.py#L390-L393
    # This warning is thrown because of using Pydantic models as the column schema in a table variant
    # The reason we need to use variants, however, is https://github.com/dlt-hub/dlt/pull/2109
    class HideSpecificWarning(logging.Filter):
        def filter(self, record):
            if (
                "A data item validator was created from column schema"
                in record.getMessage()
            ):
                return False  # Filter out this log
            return True  # Allow all other logs

    logger = logging.getLogger("dlt")
    logger.addFilter
    logger.addFilter(HideSpecificWarning())

LISTS_LITERAL = Literal["lists"]


class Table(StrEnum):
    COMPANIES = "companies"
    PERSONS = "persons"
    OPPORTUNITIES = "opportunities"
    NOTES = "notes"
    LISTS = "lists"
    INTERACTIONS = "interactions"
    FIELDS = "fields"


ENTITY = Literal["companies", "persons", "opportunities"]


def get_entity_data_class(entity: ENTITY | LISTS_LITERAL):
    match entity:
        case "companies":
            return Company
        case "persons":
            return Person
        case "opportunities":
            return Opportunity
        case "lists":
            return ListModel


def get_entity_data_class_paged(entity: ENTITY):
    match entity:
        case "companies":
            return CompanyPaged
        case "persons":
            return PersonPaged
        case "opportunities":
            return OpportunityPaged


def use_id(entity: Company | Person | Opportunity | ListModel):
    return entity.model_dump() | {"_dlt_id": entity.id}


def __create_id_resource(
    entity: ENTITY | LISTS_LITERAL, is_id_generator: bool = True, dev_mode=False
) -> DltResource:
    name = f"{entity}_ids" if is_id_generator else entity
    datacls = get_entity_data_class(entity)

    @dlt.resource(
        # This is only a helper resource to improve performance
        # by avoiding paging with a cursor, e.g. this resource
        # pages over entities, yielding chunks of entity IDs, but not
        # pulling field data (which takes longer).
        # A downstream resource then picks up the chunks of IDs and can request
        # field data in parallel, as we don't need to follow a pagination
        # cursor
        selected=not is_id_generator,
        write_disposition="replace",
        primary_key="id",
        columns=datacls,
        name=name,
        parallelized=not dev_mode,
    )
    def __ids() -> Iterable[TDataItem]:
        rest_client = get_v2_rest_client()
        list_adapter = TypeAdapter(list[datacls])

        yield from (
            list_adapter.validate_python(entities)
            for entities in rest_client.paginate(
                entity, params={"limit": MAX_PAGE_LIMIT_V2}, hooks=hooks
            )
        )

    if dev_mode:
        __ids.add_limit(1)
    if not is_id_generator:
        # We have a unique ID, le't tell DLT about it
        __ids.add_map(use_id)
    __ids.__name__ = name
    __ids.__qualname__ = name
    return __ids


ChatMessage.__annotations__["manualCreator"] = int
ChatMessage.model_fields["manualCreator"] = FieldInfo.from_annotation(int)

Attendee.__annotations__["person"] = Optional[int]
Attendee.model_fields["person"] = FieldInfo.from_annotation(Optional[int])

FlattenedInteraction = flatten_root_model(Interaction)
dlt_config: DltConfig = {"skip_nested_types": True}
setattr(FlattenedInteraction, "dlt_config", dlt_config)

DltNote = deepcopy(Note)
interaction_type = Optional[Literal[tuple(InteractionTypeToLiteral.values())]]
DltNote.__annotations__["interaction_type"] = interaction_type
DltNote.model_fields["interaction_type"] = FieldInfo.from_annotation(interaction_type)
# TODO: use something better than str here
DltNote.__annotations__["type"] = str
DltNote.model_fields["type"] = FieldInfo.from_annotation(str)


@dlt.resource(
    primary_key="id",
    columns=DltNote,
    max_table_nesting=1,
    write_disposition="replace",
    parallelized=True,
    references=[
        {
            "columns": ["creator_id"],
            "referenced_columns": ["id"],
            "referenced_table": Table.PERSONS.value,
        },
        {
            "columns": ["interaction_id", "interaction_type"],
            "referenced_columns": ["id", "type"],
            "referenced_table": Table.INTERACTIONS.value,
        },
        {
            "columns": ["parent_id"],
            "referenced_columns": ["id"],
            "referenced_table": Table.NOTES.value,
        },
    ],
)
def notes():
    rest_client = get_v1_rest_client()

    yield from (
        note_adapter.validate_python(notes)
        for notes in rest_client.paginate(
            Table.NOTES.value,
            params={
                "page_size": MAX_PAGE_LIMIT_V1,
            },
        )
    )


def get_dropdown_options_table(field: FieldModel) -> str:
    return f"dropdown_options_{field.id}"


def mark_dropdown_item(
    dropdown_item: Dropdown | RankedDropdown, field: FieldModel
) -> DataItemWithMeta:
    return dlt.mark.with_hints(
        item=dropdown_item.model_dump() | {"_dlt_id": dropdown_item.dropdownOptionId},
        hints=dlt.mark.make_hints(
            table_name=get_dropdown_options_table(field),
            write_disposition="merge",
            primary_key="dropdownOptionId",
            merge_key="dropdownOptionId",
            columns=type(dropdown_item),
        ),
        # needs to be a variant due to https://github.com/dlt-hub/dlt/pull/2109
        create_table_variant=True,
    )


def process_and_yield_fields(
    entity: Company | Person | OpportunityWithFields,
    origin_table: ENTITY | str,
) -> Generator[DataItemWithMeta, None, None]:
    ret: Dict[str, Any] = {}
    references: TTableReferenceParam = []
    if not entity.fields:
        return (ret, references)
    for field in entity.fields:
        yield dlt.mark.with_hints(
            item=field.model_dump(exclude={"value"})
            | {"value_type": field.value.root.type, "_dlt_id": field.id},
            hints=dlt.mark.make_hints(
                table_name=Table.FIELDS.value,
                write_disposition="merge",
                primary_key="id",
                merge_key="id",
                references=[
                    {
                        "columns": ["id"],
                        "referenced_columns": ["id"],
                        "referenced_table": origin_table,
                    }
                ],
            ),
            # needs to be a variant due to https://github.com/dlt-hub/dlt/pull/2109
            create_table_variant=True,
        )
        new_column = (
            f"{field.id}_{field.name}" if field.id.startswith("field-") else field.id
        )
        value = field.value.root
        match value:
            case DateValue():
                ret[new_column] = value.data
            case DropdownValue() | RankedDropdownValue():
                ret[f"{new_column}_dropdown_option_id"] = (
                    value.data.dropdownOptionId if value.data is not None else None
                )
                if value.data is not None:
                    yield mark_dropdown_item(value.data, field)
            case DropdownsValue():
                if value.data is None or len(value.data) == 0:
                    ret[new_column] = []
                    continue
                ret[new_column] = value.data
                for d in value.data:
                    yield mark_dropdown_item(d, field)
            case FormulaValue():
                ret[new_column] = value.data.calculatedValue
                raise ValueError(f"Value type {value} not implemented")
            case InteractionValue():
                if value.data is None:
                    ret[new_column] = None
                    continue
                interaction = value.data.root
                ret[new_column] = interaction.model_dump(include={"id", "type"})
                yield dlt.mark.with_hints(
                    item=interaction.model_dump(),
                    hints=dlt.mark.make_hints(
                        columns=FlattenedInteraction,
                        table_name=Table.INTERACTIONS.value,
                        write_disposition="merge",
                        primary_key=["id", "type"],
                        merge_key=["id", "type"],
                    ),
                    # needs to be a variant due to https://github.com/dlt-hub/dlt/pull/2109
                    create_table_variant=True,
                )
            case PersonValue() | CompanyValue():
                ret[new_column] = value.data
            case PersonsValue() | CompaniesValue():
                ret[new_column] = value.data if value.data else []
            case (
                TextValue()
                | FloatValue()
                | TextValue()
                | TextsValue()
                | FloatsValue()
                | LocationValue()
                | LocationsValue()
            ):
                ret[new_column] = value.data
            case _:
                raise ValueError(f"Value type {value} not implemented")

    return (ret, references)


# TODO: Workaround for the fact that when `add_limit` is used, the yielded entities
# become dicts instead of first-class entities
def __get_id(obj):
    if isinstance(obj, dict):
        return obj.get("id")
    return getattr(obj, "id", None)


def __create_entity_resource(entity_name: ENTITY, dev_mode=False) -> DltResource:
    datacls = get_entity_data_class_paged(entity_name)
    name = entity_name

    @dlt.transformer(
        # we fetch IDs for all entities first,
        # without any data, so we can parallelize the more expensive data fetching
        # whilst not hitting the API limits so fast and we can parallelize
        # because we don't need to page with cursors
        data_from=__create_id_resource(entity_name, dev_mode=dev_mode),
        write_disposition="replace",
        parallelized=True,
        primary_key="id",
        merge_key="id",
        max_table_nesting=3,
        name=name,
    )
    def __entities(
        entity_arr: List[Company | Person | Opportunity],
    ) -> Iterable[TDataItem]:
        rest_client = get_v2_rest_client()

        ids = [__get_id(x) for x in entity_arr]
        response = rest_client.get(
            entity_name,
            params={
                "limit": len(ids),
                "ids": ids,
                "fieldTypes": [
                    Type2.ENRICHED.value,
                    Type2.GLOBAL_.value,
                    Type2.RELATIONSHIP_INTELLIGENCE.value,
                ],
            },
            hooks=hooks,
        )
        response.raise_for_status()
        entities = datacls.model_validate_json(json_data=response.text)

        for e in entities.data:
            (ret, references) = yield from process_and_yield_fields(e, name)
            yield dlt.mark.with_hints(
                item=e.model_dump(exclude={"fields"}) | ret | {"_dlt_id": e.id},
                hints=dlt.mark.make_hints(
                    table_name=name,
                    references=references,
                ),
            )

    __entities.__name__ = name
    __entities.__qualname__ = name
    return __entities


# Via https://stackoverflow.com/questions/34073370
class ReturningGenerator:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.value = yield from self.gen
        return self.value


def __create_list_entries_resource(list_ref: ListReference, dev_mode=False):
    name = f"lists-{list_ref}-entries"
    endpoint = generate_list_entries_path(list_ref)

    @dlt.resource(
        write_disposition="replace",
        parallelized=True,
        primary_key="id",
        merge_key="id",
        max_table_nesting=3,
        name=name,
        table_name=name,
    )
    def __list_entries() -> Iterable[TDataItem]:
        rest_client = get_v2_rest_client()
        for list_entries in (
            list_adapter.validate_python(entities)
            for entities in rest_client.paginate(
                endpoint,
                params={
                    "limit": MAX_PAGE_LIMIT_V2,
                    "fieldTypes": [
                        Type2.ENRICHED.value,
                        Type2.GLOBAL_.value,
                        Type2.RELATIONSHIP_INTELLIGENCE.value,
                        Type2.LIST.value,
                    ],
                },
                hooks=hooks,
            )
        ):
            field_results = []
            list_entry_results = []
            for list_entry in list_entries:
                e = list_entry.root
                gen_fields = process_and_yield_fields(e.entity, name)
                gen = ReturningGenerator(gen_fields)
                field_results.extend(gen)
                (ret, references) = gen.value

                combined_list_entry = (
                    e.model_dump(exclude={"entity"})
                    | ret
                    | {"_dlt_id": e.id, "entity_id": e.entity.id}
                )
                list_entry_results.append(combined_list_entry)

            yield dlt.mark.with_hints(
                item=list_entry_results,
                hints=dlt.mark.make_hints(
                    table_name=name,
                    references=references,
                ),
                # needs to be a variant due to https://github.com/dlt-hub/dlt/pull/2109
                create_table_variant=True,
            )
            yield from field_results

    __list_entries.__name__ = name
    __list_entries.__qualname__ = name
    return __list_entries


@dlt.source(name="affinity")
def source(
    list_refs: List[ListReference] = field(default_factory=list), dev_mode=False
) -> Sequence[DltResource]:
    """
    list_refs - one or more references to lists and/or saved list views
    """
    list_resources = [
        __create_list_entries_resource(ref, dev_mode=dev_mode) for ref in list_refs
    ]

    companies = __create_entity_resource("companies", dev_mode=dev_mode)
    """ The companies resource. Contains all company entities. """

    persons = __create_entity_resource("persons", dev_mode=dev_mode)
    """ The persons resource. Contains all person entities. """

    opportunities = __create_id_resource(
        "opportunities", dev_mode=dev_mode, is_id_generator=False
    )
    """ The opportunities resource. Contains all opportunity entities. """

    lists = __create_id_resource("lists", dev_mode=dev_mode, is_id_generator=False)
    """ The lists resource. This contains information about lists themselves, not about their entries """

    return (
        companies,
        notes,
        persons,
        opportunities,
        lists,
        *list_resources,
    )


__all__ = ["source", "ListReference"]
