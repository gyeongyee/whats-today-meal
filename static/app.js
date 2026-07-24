"use strict";

const STORAGE_KEY = "lunchMenuAI.v2";
const LEGACY_KEY = "lunchHistory";
const state = {retryCount: 0, selectedMenu: "", toastTimer: null};
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

function renderRecommendations(data) {
    $("recommendSection").classList.remove("hidden");
    const groupLabel = data.participant_count > 1 ? `${data.participant_count}명의 ` : "";
    $("modeDescription").textContent = data.mode === "strict"
        ? `${groupLabel}최근 3일과 의미가 겹치는 메뉴를 낮은 순위로 조정했어요.`
        : `완화 ${data.relax_level}단계 · ${groupLabel}어제와 같은 메뉴는 계속 제외했어요.`;
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
        actions.append(makeButton("이걸로 결정", "choose-button", () => chooseMenu(item.menu, card)));
        card.append(top, title, meta, reason, actions);
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

/*
 * 사람별 날짜 기록은 브라우저에만 보관합니다.
 * 추천 요청에는 최근 3일치만 전송되고 서버에는 저장되지 않습니다.
 */

$("recommendBtn").addEventListener("click", () => {
    state.retryCount = 0;
    getRecommendations("strict");
});
$("relaxBtn").addEventListener("click", () => {
    state.retryCount += 1;
    getRecommendations("relaxed");
});
$("addMemberBtn").addEventListener("click", addTeamMember);
$("clearHistoryBtn").addEventListener("click", clearHistory);
["yesterday", "twoDaysAgo", "threeDaysAgo"].forEach((id) => {
    $(id).addEventListener("change", saveRecentInputs);
});

migrateAndRollOver();
syncInputsFromStore();
