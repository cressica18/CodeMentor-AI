"""
Pydantic models that map directly to Codeforces API response shapes.

These are *ingestion* models — they reflect the CF wire format and are
intentionally separate from the application's own schema layer so that
upstream changes in the CF API can be absorbed here without touching
business logic.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class CFProblem(BaseModel):
    """Represents a single CF problem (embedded inside a submission)."""

    contest_id: Optional[int] = Field(None, alias="contestId")
    problemset_name: Optional[str] = Field(None, alias="problemsetName")
    index: str
    name: str
    type: Optional[str] = None
    points: Optional[float] = None
    rating: Optional[int] = None
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class CFUser(BaseModel):
    """Profile snapshot returned by user.info."""

    handle: str
    email: Optional[str] = None
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    country: Optional[str] = None
    city: Optional[str] = None
    organization: Optional[str] = None
    contribution: int = 0
    rank: Optional[str] = None
    rating: Optional[int] = None
    max_rank: Optional[str] = Field(None, alias="maxRank")
    max_rating: Optional[int] = Field(None, alias="maxRating")
    last_online_time_seconds: Optional[int] = Field(
        None, alias="lastOnlineTimeSeconds"
    )
    registration_time_seconds: Optional[int] = Field(
        None, alias="registrationTimeSeconds"
    )
    friend_of_count: int = Field(0, alias="friendOfCount")
    avatar: Optional[str] = None
    title_photo: Optional[str] = Field(None, alias="titlePhoto")

    model_config = {"populate_by_name": True}

    @property
    def display_name(self) -> str:
        parts = [self.first_name, self.last_name]
        full = " ".join(p for p in parts if p)
        return full or self.handle


class CFRatingChange(BaseModel):
    """One entry in a user's contest rating history."""

    contest_id: int = Field(..., alias="contestId")
    contest_name: str = Field(..., alias="contestName")
    handle: str
    rank: int
    rating_update_time_seconds: int = Field(
        ..., alias="ratingUpdateTimeSeconds"
    )
    old_rating: int = Field(..., alias="oldRating")
    new_rating: int = Field(..., alias="newRating")

    model_config = {"populate_by_name": True}

    @property
    def delta(self) -> int:
        return self.new_rating - self.old_rating


class CFSubmission(BaseModel):
    """One submission record from user.status."""

    id: int
    contest_id: Optional[int] = Field(None, alias="contestId")
    creation_time_seconds: int = Field(..., alias="creationTimeSeconds")
    relative_time_seconds: Optional[int] = Field(
        None, alias="relativeTimeSeconds"
    )
    problem: CFProblem
    author: dict  # participant info — not parsed deeply
    programming_language: Optional[str] = Field(
        None, alias="programmingLanguage"
    )
    verdict: Optional[str] = None
    testset: Optional[str] = None
    passed_test_count: int = Field(0, alias="passedTestCount")
    time_consumed_millis: int = Field(0, alias="timeConsumedMillis")
    memory_consumed_bytes: int = Field(0, alias="memoryConsumedBytes")

    model_config = {"populate_by_name": True}

    @field_validator("verdict", mode="before")
    @classmethod
    def normalise_verdict(cls, v: object) -> Optional[str]:
        return str(v) if v is not None else None
