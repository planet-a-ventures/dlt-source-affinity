from enum import IntEnum
from inspect import get_annotations
from pydantic import BaseModel, Field, model_serializer
from typing import ClassVar, List, Annotated, get_args
from datetime import datetime

from dlt.common.libs.pydantic import DltConfig

from .v2 import ChatMessage, PhoneCall, Email, Meeting


class NoteType(IntEnum):
    PLAIN_TEXT = 0
    HTML = 2
    AI_SUMMARY = 3
    """Can only be created by the Notetaker AI tool from Affinity."""
    EMAIL = 1
    """Deprecated"""


class InteractionType(IntEnum):
    MEETING = 0
    """Type specifying a meeting interaction."""
    CALL = 1
    """Type specifying a call interaction."""
    CHAT_MESSAGE = 2
    """Type specifying a chat message interaction."""
    EMAIL = 3
    """Type specifying an email interaction."""


def get_type_annotation(m: BaseModel):
    annotations = get_annotations(m, eval_str=True)
    return get_args(get_args(annotations["type"])[0])[0]


InteractionTypeToLiteral: dict[InteractionType, str] = {
    InteractionType.MEETING: get_type_annotation(Meeting),
    InteractionType.CALL: get_type_annotation(PhoneCall),
    InteractionType.CHAT_MESSAGE: get_type_annotation(ChatMessage),
    InteractionType.EMAIL: get_type_annotation(Email),
}


def interaction_type_to_literal(i_type: InteractionType) -> str:
    ret = InteractionTypeToLiteral[i_type]
    if ret is None:
        raise ValueError(f"Missing string type for {i_type}")
    return ret


class Note(
    BaseModel,
):
    dlt_config: ClassVar[DltConfig] = {"skip_nested_types": True}

    @model_serializer(mode="wrap")
    def ser_model(self, nxt):
        ret = nxt(self)
        if self.interaction_type is not None:
            ret["interaction_type"] = interaction_type_to_literal(
                InteractionType(self.interaction_type)
            )
        # TODO: Note types are not available in the V2 OpenAPI spec, yet
        # so we have to guess their enum representation; Fix this, once possible
        ret["type"] = self.type.name.lower().replace("_", "-")
        return ret

    """Represents a note object with metadata and associations."""

    id: Annotated[int, Field(examples=[1], ge=1, le=9007199254740991)]
    """The unique identifier of the note object."""

    creator_id: Annotated[int, Field(examples=[1], ge=1, le=9007199254740991)]
    """The unique identifier of the person object who created the note."""

    person_ids: List[int]
    """An array containing the unique identifiers for all the persons relevant to the note.
    This is the union of associated_person_ids and interaction_person_ids."""

    associated_person_ids: List[int]
    """An array containing the unique identifiers for the persons directly associated with the note."""

    interaction_person_ids: List[int]
    """An array containing the unique identifiers for the persons on the interaction the note is attached to, if any."""

    interaction_id: Annotated[
        int | None, Field(examples=[1], ge=1, le=9007199254740991)
    ]
    """The unique identifier of the interaction the note is attached to, if any."""

    interaction_type: InteractionType | None
    """The type of the interaction the note is attached to, if any."""

    is_meeting: bool
    """True if the note is attached to a meeting or a call."""

    mentioned_person_ids: List[
        Annotated[int | None, Field(examples=[1], ge=1, le=9007199254740991)]
    ]
    """An array containing the unique identifiers for the persons who are @ mentioned in the note."""

    organization_ids: List[
        Annotated[int | None, Field(examples=[1], ge=1, le=9007199254740991)]
    ]
    """An array of unique identifiers of organization objects that are associated with the note."""

    opportunity_ids: List[
        Annotated[int | None, Field(examples=[1], ge=1, le=9007199254740991)]
    ]
    """An array of unique identifiers of opportunity objects that are associated with the note."""

    parent_id: Annotated[int | None, Field(examples=[1], ge=1, le=9007199254740991)]
    """The unique identifier of the note that this note is a reply to.
    If this field is null, the note is not a reply."""

    content: str
    """The string containing the content of the note."""

    type: NoteType
    """The type of the note. Supported types for new note creation via API are 0 and 2, representing plain text and HTML notes, respectively."""

    created_at: datetime
    """The string representing the time when the note was created."""

    updated_at: datetime | None
    """The string representing the last time the note was updated."""
