from .model import Errors, ListEntryWithEntity
from .model.notes import Note

from pydantic import TypeAdapter


error_adapter = TypeAdapter(Errors)
list_adapter = TypeAdapter(list[ListEntryWithEntity])
note_adapter = TypeAdapter(list[Note])
