from pydantic import RootModel
from pydantic_flatten_rootmodel import flatten_root_model

from ..model.v2 import Interaction


def test_x():
    FlattenedInteraction = flatten_root_model(Interaction)
    assert not issubclass(FlattenedInteraction, RootModel)
