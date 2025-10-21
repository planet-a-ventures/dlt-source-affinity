from pydantic import TypeAdapter

from .model.v1 import Note
from .model.v2 import Errors, ListEntryWithEntity

error_adapter = TypeAdapter(Errors)
list_adapter = TypeAdapter(list[ListEntryWithEntity])
note_adapter = TypeAdapter(list[Note])
