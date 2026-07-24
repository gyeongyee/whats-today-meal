"use strict";

const STORAGE_KEY = "lunchMenuAI.v2";
const LEGACY_KEY = "lunchHistory";
const state = {x: null, y: null, retryCount: 0, selectedMenu: "", toastTimer: null};
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
        if (parsed && parsed.version === 2 && Array.isArray(parsed.meals)) return parsed;
    } catch (_) { /* 손상된 로컬 값은 초기화 */ }
    return {version: 2, meals: [], today: null};
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
    $("address").value = localStorage.getItem("lunchAddress") || "";
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
    const payload = {
        yesterday: $("yesterday").value.trim(),
        two_days_ago: $("twoDaysAgo").value.trim(),
        three_days_ago: $("threeDaysAgo").value.trim(),
        mode,
        avoid_spicy: $("avoidSpicy").checked,
        prefer_soup: $("preferSoup").checked,
        prefer_light: $("preferLight").checked,
        retry_count: state.retryCount,
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

function renderRecommendations(data) {
    $("recommendSection").classList.remove("hidden");
    $("modeDescription").textContent = data.mode === "strict"
        ? "최근 3일과 의미가 겹치는 메뉴를 낮은 순위로 조정했어요."
        : `완화 ${data.relax_level}단계 · 어제와 같은 메뉴는 계속 제외했어요.`;
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
        const meta = document.createElement("p");
        meta.className = "menu-meta";
        meta.textContent = `${item.cuisine} · ${item.kind}`;
        const reason = document.createElement("p");
        reason.className = "menu-reason";
        reason.textContent = item.reason;
        const actions = document.createElement("div");
        actions.className = "card-actions";
        actions.append(
            makeButton("이걸로 결정", "choose-button", () => chooseMenu(item.menu, card)),
            makeButton("주변 식당 ↗", "find-button", () => findRestaurants(item.search_query))
        );
        card.append(top, title, meta, reason, actions);
        container.append(card);
    });
    $("recommendSection").scrollIntoView({behavior: "smooth", block: "start"});
}

function chooseMenu(menu, selectedCard) {
    const store = readStore();
    store.today = {date: localDate(), menu};
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
            writeStore(next);
            renderTimeline();
        });
        today.append(label, strong, clear);
        today.classList.remove("empty");
    } else {
        today.textContent = "아직 오늘의 메뉴를 결정하지 않았어요.";
        today.classList.add("empty");
    }

    const timeline = $("timeline");
    timeline.replaceChildren();
    const recent = store.meals.slice(0, 12);
    if (!recent.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = "최근 식사를 입력하면 날짜별 기록이 여기에 쌓여요.";
        timeline.append(empty);
        return;
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
        input.setAttribute("aria-label", `${formatDate(item.date)} 메뉴`);
        const save = makeButton("저장", "small-button", () => {
            const next = readStore();
            upsertMeal(next, item.date, input.value.trim());
            writeStore(next);
            syncInputsFromStore();
            showToast("식사 기록을 수정했어요.");
        });
        const remove = makeButton("삭제", "small-button ghost", () => {
            const next = readStore();
            upsertMeal(next, item.date, "");
            writeStore(next);
            syncInputsFromStore();
            showToast("식사 기록을 삭제했어요.");
        });
        row.append(date, input, save, remove);
        timeline.append(row);
    });
}

async function applyAddress() {
    const address = $("address").value.trim();
    if (!address) return showToast("주소를 입력해 주세요.");
    $("locationStatus").textContent = "주소를 확인하고 있어요…";
    try {
        const data = await apiFetch(`/api/geocode?address=${encodeURIComponent(address)}`);
        state.x = Number(data.x);
        state.y = Number(data.y);
        localStorage.setItem("lunchAddress", address);
        $("locationStatus").textContent = `✓ ${data.address_name}`;
        showToast("검색 위치를 설정했어요.");
    } catch (error) {
        $("locationStatus").textContent = "주소 설정 실패";
        showToast(error.message);
    }
}

function useCurrentLocation() {
    if (!navigator.geolocation) return showToast("이 브라우저는 현재 위치를 지원하지 않아요.");
    $("locationStatus").textContent = "현재 위치를 확인하고 있어요…";
    navigator.geolocation.getCurrentPosition(
        ({coords}) => {
            state.x = coords.longitude;
            state.y = coords.latitude;
            $("locationStatus").textContent = "✓ 현재 위치가 적용됐어요.";
            showToast("검색 위치를 설정했어요.");
        },
        () => {
            $("locationStatus").textContent = "현재 위치 사용 실패";
            showToast("브라우저 위치 권한을 허용한 뒤 다시 시도해 주세요.");
        },
        {enableHighAccuracy: true, timeout: 9000, maximumAge: 300000}
    );
}

async function findRestaurants(menu) {
    if (state.x === null && $("address").value.trim()) await applyAddress();
    if (state.x === null || state.y === null) return showToast("먼저 주소 또는 현재 위치를 설정해 주세요.");
    const radius = Number($("radius").value);
    $("restaurantSection").classList.remove("hidden");
    $("restaurantTitle").textContent = `${menu} 먹으러 어디로 갈까요?`;
    $("restaurants").innerHTML = '<p class="loading">가까운 식당을 찾고 있어요…</p>';
    $("restaurantSection").scrollIntoView({behavior: "smooth", block: "start"});
    try {
        const params = new URLSearchParams({query: menu, x: state.x, y: state.y, radius});
        const data = await apiFetch(`/api/restaurants?${params}`);
        renderRestaurants(data);
    } catch (error) {
        const message = document.createElement("p");
        message.className = "empty-state";
        message.textContent = error.message;
        $("restaurants").replaceChildren(message);
        showToast(error.message);
    }
}

function renderRestaurants(data) {
    const container = $("restaurants");
    container.replaceChildren();
    if (!data.restaurants.length) {
        const empty = document.createElement("p");
        empty.className = "empty-state";
        empty.textContent = data.suggestion;
        container.append(empty);
        return;
    }
    data.restaurants.forEach((item) => {
        const article = document.createElement("article");
        article.className = "restaurant-item";
        const info = document.createElement("div");
        const title = document.createElement("h3");
        title.textContent = item.name;
        const category = document.createElement("p");
        category.textContent = item.category;
        const address = document.createElement("p");
        address.textContent = item.address;
        info.append(title, category, address);
        if (item.phone) {
            const phone = document.createElement("p");
            phone.textContent = item.phone;
            info.append(phone);
        }
        if (item.place_url) {
            const link = document.createElement("a");
            link.href = item.place_url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            link.textContent = "카카오맵 상세페이지 ↗";
            info.append(link);
        }
        const distance = document.createElement("strong");
        distance.className = "distance";
        distance.textContent = item.distance_m < 1000 ? `${item.distance_m}m` : `${(item.distance_m / 1000).toFixed(1)}km`;
        article.append(info, distance);
        container.append(article);
    });
}

function clearHistory() {
    if (!window.confirm("오늘 선택과 모든 식사 기록을 삭제할까요?")) return;
    localStorage.removeItem(STORAGE_KEY);
    migrateAndRollOver();
    syncInputsFromStore();
    showToast("모든 식사 기록을 삭제했어요.");
}

$("recommendBtn").addEventListener("click", () => {
    state.retryCount = 0;
    getRecommendations("strict");
});
$("relaxBtn").addEventListener("click", () => {
    state.retryCount += 1;
    getRecommendations("relaxed");
});
$("useAddressBtn").addEventListener("click", applyAddress);
$("useLocationBtn").addEventListener("click", useCurrentLocation);
$("clearHistoryBtn").addEventListener("click", clearHistory);
$("address").addEventListener("keydown", (event) => {
    if (event.key === "Enter") applyAddress();
});
["yesterday", "twoDaysAgo", "threeDaysAgo"].forEach((id) => {
    $(id).addEventListener("change", saveRecentInputs);
});

migrateAndRollOver();
syncInputsFromStore();
