"use strict";

const STORAGE_KEY = "lunchMenuAI.v2";
const LEGACY_KEY = "lunchHistory";
const state = {
    retryCount: 0,
    selectedMenu: "",
    lastRecommendations: [],
    toastTimer: null,
};
const $ = (id) => document.getElementById(id);

function localDate(offset = 0) {
    const date = new Date();
    date.setDate(date.getDate() + offset);
    return [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0"),
    ].join("-");
}

function readStore() {
    try {
        const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
        if (parsed && parsed.version === 2 && Array.isArray(parsed.meals)) {
            if (!Array.isArray(parsed.teamMembers)) parsed.teamMembers = [];
            parsed.teamMembers = parsed.teamMembers.slice(0, 9).map((member, index) => {
                const meals = Array.isArray(member.meals) ? member.meals : [
                    {date: localDate(-1), menu: member.yesterday || ""},
                    {date: localDate(-2), menu: member.twoDaysAgo || ""},
                    {date: localDate(-3), menu: member.threeDaysAgo || ""},
                ].filter((item) => item.menu);
                return {
                    id: member.id || `member-${index}-${Date.now()}`,
                    name: String(member.name || `팀원 ${index + 1}`).slice(0, 20),
                    meals,
                };
            });
            return parsed;
        }
    } catch (_) { /* 손상된 로컬 값은 초기화 */ }
    return {version: 2, meals: [], today: null, teamMembers: []};
}

function writeStore(store) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function upsertMeal(store, date, menu) {
    store.meals = store.meals.filter((item) => item.date !== date);
    if (menu) store.meals.push({date, menu});
    store.meals.sort((a, b) => b.date.localeCompare(a.date));
    store.meals = store.meals.slice(0, 90);
}

function migrateAndRollOver() {
    const store = readStore();
    try {
        const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || "null");
        if (legacy && store.meals.length === 0) {
            upsertMeal(store, localDate(-1), String(legacy.yesterday || "").trim());
            upsertMeal(store, localDate(-2), String(legacy.twoDaysAgo || "").trim());
            upsertMeal(store, localDate(-3), String(legacy.threeDaysAgo || "").trim());
            localStorage.removeItem(LEGACY_KEY);
        }
    } catch (_) { localStorage.removeItem(LEGACY_KEY); }

    if (store.today && store.today.date !== localDate()) {
        upsertMeal(store, store.today.date, store.today.menu);
        store.today = null;
    }
    writeStore(store);
}

function mealOn(store, date) {
    return store.meals.find((item) => item.date === date)?.menu || "";
}

function syncInputsFromStore() {
    const store = readStore();
    $("yesterday").value = mealOn(store, localDate(-1));
    $("twoDaysAgo").value = mealOn(store, localDate(-2));
    $("threeDaysAgo").value = mealOn(store, localDate(-3));
    renderTeamMembers();
    renderTimeline();
}

function saveRecentInputs() {
    const store = readStore();
    [
        [-1, $("yesterday").value.trim()],
        [-2, $("twoDaysAgo").value.trim()],
        [-3, $("threeDaysAgo").value.trim()],
    ].forEach(([offset, menu]) => upsertMeal(store, localDate(offset), menu));
    writeStore(store);
    renderTimeline();
}

function memberInput(labelText, field, value, placeholder) {
    const label = document.createElement("label");
    const span = document.createElement("span");
    span.textContent = labelText;
    const input = document.createElement("input");
    input.dataset.field = field;
    input.value = value || "";
    input.maxLength = 120;
    input.autocomplete = "off";
    input.placeholder = placeholder;
    input.addEventListener("change", saveTeamMembers);
    label.append(span, input);
    return label;
}

function collectTeamMembers() {
    return [...document.querySelectorAll(".team-member-card")].map((card, index) => ({
        id: card.dataset.id,
        name: card.querySelector('[data-field="name"]').value.trim() || `팀원 ${index + 1}`,
        yesterday: card.querySelector('[data-field="yesterday"]').value.trim(),
        twoDaysAgo: card.querySelector('[data-field="twoDaysAgo"]').value.trim(),
        threeDaysAgo: card.querySelector('[data-field="threeDaysAgo"]').value.trim(),
    }));
}

function saveTeamMembers() {
    const store = readStore();
    store.teamMembers = collectTeamMembers().map((member) => {
        const saved = store.teamMembers.find((item) => item.id === member.id);
        const next = {...saved, id: member.id, name: member.name, meals: [...(saved?.meals || [])]};
        [
            [-1, member.yesterday],
            [-2, member.twoDaysAgo],
            [-3, member.threeDaysAgo],
        ].forEach(([offset, menu]) => upsertPersonMeal(next, localDate(offset), menu));
        return next;
    });
    writeStore(store);
    renderTimeline();
}

function upsertPersonMeal(person, date, menu) {
    person.meals = (person.meals || []).filter((item) => item.date !== date);
    if (menu) person.meals.push({date, menu});
    person.meals.sort((a, b) => b.date.localeCompare(a.date));
    person.meals = person.meals.slice(0, 90);
}

function memberMealOn(member, date) {
    return member.meals?.find((item) => item.date === date)?.menu || "";
}

function renderTeamMembers() {
    const members = readStore().teamMembers.slice(0, 9);
    const container = $("teamMembers");
    container.replaceChildren();
    $("teamEmpty").classList.toggle("hidden", members.length > 0);

    members.forEach((member, index) => {
        const card = document.createElement("article");
        card.className = "team-member-card";
        card.dataset.id = member.id;

        const header = document.createElement("div");
        header.className = "member-card-header";
        const badge = document.createElement("span");
        badge.textContent = `동료 ${index + 1}`;
        const name = document.createElement("input");
        name.className = "member-name";
        name.dataset.field = "name";
        name.value = member.name || `팀원 ${index + 1}`;
        name.maxLength = 20;
        name.setAttribute("aria-label", `${index + 1}번째 팀원 이름`);
        name.addEventListener("change", saveTeamMembers);
        const remove = makeButton("삭제", "remove-member-button", () => {
            const store = readStore();
            store.teamMembers = store.teamMembers.filter((item) => item.id !== member.id);
            writeStore(store);
            renderTeamMembers();
            showToast("팀원을 목록에서 뺐어요.");
        });
        header.append(badge, name, remove);

        const meals = document.createElement("div");
        meals.className = "member-meals";
        meals.append(
            memberInput("어제", "yesterday", memberMealOn(member, localDate(-1)), "예: 제육볶음, 라면"),
            memberInput("2일 전", "twoDaysAgo", memberMealOn(member, localDate(-2)), "예: 김치찌개"),
            memberInput("3일 전", "threeDaysAgo", memberMealOn(member, localDate(-3)), "예: 초밥")
        );
        card.append(header, meals);
        container.append(card);
    });
}

function addTeamMember() {
    const store = readStore();
    if (store.teamMembers.length >= 9) return showToast("팀원은 최대 9명까지 추가할 수 있어요.");
    const number = store.teamMembers.length + 1;
    store.teamMembers.push({
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        name: `팀원 ${number}`,
        meals: [],
    });
    writeStore(store);
    renderTeamMembers();
    $("teamMembers").lastElementChild?.querySelector(".member-name")?.focus();
}

function formatDate(dateString) {
    const date = new Date(`${dateString}T00:00:00`);
    return new Intl.DateTimeFormat("ko-KR", {month: "long", day: "numeric", weekday: "short"}).format(date);
}

function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.remove("hidden");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.add("hidden"), 2800);
}

function checkedValues(selector) {
    return [...document.querySelectorAll(`${selector}:checked`)].map((input) => input.value);
}

const SPECIAL_IMAGE_SEARCH = {
    "라면": "Korean ramyeon noodle soup bowl",
    "쌀국수": "Vietnamese pho noodle soup bowl",
    "난과 커리": "Indian naan bread with curry meal",
    "갈릭 쉬림프": "Hawaiian garlic shrimp plate",
    "마파두부덮밥": "mapo tofu rice",
};

const LOCAL_MENU_IMAGES = {
    "두부덮밥": "/static/images/menus/tofu-rice-bowl.png",
    "비건 카레": "/static/images/menus/vegan-curry.png",
    "비건 비빔밥": "/static/images/menus/vegan-bibimbap.png",
    "콩국수": "/static/images/menus/kongguksu.png",
    "쌀 베이글": "/static/images/menus/rice-bagel.png",
    "비건 파스타": "/static/images/menus/vegan-pasta.png",
    "당근 라페 샌드위치": "/static/images/menus/carrot-rappee-sandwich.png",
    "비건 김밥": "/static/images/menus/vegan-gimbap.png",
};

async function findExactMenuImage(menu) {
    const generatedImage = window.APP_CONFIG?.menuImages?.[menu];
    if (generatedImage) {
        return {src: generatedImage, page: ""};
    }
    if (LOCAL_MENU_IMAGES[menu]) {
        return {src: LOCAL_MENU_IMAGES[menu], page: ""};
    }

    const cacheKey = `menuImage:v3:${menu}`;
    const cached = sessionStorage.getItem(cacheKey);
    if (cached) return JSON.parse(cached);

    if (SPECIAL_IMAGE_SEARCH[menu]) {
        const commonsParams = new URLSearchParams({
            action: "query",
            generator: "search",
            gsrsearch: SPECIAL_IMAGE_SEARCH[menu],
            gsrnamespace: "6",
            gsrlimit: "1",
            prop: "imageinfo",
            iiprop: "url",
            iiurlwidth: "800",
            format: "json",
            origin: "*",
        });
        try {
            const commons = await fetch(`https://commons.wikimedia.org/w/api.php?${commonsParams}`)
                .then((response) => response.ok ? response.json() : null);
            const filePage = Object.values(commons?.query?.pages || {})[0];
            const imageInfo = filePage?.imageinfo?.[0];
            if (imageInfo?.thumburl || imageInfo?.url) {
                const result = {
                    src: imageInfo.thumburl || imageInfo.url,
                    page: imageInfo.descriptionurl || "",
                };
                sessionStorage.setItem(cacheKey, JSON.stringify(result));
                return result;
            }
        } catch (_) { /* 정확한 문서 대표 이미지로 전환 */ }
    }

    const exactUrl = `https://ko.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(menu)}`;
    try {
        const exact = await fetch(exactUrl).then((response) => response.ok ? response.json() : null);
        if (exact?.thumbnail?.source) {
            const result = {src: exact.thumbnail.source, page: exact.content_urls?.desktop?.page || ""};
            sessionStorage.setItem(cacheKey, JSON.stringify(result));
            return result;
        }
    } catch (_) { /* 검색 API로 한 번 더 시도 */ }

    const params = new URLSearchParams({
        action: "query",
        generator: "search",
        gsrsearch: `${menu} 음식`,
        gsrlimit: "1",
        prop: "pageimages|info",
        piprop: "thumbnail",
        pithumbsize: "800",
        inprop: "url",
        format: "json",
        origin: "*",
    });
    try {
        const searched = await fetch(`https://ko.wikipedia.org/w/api.php?${params}`)
            .then((response) => response.ok ? response.json() : null);
        const page = Object.values(searched?.query?.pages || {})[0];
        if (page?.thumbnail?.source) {
            const result = {src: page.thumbnail.source, page: page.fullurl || ""};
            sessionStorage.setItem(cacheKey, JSON.stringify(result));
            return result;
        }
    } catch (_) { /* 생성한 기본 이미지 유지 */ }
    return null;
}

async function applyExactMenuImage(menu, visual, image, sourceLink) {
    const result = await findExactMenuImage(menu);
    if (!result) return;
    image.addEventListener("load", () => visual.classList.add("has-photo"), {once: true});
    image.src = result.src;
    if (result.page) {
        sourceLink.href = result.page;
        sourceLink.classList.remove("hidden");
    }
}

async function apiFetch(url, options) {
    const response = await fetch(url, options);
    let data;
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok) {
        const message = typeof data.detail === "string" ? data.detail : "요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.";
        throw new Error(message);
    }
    return data;
}

async function getRecommendations(mode = "strict") {
    saveRecentInputs();
    saveTeamMembers();
    const teamMembers = collectTeamMembers()
        .map((member) => ({
            name: member.name,
            yesterday: member.yesterday,
            two_days_ago: member.twoDaysAgo,
            three_days_ago: member.threeDaysAgo,
        }));
    const payload = {
        yesterday: $("yesterday").value.trim(),
        two_days_ago: $("twoDaysAgo").value.trim(),
        three_days_ago: $("threeDaysAgo").value.trim(),
        mode,
        avoid_spicy: $("avoidSpicy").checked,
        prefer_soup: $("preferSoup").checked,
        prefer_light: $("preferLight").checked,
        prefer_hearty: $("preferHearty").checked,
        prefer_quick: $("preferQuick").checked,
        prefer_share: $("preferShare").checked,
        preferred_cuisines: checkedValues(".cuisine-filter"),
        preferred_tags: checkedValues(".tag-filter"),
        previous_recommendations:
            mode === "relaxed" ? state.lastRecommendations : [],
        retry_count: state.retryCount,
        team_members: teamMembers,
    };
    const button = $("recommendBtn");
    button.disabled = true;
    button.firstElementChild.textContent = "AI가 메뉴를 비교하고 있어요…";
    try {
        const data = await apiFetch("/api/recommend", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload),
        });
        renderRecommendations(data);
    } catch (error) {
        showToast(error.message);
    } finally {
        button.disabled = false;
        button.firstElementChild.textContent = "오늘 메뉴 3개 추천받기";
    }
}

function makeButton(label, className, handler) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", handler);
    return button;
}

async function openMenuDetails(menu) {
    const dialog = $("menuDetailDialog");
    $("menuDetailTitle").textContent = menu;
    $("menuDetailMeta").textContent = "메뉴 정보를 불러오는 중이에요…";
    $("menuDetailDescription").textContent = "";
    $("menuDetailCalories").textContent = "";
    $("menuDetailTags").replaceChildren();

    const visual = $("menuDetailVisual");
    const image = $("menuDetailImage");
    const emoji = $("menuDetailEmoji");
    const sourceLink = $("menuDetailSource");
    visual.className = "menu-detail-visual";
    image.src = "/static/images/food-card-bg.webp";
    emoji.textContent = "🍽️";
    sourceLink.classList.add("hidden");
    sourceLink.removeAttribute("href");

    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");

    try {
        const item = await apiFetch(`/api/menus/${encodeURIComponent(menu)}`);
        $("menuDetailMeta").textContent = `${item.cuisine} · ${item.kind}`;
        $("menuDetailTitle").textContent = item.menu;
        $("menuDetailDescription").textContent = item.description;
        $("menuDetailCalories").textContent =
            `예상 ${item.calorie_min.toLocaleString("ko-KR")}–${item.calorie_max.toLocaleString("ko-KR")} kcal`;
        emoji.textContent = item.emoji;
        visual.classList.add(`visual-${item.visual_key}`);
        item.tags.forEach((tag) => {
            const chip = document.createElement("span");
            chip.textContent = `#${tag}`;
            $("menuDetailTags").append(chip);
        });
        applyExactMenuImage(item.menu, visual, image, sourceLink);
    } catch (error) {
        $("menuDetailMeta").textContent = "정보를 불러오지 못했어요.";
        $("menuDetailDescription").textContent = error.message;
    }
}

function renderRecommendations(data) {
    state.lastRecommendations = data.recommendations.map((item) => item.menu);
    $("recommendSection").classList.remove("hidden");
    const groupLabel = data.participant_count > 1 ? `${data.participant_count}명의 ` : "";
    $("modeDescription").textContent = data.mode === "strict"
        ? `${groupLabel}최근 3일과 의미가 겹치는 메뉴를 낮은 순위로 조정했어요.`
        : `완화 ${data.relax_level}단계 · 방금 추천한 3개와 ${groupLabel}어제 메뉴를 제외했어요.`;
    $("engineBadge").textContent = `✦ ${data.engine_label}`;
    const container = $("recommendations");
    container.replaceChildren();

    data.recommendations.forEach((item, index) => {
        const card = document.createElement("article");
        card.className = "menu-card";
        const top = document.createElement("div");
        top.className = "menu-card-top";
        const number = document.createElement("span");
        number.className = "menu-number";
        number.textContent = `0${index + 1}`;
        const match = document.createElement("span");
        match.className = "match";
        match.textContent = item.similarity < 0.25 ? "새로운 선택" : "취향 확장";
        top.append(number, match);
        const title = document.createElement("h3");
        title.textContent = item.menu;
        const visual = document.createElement("div");
        visual.className = `menu-visual visual-${item.visual_key}`;
        visual.setAttribute("role", "img");
        visual.setAttribute("aria-label", `${item.menu} 음식 이미지`);
        const image = document.createElement("img");
        image.src = "/static/images/food-card-bg.webp";
        image.alt = "";
        const emoji = document.createElement("span");
        emoji.textContent = item.emoji;
        const sourceLink = document.createElement("a");
        sourceLink.className = "image-source hidden";
        sourceLink.target = "_blank";
        sourceLink.rel = "noopener noreferrer";
        sourceLink.textContent = "사진 출처";
        sourceLink.setAttribute("aria-label", `${item.menu} 사진 출처 보기`);
        visual.append(image, emoji, sourceLink);
        applyExactMenuImage(item.menu, visual, image, sourceLink);
        const meta = document.createElement("p");
        meta.className = "menu-meta";
        meta.textContent = `${item.cuisine} · ${item.kind}`;
        const description = document.createElement("p");
        description.className = "menu-description";
        description.textContent = item.description;
        const calories = document.createElement("p");
        calories.className = "menu-calories";
        calories.textContent = `예상 ${item.calorie_min.toLocaleString("ko-KR")}–${item.calorie_max.toLocaleString("ko-KR")} kcal`;
        const reason = document.createElement("p");
        reason.className = "menu-reason";
        reason.textContent = item.reason;
        const actions = document.createElement("div");
        actions.className = "card-actions";
        actions.append(makeButton("이걸로 결정", "choose-button", () => chooseMenu(item.menu, card)));
        card.append(top, visual, title, meta, description, calories, reason, actions);
        container.append(card);
    });
    $("recommendSection").scrollIntoView({behavior: "smooth", block: "start"});
}

function chooseMenu(menu, selectedCard) {
    const store = readStore();
    store.today = {date: localDate(), menu};
    upsertMeal(store, localDate(), menu);
    store.teamMembers.forEach((member) => upsertPersonMeal(member, localDate(), menu));
    writeStore(store);
    state.selectedMenu = menu;
    document.querySelectorAll(".menu-card").forEach((card) => card.classList.remove("selected"));
    selectedCard?.classList.add("selected");
    renderTimeline();
    showToast(`오늘은 ${menu}! 선택을 저장했어요.`);
}

function renderTimeline() {
    const store = readStore();
    const today = $("todayChoice");
    today.replaceChildren();
    if (store.today?.date === localDate()) {
        const label = document.createElement("span");
        label.textContent = "오늘의 선택";
        const strong = document.createElement("strong");
        strong.textContent = store.today.menu;
        const clear = makeButton("선택 취소", "text-button", () => {
            const next = readStore();
            next.today = null;
            upsertMeal(next, localDate(), "");
            next.teamMembers.forEach((member) => upsertPersonMeal(member, localDate(), ""));
            writeStore(next);
            syncInputsFromStore();
        });
        today.append(label, strong, clear);
        today.classList.remove("empty");
    } else {
        today.textContent = "아직 오늘의 메뉴를 결정하지 않았어요.";
        today.classList.add("empty");
    }

    const timeline = $("timeline");
    timeline.replaceChildren();
    const people = [
        {id: "self", name: "나", meals: store.meals, self: true},
        ...store.teamMembers.map((member) => ({...member, self: false})),
    ];
    people.forEach((person) => {
        const card = document.createElement("section");
        card.className = "person-timeline";
        const heading = document.createElement("div");
        heading.className = "person-timeline-heading";
        const name = document.createElement("h3");
        name.textContent = person.name;
        const count = document.createElement("span");
        count.textContent = `${person.meals.length}일 기록`;
        heading.append(name, count);
        card.append(heading);

        const recent = person.meals.slice(0, 12);
        if (!recent.length) {
            const empty = document.createElement("p");
            empty.className = "person-empty";
            empty.textContent = "아직 저장된 식사가 없어요.";
            card.append(empty);
        }
        recent.forEach((item) => {
            const row = document.createElement("article");
            row.className = "timeline-row";
            const date = document.createElement("time");
            date.dateTime = item.date;
            date.textContent = formatDate(item.date);
            const input = document.createElement("input");
            input.value = item.menu;
            input.maxLength = 120;
            input.setAttribute("aria-label", `${person.name}의 ${formatDate(item.date)} 메뉴`);
            const update = (menu) => {
                const next = readStore();
                if (person.self) {
                    upsertMeal(next, item.date, menu);
                } else {
                    const member = next.teamMembers.find((entry) => entry.id === person.id);
                    if (member) upsertPersonMeal(member, item.date, menu);
                }
                writeStore(next);
                syncInputsFromStore();
            };
            const save = makeButton("저장", "small-button", () => {
                update(input.value.trim());
                showToast(`${person.name}의 식사 기록을 수정했어요.`);
            });
            const remove = makeButton("삭제", "small-button ghost", () => {
                update("");
                showToast(`${person.name}의 식사 기록을 삭제했어요.`);
            });
            row.append(date, input, save, remove);
            card.append(row);
        });
        timeline.append(card);
    });
}

function clearHistory() {
    if (!window.confirm("팀원 목록과 사람별 식사 기록을 모두 삭제할까요?")) return;
    localStorage.removeItem(STORAGE_KEY);
    migrateAndRollOver();
    syncInputsFromStore();
    showToast("모든 사람의 식사 기록을 삭제했어요.");
}

const seasonalMobileQuery = window.matchMedia("(max-width: 560px)");

function syncSeasonalAccordion(mediaQuery) {
    document.querySelectorAll(".season-card").forEach((card) => {
        if (mediaQuery.matches) {
            card.removeAttribute("open");
        } else {
            card.setAttribute("open", "");
        }
    });
}

const preferSpicyInput = document.querySelector('.tag-filter[value="매운맛"]');

function keepSpicyChoicesExclusive(changedInput, otherInput) {
    if (changedInput.checked) otherInput.checked = false;
}

/*
 * 사람별 날짜 기록은 브라우저에만 보관합니다.
 * 추천 요청에는 최근 3일치만 전송되고 서버에는 저장되지 않습니다.
 */

$("recommendBtn").addEventListener("click", () => {
    state.retryCount = 0;
    state.lastRecommendations = [];
    getRecommendations("strict");
});
$("relaxBtn").addEventListener("click", () => {
    state.retryCount += 1;
    getRecommendations("relaxed");
});
$("addMemberBtn").addEventListener("click", addTeamMember);
$("clearHistoryBtn").addEventListener("click", clearHistory);
$("avoidSpicy").addEventListener("change", () => {
    keepSpicyChoicesExclusive($("avoidSpicy"), preferSpicyInput);
});
preferSpicyInput.addEventListener("change", () => {
    keepSpicyChoicesExclusive(preferSpicyInput, $("avoidSpicy"));
});
$("menuDetailClose").addEventListener("click", () => $("menuDetailDialog").close());
$("menuDetailDialog").addEventListener("click", (event) => {
    if (event.target === $("menuDetailDialog")) $("menuDetailDialog").close();
});
document.querySelectorAll(".catalog-menu, .season-menu").forEach((button) => {
    button.addEventListener("click", () => openMenuDetails(button.dataset.menu));
});
document.querySelectorAll(".situation-tab").forEach((button) => {
    button.addEventListener("click", () => {
        document.querySelectorAll(".situation-tab").forEach((tab) => {
            const selected = tab === button;
            tab.classList.toggle("active", selected);
            tab.setAttribute("aria-selected", String(selected));
        });
        document.querySelectorAll("[data-situation-panel]").forEach((panel) => {
            panel.classList.toggle("hidden", panel.dataset.situationPanel !== button.dataset.situation);
        });
    });
});
["yesterday", "twoDaysAgo", "threeDaysAgo"].forEach((id) => {
    $(id).addEventListener("change", saveRecentInputs);
});

migrateAndRollOver();
syncInputsFromStore();
syncSeasonalAccordion(seasonalMobileQuery);
seasonalMobileQuery.addEventListener("change", (event) => syncSeasonalAccordion(event));
