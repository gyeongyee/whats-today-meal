from __future__ import annotations

import hashlib

from ai_service import AISemanticService
from menu_data import MENU_CATALOG, Menu
from models import RecommendRequest, RecommendResponse, RecommendationItem
from similarity_service import (
    MenuProfile,
    clean_text,
    local_similarity,
    profile_of,
    profiles_of,
)


class RecommendationEngine:
    def __init__(self, ai_service: AISemanticService):
        self.ai_service = ai_service

    @staticmethod
    def _preference_score(menu: Menu, request: RecommendRequest) -> float:
        tags = set(menu["tags"])
        score = 0.0
        if request.avoid_spicy:
            score += -100 if "매운맛" in tags else 8
        if request.prefer_soup:
            score += 24 if "국물" in tags else -4
        if request.prefer_light:
            score += 26 if "가벼움" in tags else -4
        return score

    @staticmethod
    def _stable_variety(menu: Menu, request: RecommendRequest) -> float:
        seed = f"{menu['name']}:{request.retry_count}:{request.mode}".encode()
        return int(hashlib.sha256(seed).hexdigest()[:4], 16) / 65535 * 8

    @staticmethod
    def _day_similarity(candidate: MenuProfile, meals: list[MenuProfile]) -> float:
        """하루에 여러 메뉴가 있으면 그중 가장 유사한 메뉴를 해당 날짜 유사도로 사용한다."""
        return max((local_similarity(candidate, meal) for meal in meals), default=0.0)

    @staticmethod
    def _is_exact_meal(candidate: MenuProfile, meals: list[MenuProfile]) -> bool:
        candidate_name = clean_text(candidate.name)
        return any(candidate_name == clean_text(meal.name) for meal in meals if meal.name)

    @staticmethod
    def _local_reason(
        menu: Menu,
        histories_by_day: list[list[MenuProfile]],
        request: RecommendRequest,
    ) -> str:
        tags = set(menu["tags"])
        if request.prefer_soup and "국물" in tags:
            return "최근 여러 끼니와의 겹침을 줄이면서 오늘의 국물 선호를 반영한 따뜻한 선택이에요."
        if request.prefer_light and "가벼움" in tags:
            return "최근 식사들과 다른 결을 유지하면서 가볍게 즐기기 좋은 메뉴예요."
        if request.avoid_spicy and "매운맛" not in tags:
            return "매운맛은 피하고 최근 여러 끼니와의 유사도는 낮춘 선택이에요."
        if request.mode == "relaxed":
            return "어제 먹은 메뉴들은 피하되 2~3일 전 조건을 풀어 선택의 폭을 넓혔어요."
        yesterday_names = [meal.name for meal in histories_by_day[0] if meal.name]
        if yesterday_names:
            summary = ", ".join(yesterday_names[:2])
            return f"어제 먹은 {summary}와 조리법과 맛의 겹침이 적은 메뉴예요."
        return f"{menu['cuisine']} 계열에서 부담 없이 시작하기 좋은 새로운 후보예요."

    async def recommend(self, request: RecommendRequest) -> RecommendResponse:
        history_text = [request.yesterday, request.two_days_ago, request.three_days_ago]
        histories_by_day = [profiles_of(day) for day in history_text]

        local_ranked: list[tuple[float, Menu, list[float]]] = []
        for menu in MENU_CATALOG:
            candidate = profile_of(menu)
            similarities = [
                self._day_similarity(candidate, daily_meals)
                for daily_meals in histories_by_day
            ]

            # 어제 먹은 메뉴가 여러 개여도 모든 동일 메뉴를 두 모드에서 항상 제외한다.
            if self._is_exact_meal(candidate, histories_by_day[0]):
                continue
            if request.mode == "strict" and similarities[0] >= 0.72:
                continue

            weights = (66, 38, 22) if request.mode == "strict" else (38, 7, 3)
            score = 100 - sum(
                similarity * weight
                for similarity, weight in zip(similarities, weights, strict=True)
            )
            score += self._preference_score(menu, request)
            score += self._stable_variety(menu, request)
            local_ranked.append((score, menu, similarities))

        local_ranked.sort(key=lambda item: item[0], reverse=True)
        shortlist = local_ranked[:16]
        ai_results = await self.ai_service.assess(
            [menu for _, menu, _ in shortlist], history_text, request
        )

        reranked: list[tuple[float, Menu, list[float], str]] = []
        for local_score, menu, local_similarities in shortlist:
            assessment = ai_results.get(menu["name"]) if ai_results else None
            similarities = assessment.similarities if assessment else local_similarities
            if request.mode == "strict" and similarities[0] >= 0.72:
                continue
            weights = (66, 38, 22) if request.mode == "strict" else (38, 7, 3)
            semantic_score = 100 - sum(
                similarity * weight
                for similarity, weight in zip(similarities, weights, strict=True)
            )
            score = semantic_score + self._preference_score(menu, request)
            score += local_score * 0.08 + self._stable_variety(menu, request)
            reason = (
                assessment.reason
                if assessment
                else self._local_reason(menu, histories_by_day, request)
            )
            reranked.append((score, menu, similarities, reason))
        reranked.sort(key=lambda item: item[0], reverse=True)

        selected: list[tuple[float, Menu, list[float], str]] = []
        used_kinds: set[str] = set()
        for item in reranked:
            menu = item[1]
            if menu["kind"] in used_kinds and len(selected) < 2:
                continue
            selected.append(item)
            used_kinds.add(menu["kind"])
            if len(selected) == 3:
                break
        if len(selected) < 3:
            selected = reranked[:3]

        engine = "ai" if ai_results else "local"
        return RecommendResponse(
            mode=request.mode,
            engine=engine,
            engine_label="AI 의미 분석 적용" if engine == "ai" else "로컬 의미 분석 적용",
            relax_level=request.retry_count,
            recommendations=[
                RecommendationItem(
                    menu=menu["name"],
                    cuisine=menu["cuisine"],
                    kind=menu["kind"],
                    reason=reason,
                    search_query=menu["name"],
                    similarity=round(max(similarities), 2),
                )
                for _, menu, similarities, reason in selected
            ],
        )
