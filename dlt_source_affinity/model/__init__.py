from pydantic import BaseModel, model_serializer


class MyBaseModel(BaseModel):
    @model_serializer(mode="wrap")
    def ser_model(self, nxt):
        if self.__class__.__qualname__ == "PersonData":
            return self.id
        else:
            return nxt(self)
