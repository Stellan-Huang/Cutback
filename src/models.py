from typing import Literal

from pydantic import BaseModel, model_validator


class EditAction(BaseModel):
    action: Literal["DELETE_RANGE"]
    start_time: float
    end_time: float

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_time < 0:
            raise ValueError("start_time 不能小于 0")

        if self.end_time <= self.start_time:
            raise ValueError("end_time 必须大于 start_time")

        return self


class ReviewResult(BaseModel):
    status: Literal["ACTION", "CLARIFY", "NO_ACTION"]
    action: EditAction | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_result(self):
        if self.status == "ACTION" and self.action is None:
            raise ValueError("ACTION 必须包含 EditAction")

        if self.status != "ACTION" and self.action is not None:
            raise ValueError("非 ACTION 状态不能包含 EditAction")

        return self
