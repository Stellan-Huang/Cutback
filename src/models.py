"""Data models for Cutback."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EditAction(BaseModel):
    action: Literal["DELETE_RANGE"]
    start_time: float = Field(ge=0)
    end_time: float

    @model_validator(mode="after")
    def end_after_start(self) -> "EditAction":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be > start_time")
        return self
