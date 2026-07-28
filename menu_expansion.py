from __future__ import annotations

from collections.abc import Iterable


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.strip().splitlines() if line.strip()]


EXPANDED_MENU_GROUPS = {
    "국밥·탕·해장국": _lines(
        """
순대국밥
돼지국밥
소머리국밥
콩나물국밥
굴국밥
선지국밥
내장국밥
뼈해장국
우거지해장국
황태해장국
양평해장국
올갱이국
재첩국
미역국 정식
소고기무국
육개장
닭개장
설렁탕
곰탕
나주곰탕
도가니탕
갈비탕
꼬리곰탕
삼계탕
반계탕
백숙
추어탕
감자탕
뼈다귀탕
매운갈비탕
사골우거지탕
버섯들깨탕
들깨수제비탕
순두부국밥
김치국밥
장터국밥
따로국밥
얼큰소고기국밥
부산돼지국밥
밀양돼지국밥
수육국밥
"""
    ),
    "찌개·전골": _lines(
        """
김치찌개
참치김치찌개
꽁치김치찌개
돼지고기김치찌개
된장찌개
차돌된장찌개
해물된장찌개
순두부찌개
해물순두부찌개
차돌순두부찌개
청국장찌개
부대찌개
햄부대찌개
스팸부대찌개
동태찌개
알탕
대구탕
꽃게탕
매운탕
오징어찌개
짜글이찌개
돼지짜글이
두부짜글이
고추장찌개
비지찌개
버섯전골
불고기전골
곱창전골
만두전골
두부전골
"""
    ),
    "국수·면류": _lines(
        """
잔치국수
비빔국수
열무국수
김치말이국수
멸치국수
칼국수
바지락칼국수
닭칼국수
들깨칼국수
장칼국수
수제비
들깨수제비
감자수제비
쫄면
막국수
물막국수
비빔막국수
냉면
물냉면
비빔냉면
밀면
물밀면
비빔밀면
콩국수
메밀국수
판모밀
우동
김치우동
튀김우동
라면
"""
    ),
    "밥·볶음밥·덮밥": _lines(
        """
비빔밥
돌솥비빔밥
전주비빔밥
산채비빔밥
육회비빔밥
회덮밥
알밥
김치볶음밥
새우볶음밥
야채볶음밥
오므라이스
카레라이스
하이라이스
짜장밥
잡채밥
제육덮밥
불고기덮밥
오징어덮밥
낙지덮밥
쭈꾸미덮밥
닭갈비덮밥
치킨마요덮밥
참치마요덮밥
스팸마요덮밥
돈가스덮밥
가츠동
규동
장어덮밥
연어덮밥
소고기덮밥
"""
    ),
    "볶음·구이·정식·백반": _lines(
        """
제육볶음
고추장불고기
간장불고기
돼지불백
소불고기
오징어볶음
낙지볶음
쭈꾸미볶음
닭갈비
철판닭갈비
돼지두루치기
김치두루치기
오삼불고기
고등어구이
삼치구이
갈치구이
임연수구이
조기구이
생선구이정식
보쌈정식
수육정식
돼지갈비정식
떡갈비정식
함박스테이크
돈가스
치즈돈가스
생선가스
치킨가스
백반
"""
    ),
    "분식·간편식": _lines(
        """
김밥
참치김밥
치즈김밥
돈가스김밥
제육김밥
충무김밥
떡볶이
국물떡볶이
라볶이
순대
모둠튀김
만두
군만두
찐만두
김치만두
고기만두
떡만둣국
만둣국
떡국
어묵탕
"""
    ),
    "중식·일식·기타": _lines(
        """
짜장면
간짜장
쟁반짜장
짬뽕
삼선짬뽕
짬뽕밥
볶음짬뽕
탕수육 정식
마파두부밥
중화비빔밥
중국냉면
초밥
모둠초밥
회정식
물회
우동정식
돈부리
쌀국수
팟타이
분짜
햄버거
샌드위치
"""
    ),
}


JAPANESE_KEYWORDS = (
    "우동",
    "모밀",
    "초밥",
    "회정식",
    "돈부리",
    "가츠동",
    "규동",
    "돈가스",
    "치킨가스",
    "생선가스",
    "함박스테이크",
    "오므라이스",
    "카레라이스",
    "하이라이스",
    "장어덮밥",
    "연어덮밥",
)
CHINESE_KEYWORDS = (
    "짜장",
    "짬뽕",
    "탕수육",
    "마파두부",
    "중화",
    "잡채밥",
    "새우볶음밥",
    "야채볶음밥",
)
SOUTHEAST_ASIAN_KEYWORDS = ("쌀국수", "팟타이", "분짜")
WESTERN_KEYWORDS = ("햄버거", "샌드위치")


def _cuisine(name: str) -> str:
    if name == "물회":
        return "일식"
    if name == "중국냉면":
        return "중식"
    if name.endswith("김밥"):
        return "한식"
    if any(keyword in name for keyword in JAPANESE_KEYWORDS):
        return "일식"
    if any(keyword in name for keyword in CHINESE_KEYWORDS):
        return "중식"
    if any(keyword in name for keyword in SOUTHEAST_ASIAN_KEYWORDS):
        return "동남아"
    if any(keyword in name for keyword in WESTERN_KEYWORDS):
        return "양식"
    return "한식"


def _kind(name: str, group: str) -> str:
    if "볶음밥" in name:
        return "볶음밥"
    if "국밥" in name or "해장국" in name:
        return "국밥"
    if (
        "덮밥" in name
        or name.endswith("밥")
        or "비빔밥" in name
        or name in {"카레라이스", "하이라이스", "돈부리"}
    ):
        return "덮밥"
    if "찌개" in name or "짜글이" in name:
        return "찌개"
    if "전골" in name:
        return "전골"
    if any(keyword in name for keyword in ("국수", "냉면", "밀면", "막국수", "쫄면", "칼국수", "수제비", "모밀", "우동", "라면", "짜장면", "짬뽕", "팟타이", "분짜", "쌀국수")):
        return "면"
    if any(keyword in name for keyword in ("김밥", "햄버거", "샌드위치")):
        return "간편식"
    if any(keyword in name for keyword in ("떡볶이", "순대", "만두")):
        return "분식"
    if any(keyword in name for keyword in ("돈가스", "치킨가스", "생선가스", "튀김", "탕수육")):
        return "튀김"
    if any(keyword in name for keyword in ("볶음", "두루치기", "불고기", "닭갈비")):
        return "볶음"
    if "구이" in name:
        return "구이"
    if any(keyword in name for keyword in ("탕", "곰탕", "국")) or group == "국밥·탕·해장국":
        return "탕"
    if any(keyword in name for keyword in ("정식", "백반")):
        return "정식"
    if "초밥" in name:
        return "초밥"
    return "정식"


def _tags(name: str, group: str) -> list[str]:
    tags: list[str] = []

    def add(*values: str) -> None:
        for value in values:
            if value not in tags:
                tags.append(value)

    if any(keyword in name for keyword in ("밥", "정식", "백반", "국밥", "덮밥", "오므라이스", "카레라이스", "하이라이스", "돈부리")):
        add("밥")
    if (
        group in {"국밥·탕·해장국", "찌개·전골"}
        or name.endswith(("탕", "국", "찌개", "전골"))
        or any(
            keyword in name
            for keyword in ("우동", "라면", "짬뽕", "칼국수", "수제비")
        )
    ):
        add("국물")
    if _kind(name, group) == "면":
        add("면")
    if any(keyword in name for keyword in ("소고기", "소머리", "차돌", "갈비", "곰탕", "설렁탕", "도가니", "꼬리", "육회", "불고기")):
        add("소고기")
    if any(keyword in name for keyword in ("돼지", "제육", "수육", "보쌈", "돈가스", "순대", "감자탕", "내장", "스팸", "햄")):
        add("돼지고기")
    if any(keyword in name for keyword in ("닭", "치킨", "삼계", "반계", "백숙")):
        add("닭고기")
    if any(keyword in name for keyword in ("굴", "재첩", "황태", "동태", "대구", "꽃게", "해물", "오징어", "낙지", "쭈꾸미", "고등어", "삼치", "갈치", "임연수", "조기", "생선", "회", "연어", "장어", "참치", "알탕", "매운탕", "새우")):
        add("해산물")
    if any(keyword in name for keyword in ("김치", "매운", "얼큰", "육개장", "닭개장", "짬뽕", "고추장", "떡볶이", "라볶이", "비빔", "쫄면", "장칼국수", "낙지", "쭈꾸미", "오징어볶음")):
        add("매운맛")
    if any(keyword in name for keyword in ("가스", "튀김", "탕수육", "군만두")):
        add("튀김")
    if any(keyword in name for keyword in ("김밥", "라면", "햄버거", "샌드위치")):
        add("빠름")
    if any(keyword in name for keyword in ("전골", "감자탕", "뼈다귀탕", "보쌈", "수육", "모둠", "만두")):
        add("공유")
    if any(keyword in name for keyword in ("채소", "야채", "산채", "버섯", "열무", "비빔밥")):
        add("채소")
    if any(keyword in name for keyword in ("두부", "비지", "청국장", "된장")):
        add("두부")
    if any(keyword in name for keyword in ("간장", "불고기", "찜")):
        add("간장")
    if any(keyword in name for keyword in ("냉면", "밀면", "막국수", "콩국수", "김치말이국수")):
        add("차가움")
    if not tags:
        add("밥")
    return tags


def expand_menu_catalog(base_catalog: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    catalog = [dict(menu) for menu in base_catalog]
    existing = {str(menu["name"]) for menu in catalog}
    for group, names in EXPANDED_MENU_GROUPS.items():
        for name in names:
            if name in existing:
                continue
            catalog.append(
                {
                    "name": name,
                    "cuisine": _cuisine(name),
                    "kind": _kind(name, group),
                    "tags": _tags(name, group),
                }
            )
            existing.add(name)
    for menu in catalog:
        name = str(menu["name"])
        tags = list(menu["tags"])
        cool_soup = (
            any(
                keyword in name
                for keyword in (
                    "냉면",
                    "물밀면",
                    "김치말이국수",
                    "열무국수",
                    "콩국수",
                    "막국수",
                    "메밀국수",
                    "판모밀",
                    "소바",
                    "물회",
                    "중국냉면",
                )
            )
            and "비빔" not in name
        )
        restorative = any(
            keyword in name
            for keyword in (
                "백숙",
                "삼계탕",
                "반계탕",
                "추어탕",
                "도가니탕",
                "꼬리곰탕",
                "장어덮밥",
            )
        )
        if cool_soup:
            for tag in ("국물", "차가움", "시원한 국물"):
                if tag not in tags:
                    tags.append(tag)
        if restorative and "보양식" not in tags:
            tags.append("보양식")
        menu["tags"] = tags
    return catalog


IMAGE_ALIAS_RULES = (
    (("참치김치", "꽁치김치", "돼지고기김치"), "김치찌개"),
    (("차돌된장", "해물된장"), "된장찌개"),
    (("해물순두부", "차돌순두부"), "순두부찌개"),
    (("햄부대", "스팸부대"), "부대찌개"),
    (("동태", "알탕", "대구탕", "꽃게탕", "매운탕", "오징어찌개"), "동태찌개"),
    (("짜글이", "고추장찌개"), "김치찌개"),
    (("전골",), "샤브샤브"),
    (("순대국밥",), "순대국"),
    (("돼지국밥", "수육국밥", "내장국밥"), "돼지국밥"),
    (("콩나물국밥", "굴국밥"), "콩나물국밥"),
    (("황태", "올갱이", "재첩", "미역국", "소고기무국"), "북엇국"),
    (("곰탕", "도가니", "소머리"), "설렁탕"),
    (("갈비탕",), "갈비탕"),
    (("삼계탕", "반계탕"), "삼계탕"),
    (("백숙",), "삼계탕"),
    (("해장국", "장터국밥", "따로국밥", "얼큰소고기국밥"), "육개장"),
    (("감자탕", "뼈다귀탕", "우거지탕", "버섯들깨탕", "들깨수제비탕"), "갈비탕"),
    (("비빔국수", "열무국수", "비빔막국수", "비빔밀면", "쫄면"), "비빔국수"),
    (("잔치국수", "멸치국수", "김치말이국수"), "잔치국수"),
    (("칼국수", "수제비"), "칼국수"),
    (("막국수", "냉면", "밀면"), "냉면"),
    (("메밀국수", "판모밀"), "소바"),
    (("우동",), "우동"),
    (("라면", "라볶이"), "라면"),
    (("비빔밥",), "비빔밥"),
    (("회덮밥", "회정식"), "회덮밥"),
    (("물회",), "회덮밥"),
    (("김치볶음밥",), "김치볶음밥"),
    (("볶음밥",), "볶음밥"),
    (("오므라이스",), "오므라이스"),
    (("카레", "하이라이스"), "카레"),
    (("짜장밥",), "짜장면"),
    (("잡채밥",), "잡채밥"),
    (("제육덮밥",), "제육볶음"),
    (("불고기덮밥", "소고기덮밥"), "불고기"),
    (("오징어덮밥", "낙지덮밥", "쭈꾸미덮밥"), "낙지볶음"),
    (("닭갈비덮밥",), "닭갈비"),
    (("마요덮밥",), "오므라이스"),
    (("돈가스덮밥",), "가츠동"),
    (("장어덮밥", "연어덮밥"), "연어덮밥"),
    (("고추장불고기", "돼지불백", "돼지두루치기", "김치두루치기", "오삼불고기"), "제육볶음"),
    (("간장불고기", "소불고기"), "불고기"),
    (("오징어볶음", "쭈꾸미볶음"), "낙지볶음"),
    (("철판닭갈비",), "닭갈비"),
    (("고등어구이", "삼치구이", "갈치구이", "임연수구이", "조기구이", "생선구이정식"), "생선구이"),
    (("보쌈정식", "수육정식"), "보쌈"),
    (("갈비정식", "떡갈비정식"), "함박스테이크"),
    (("치즈돈가스",), "돈가스"),
    (("생선가스",), "치킨가스"),
    (("김밥",), "김밥"),
    (("떡볶이",), "떡볶이"),
    (("순대",), "순대국"),
    (("튀김", "만두"), "김밥"),
    (("떡국",), "떡국"),
    (("어묵탕",), "우동"),
    (("짜장",), "짜장면"),
    (("짬뽕",), "짬뽕"),
    (("중국냉면",), "냉면"),
    (("탕수육",), "탕수육"),
    (("마파두부",), "마파두부덮밥"),
    (("중화비빔밥",), "중화비빔밥"),
    (("초밥",), "초밥"),
    (("돈부리",), "규동"),
    (("쌀국수",), "쌀국수"),
    (("팟타이",), "팟타이"),
    (("분짜",), "분짜"),
    (("햄버거",), "햄버거"),
    (("샌드위치",), "샌드위치"),
)


def image_alias_for(name: str) -> str | None:
    for keywords, alias in IMAGE_ALIAS_RULES:
        if any(keyword in name for keyword in keywords):
            return alias
    return None
