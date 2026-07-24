from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TeamMemberMeals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=20)
    yesterday: str = Field(default="", max_length=120)
    two_days_ago: str = Field(default="", max_length=120)
    three_days_ago: str = Field(default="", max_length=120)

    @field_validator("name", "yesterday", "two_days_ago", "three_days_ago")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    yesterday: str = Field(default="", max_length=120)
    two_days_ago: str = Field(default="", max_length=120)
    three_days_ago: str = Field(default="", max_length=120)
    mode: Literal["strict", "relaxed"] = "strict"
    avoid_spicy: bool = False
    prefer_soup: bool = False
    prefer_light: bool = False
    retry_count: int = Field(default=0, ge=0, le=20)
    team_members: list[TeamMemberMeals] = Field(default_factory=list, max_length=9)

    @field_validator("yesterday", "two_days_ago", "three_days_ago")
    @classmethod
    def normalize_meal(cls, value: str) -> str:
        return " ".join(value.strip().split())


class RecommendationItem(BaseModel):
    menu: str
    cuisine: str
    kind: str
    reason: str
    similarity: float = Field(ge=0, le=1)


class RecommendResponse(BaseModel):
    mode: Literal["strict", "relaxed"]
    engine: Literal["ai", "local"]
    engine_label: str
    relax_level: int
    participant_count: int = Field(ge=1, le=10)
    recommendations: list[RecommendationItem] = Field(min_length=3, max_length=3)


class AIAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    menu: str = Field(min_length=1, max_length=50)
    similarities: list[float] = Field(min_length=3, max_length=3)
    reason: str = Field(min_length=5, max_length=160)

    @field_validator("similarities")
    @classmethod
    def check_similarity_range(cls, values: list[float]) -> list[float]:
        if any(value < 0 or value > 1 for value in values):
            raise ValueError("similarity must be between 0 and 1")
        return values


class AIAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessments: list[AIAssessment] = Field(min_length=1, max_length=20)
