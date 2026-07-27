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
        if request.prefer_hearty:
            score += 20 if tags & {"밥", "고기", "소고기", "돼지고기", "닭고기"} else -3
        if request.prefer_quick:
            score += 20 if tags & {"빠름", "간편식", "빵", "또르띠야"} else -3
        if request.prefer_share:
            score += 20 if "공유" in tags else -2
        if request.preferred_tags:
            score += min(36, 13 * len(tags & set(request.preferred_tags)))
        if "다이어트" in request.preferred_tags:
            score += 55 if "다이어트" in tags else -18
        if request.preferred_cuisines:
            cuisine_groups = {
                "한식": {"한식", "분식"},
                "일식": {"일식"},
                "중식": {"중식"},
                "양식": {"양식"},
                "세계": {
                    "동남아", "인도", "멕시칸", "중동", "스페인",
                },
            }
            selected = {
                cuisine
                for group in request.preferred_cuisines
                for cuisine in cuisine_groups.get(group, {group})
            }
            score += 24 if menu["cuisine"] in selected else -3
        return score

    @staticmethod
    def _menu_details(menu: Menu) -> tuple[str, int, int, str, str]:
        tags = set(menu["tags"])
        kind = menu["kind"]
        if "국물" in tags:
            visual_key, emoji = "soup", "🍲"
        elif "면" in tags:
            visual_key, emoji = "noodle", "🍜"
        elif tags & {"빵", "또르띠야"}:
            visual_key, emoji = "wrap", "🌯"
        elif "채소" in tags and "가벼움" in tags:
            visual_key, emoji = "light", "🥗"
        elif tags & {"구이", "튀김"}:
            visual_key, emoji = "grill", "🍗"
        else:
            visual_key, emoji = "rice", "🍚"

        base = 520
        if "가벼움" in tags:
            base -= 150
        if "튀김" in tags or "크림" in tags or "치즈" in tags:
            base += 180
        if tags & {"밥", "면"}:
            base += 80
        if tags & {"고기", "소고기", "돼지고기", "닭고기"}:
            base += 70
        calorie_min = max(180, base - 80)
        calorie_max = base + 100

        feature_sentences = [
            sentence
            for tag, sentence in (
                ("국물", "따뜻한 국물로 속을 편안하게 채우기 좋아요."),
                ("채소", "채소의 산뜻한 식감이 살아 있어요."),
                ("튀김", "바삭한 식감으로 기분 좋은 포만감을 줘요."),
                ("구이", "불향과 구운 풍미가 매력적이에요."),
                ("매운맛", "입맛을 깨우는 매콤함이 포인트예요."),
                ("향신료", "풍성한 향신료 향을 즐기기 좋아요."),
                ("해산물", "해산물의 감칠맛을 담았어요."),
                ("가벼움", "부담이 적어 산뜻하게 즐기기 좋아요."),
            )
            if tag in tags
        ]
        feature = feature_sentences[0] if feature_sentences else f"{kind} 특유의 든든한 맛을 즐기기 좋아요."
        description = f"{menu['cuisine']} 스타일의 {kind} 메뉴예요. {feature}"
        return description, calorie_min, calorie_max, visual_key, emoji

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
        team_count = len(request.team_members)
        if team_count:
            if request.mode == "relaxed":
                return f"{team_count + 1}명의 어제 메뉴는 피하면서 2~3일 전 조건을 풀어 모두의 선택 폭을 넓혔어요."
            return f"{team_count + 1}명이 최근 먹은 메뉴들과 재료·조리법의 겹침이 적은 공동 점심 후보예요."
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
        history_text = [
            ", ".join(
                value
                for value in [
                    getattr(request, field),
                    *(getattr(member, field) for member in request.team_members),
                ]
                if value
            )
            for field in ("yesterday", "two_days_ago", "three_days_ago")
        ]
        histories_by_day = [profiles_of(day) for day in history_text]

        local_ranked: list[tuple[float, Menu, list[float]]] = []
        for menu in MENU_CATALOG:
            tags = set(menu["tags"])
            wants_vegan = "비건" in request.preferred_tags
            wants_diet = "다이어트" in request.preferred_tags
            if wants_vegan and "비건" not in tags:
                continue
            # 다이어트만 고르면 지정된 후보로 좁히고, 비건과 함께 고르면
            # 비건 후보 안에서 다이어트 적합도를 우선한다.
            if wants_diet and not wants_vegan and "다이어트" not in tags:
                continue
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
        preference_active = bool(
            request.preferred_cuisines
            or request.preferred_tags
            or request.prefer_hearty
            or request.prefer_quick
            or request.prefer_share
        )
        return RecommendResponse(
            mode=request.mode,
            engine=engine,
            engine_label="AI 의미 분석 적용" if engine == "ai" else "로컬 의미 분석 적용",
            relax_level=request.retry_count,
            participant_count=1 + len(request.team_members),
            recommendations=[
                RecommendationItem(
                    menu=menu["name"],
                    cuisine=menu["cuisine"],
                    kind=menu["kind"],
                    reason=(
                        f"선택한 음식 취향을 반영했어요. {reason}"
                        if preference_active and not reason.startswith("선택한")
                        else reason
                    ),
                    description=self._menu_details(menu)[0],
                    calorie_min=self._menu_details(menu)[1],
                    calorie_max=self._menu_details(menu)[2],
                    visual_key=self._menu_details(menu)[3],
                    emoji=self._menu_details(menu)[4],
                    similarity=round(max(similarities), 2),
                )
                for _, menu, similarities, reason in selected
            ],
        )
