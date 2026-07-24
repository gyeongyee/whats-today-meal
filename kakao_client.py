from __future__ import annotations

import os
from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from models import RestaurantItem, RestaurantSearchResponse


@dataclass(frozen=True)
class KakaoSettings:
    api_key: str
    timeout_seconds: float = 10.0


class KakaoLocalClient:
    BASE_URL = "https://dapi.kakao.com/v2/local"

    def __init__(self, settings: KakaoSettings):
        self.settings = settings

    @classmethod
    def from_env(cls) -> "KakaoLocalClient":
        return cls(KakaoSettings(api_key=os.getenv("KAKAO_REST_API_KEY", "").strip()))

    @property
    def configured(self) -> bool:
        return bool(self.settings.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.configured:
            raise HTTPException(
                status_code=503,
                detail="주변 식당 검색이 아직 준비되지 않았어요. 운영자에게 카카오 API 설정을 요청해 주세요.",
            )
        return {"Authorization": f"KakaoAK {self.settings.api_key}"}

    async def _get(self, path: str, params: dict[str, object]) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
                response = await client.get(
                    f"{self.BASE_URL}/{path}", headers=self._headers(), params=params
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("invalid payload")
                return data
        except HTTPException:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise HTTPException(
                status_code=504, detail="식당 검색 응답이 늦어지고 있어요. 잠시 후 다시 시도해 주세요."
            ) from exc
        except (httpx.HTTPStatusError, ValueError) as exc:
            raise HTTPException(
                status_code=502, detail="식당 검색 서비스에 일시적인 문제가 있어요. 잠시 후 다시 시도해 주세요."
            ) from exc

    async def geocode(self, address: str) -> dict[str, str]:
        data = await self._get("search/address.json", {"query": address})
        documents = data.get("documents")
        if not isinstance(documents, list) or not documents:
            raise HTTPException(
                status_code=404, detail="주소를 찾지 못했어요. 도로명과 건물 번호를 함께 입력해 주세요."
            )
        first = documents[0]
        return {
            "address_name": str(first.get("address_name") or address),
            "x": str(first.get("x") or ""),
            "y": str(first.get("y") or ""),
        }

    async def search_restaurants(
        self, query: str, x: float, y: float, radius: int
    ) -> RestaurantSearchResponse:
        data = await self._get(
            "search/keyword.json",
            {
                "query": query,
                "category_group_code": "FD6",
                "x": x,
                "y": y,
                "radius": radius,
                "sort": "distance",
                "size": 15,
            },
        )
        documents = data.get("documents")
        if not isinstance(documents, list):
            documents = []
        restaurants = [
            RestaurantItem(
                name=str(item.get("place_name") or "이름 없는 식당"),
                category=str(item.get("category_name") or "음식점"),
                address=str(item.get("road_address_name") or item.get("address_name") or "주소 정보 없음"),
                phone=str(item.get("phone") or ""),
                distance_m=int(item.get("distance") or 0),
                place_url=str(item.get("place_url") or ""),
            )
            for item in documents
            if isinstance(item, dict)
        ]
        suggestion = None
        if not restaurants:
            suggestion = (
                "검색 결과가 없어요. 반경을 넓히거나 메뉴의 상위 종류(예: 찌개→한식)로 검색해 보세요."
            )
        return RestaurantSearchResponse(
            query=query,
            count=len(restaurants),
            radius=radius,
            restaurants=restaurants,
            suggestion=suggestion,
        )
