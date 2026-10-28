"""Feedback HTTP contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feedback_token: str = Field(min_length=1, max_length=4096)
    rating: Literal["up", "down"] | None


class FeedbackResponse(BaseModel):
    rating: Literal["up", "down"] | None
