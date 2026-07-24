from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from menu_data import Menu
from models import AIAssessment, AIAssessmentResponse, RecommendRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AISettings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 12.0


class AISemanticService:
    """OpenAI-compatible semantic assessment with strict, fail-closed parsing."""

    def __init__(self, settings: AISettings):
        self.settings = settings

    @classmethod
    def from_env(cls) -> "AISemanticService":
        return cls(
            AISettings(
                api_key=os.getenv("AI_API_KEY", "").strip(),
                base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
                model=os.getenv("AI_MODEL", "gpt-4.1-mini").strip(),
            )
        )

    @property
    def configured(self) -> bool:
        return bool(self.settings.api_key and self.settings.base_url and self.settings.model)

    async def assess(
        self,
        candidates: list[Menu],
        histories: list[str],
        request: RecommendRequest,
    ) -> dict[str, AIAssessment] | None:
        if not self.configured or not any(histories):
            return None

        preference = {
            "avoid_spicy": request.avoid_spicy,
            "prefer_soup": request.prefer_soup,
            "prefer_light": request.prefer_light,
            "prefer_hearty": request.prefer_hearty,
            "prefer_quick": request.prefer_quick,
            "prefer_share": request.prefer_share,
            "preferred_cuisines": request.preferred_cuisines,
            "preferred_tags": request.preferred_tags,
            "mode": request.mode,
            "retry_count": request.retry_count,
            "participant_count": 1 + len(request.team_members),
        }
        prompt = (
            "당신은 한국 직장인 팀의 점심 메뉴 의미 유사도 분석기입니다. 최근 식사는 어제, 2일 전, 3일 전 순서이며, "
            "각 날짜 문자열에는 참여자들이 먹은 점심·저녁 등 여러 메뉴가 쉼표로 구분되어 들어갈 수 있습니다. "
            "각 날짜에 여러 메뉴가 있으면 후보와 가장 유사한 메뉴를 기준으로 그 날짜 유사도를 계산하세요. "
            "철자 일치뿐 아니라 재료·조리법·음식 경험이 비슷한지도 판단하세요. "
            "각 후보마다 similarities에 최근 식사 3개와의 유사도를 0~1로 정확히 3개 반환하고, "
            "참여 인원, 선호와 재추천 횟수를 반영한 자연스러운 한국어 추천 이유를 1문장으로 작성하세요. "
            "JSON 외 텍스트는 쓰지 마세요.\n"
            + json.dumps(
                {
                    "history": histories,
                    "preferences": preference,
                    "candidates": candidates,
                    "required_schema": {
                        "assessments": [
                            {"menu": "후보명", "similarities": [0.0, 0.0, 0.0], "reason": "추천 이유"}
                        ]
                    },
                },
                ensure_ascii=False,
            )
        )
        payload = {
            "model": self.settings.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "주어진 스키마만 따르는 음식 의미 분석 API입니다."},
                {"role": "user", "content": prompt},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            envelope = response.json()
            content = envelope["choices"][0]["message"]["content"]
            parsed = AIAssessmentResponse.model_validate_json(content)
            expected_names = {menu["name"] for menu in candidates}
            by_name = {item.menu: item for item in parsed.assessments}
            if set(by_name) != expected_names:
                raise ValueError("AI candidate set mismatch")
            return by_name
        except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError):
            logger.warning("AI assessment failed; using local fallback", exc_info=True)
            return None
