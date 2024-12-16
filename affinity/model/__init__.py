from pydantic import BaseModel, model_serializer


class MyBaseModel(BaseModel):
    @model_serializer(mode="wrap")
    def ser_model(self, nxt):
        # TODO: improve this to possibly make the serializer swap out any
        # `PersonData` class with tis id, except in the `PersonValue` class
        if self.__class__.__qualname__ == "Attendee":
            return {
                "emailAddress": self.emailAddress,
                "person_id": getattr(self.person, "id", None),
            }
        else:
            return nxt(self)
