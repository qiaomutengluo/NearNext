const state = {
  data: null,
  source: "all",
  interest: "all",
  query: "",
};

const SOURCE_LABELS = {
  mcgill: "McGill",
  concordia: "Concordia",
};

async function loadData() {
  const response = await fetch("events.json");
  if (!response.ok) {
    throw new Error(`无法加载 events.json (${response.status})`);
  }
  return response.json();
}

function formatRunAt(value) {
  if (!value) return "未知";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatEventTime(event) {
  if (event.raw_date_text) return event.raw_date_text;
  if (!event.start_at) return "时间待定";
  const start = new Date(event.start_at);
  const end = event.end_at ? new Date(event.end_at) : null;
  const datePart = start.toLocaleDateString("zh-CN", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const timePart = start.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
  if (!end || end.getTime() === start.getTime()) {
    return `${datePart} ${timePart}`;
  }
  const endPart = end.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${datePart} ${timePart} – ${endPart}`;
}

function dayKey(event) {
  if (!event.start_at) return "未定";
  const date = new Date(event.start_at);
  if (Number.isNaN(date.getTime())) return "未定";
  return date.toLocaleDateString("zh-CN", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

function renderMeta(data) {
  const meta = document.getElementById("meta");
  const windowText =
    data.window?.start && data.window?.end
      ? `${data.window.start} → ${data.window.end}`
      : "近期窗口";
  meta.innerHTML = `
    <span class="pill">更新于 ${formatRunAt(data.run_at)}</span>
    <span class="pill">窗口 ${windowText}</span>
    <span class="pill">${data.count ?? 0} 场活动</span>
  `;
}

function renderStats(data) {
  const statsEl = document.getElementById("stats");
  const totals = data.totals || {};
  const bySource = data.by_source || {};
  const byInterest = data.by_interest || {};
  const interestSummary = Object.entries(byInterest)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");

  statsEl.hidden = false;
  statsEl.innerHTML = `
    <div class="stat-card"><strong>${totals.filtered_events ?? data.count ?? 0}</strong><span>筛选保留</span></div>
    <div class="stat-card"><strong>${totals.all_events ?? "—"}</strong><span>原始爬取</span></div>
    <div class="stat-card"><strong>${bySource.mcgill ?? 0}</strong><span>McGill</span></div>
    <div class="stat-card"><strong>${bySource.concordia ?? 0}</strong><span>Concordia</span></div>
    <div class="stat-card"><strong>${interestSummary || "—"}</strong><span>兴趣分布</span></div>
  `;
}

function makeChip(label, value, group) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "chip";
  button.textContent = label;
  button.dataset.value = value;
  button.dataset.group = group;
  if (
    (group === "source" && state.source === value) ||
    (group === "interest" && state.interest === value)
  ) {
    button.classList.add("active");
  }
  button.addEventListener("click", () => {
    if (group === "source") state.source = value;
    if (group === "interest") state.interest = value;
    renderFilters();
    renderEvents();
  });
  return button;
}

function renderFilters() {
  const sourceFilters = document.getElementById("source-filters");
  const interestFilters = document.getElementById("interest-filters");
  sourceFilters.innerHTML = "";
  interestFilters.innerHTML = "";

  sourceFilters.append(makeChip("全部学校", "all", "source"));
  Object.entries(SOURCE_LABELS).forEach(([value, label]) => {
    sourceFilters.append(makeChip(label, value, "source"));
  });

  const interests = new Set();
  (state.data?.events || []).forEach((event) => {
    (event.matched_interests || []).forEach((item) => interests.add(item));
  });

  interestFilters.append(makeChip("全部兴趣", "all", "interest"));
  [...interests].sort().forEach((interest) => {
    const event = state.data.events.find((item) =>
      (item.matched_interests || []).includes(interest),
    );
    const label =
      event?.interest_labels?.[
        (event.matched_interests || []).indexOf(interest)
      ] || interest;
    interestFilters.append(makeChip(label, interest, "interest"));
  });
}

function matchesFilters(event) {
  if (state.source !== "all" && event.source !== state.source) return false;
  if (
    state.interest !== "all" &&
    !(event.matched_interests || []).includes(state.interest)
  ) {
    return false;
  }
  if (state.query) {
    const haystack = [
      event.title,
      event.description,
      event.location,
      ...(event.interest_labels || []),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    if (!haystack.includes(state.query)) return false;
  }
  return true;
}

function renderEvents() {
  const container = document.getElementById("events");
  const empty = document.getElementById("empty");
  const events = (state.data?.events || [])
    .filter(matchesFilters)
    .sort((a, b) => {
      const aTime = a.start_at ? new Date(a.start_at).getTime() : Infinity;
      const bTime = b.start_at ? new Date(b.start_at).getTime() : Infinity;
      return aTime - bTime;
    });

  container.innerHTML = "";
  empty.hidden = events.length > 0;
  if (!events.length) return;

  const groups = new Map();
  events.forEach((event) => {
    const key = dayKey(event);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(event);
  });

  groups.forEach((dayEvents, label) => {
    const section = document.createElement("section");
    section.className = "day-group";
    section.innerHTML = `<h2>${label}</h2>`;

    dayEvents.forEach((event) => {
      const card = document.createElement("article");
      card.className = "card";
      const tags = (event.interest_labels || event.matched_interests || [])
        .map((tag) => `<span class="tag">${tag}</span>`)
        .join("");
      const title = event.url
        ? `<a href="${event.url}" target="_blank" rel="noopener noreferrer">${event.title}</a>`
        : event.title;
      card.innerHTML = `
        <div class="card-header">
          <span class="badge ${event.source}">${SOURCE_LABELS[event.source] || event.source}</span>
          ${tags}
        </div>
        <h3>${title}</h3>
        <p class="time">${formatEventTime(event)}</p>
        ${event.location ? `<p class="location">${event.location}</p>` : ""}
        ${event.description ? `<p class="description">${event.description}</p>` : ""}
      `;
      section.appendChild(card);
    });

    container.appendChild(section);
  });
}

async function init() {
  const errorEl = document.getElementById("error");
  try {
    state.data = await loadData();
    renderMeta(state.data);
    renderStats(state.data);
    renderFilters();
    renderEvents();

    document.getElementById("search").addEventListener("input", (event) => {
      state.query = event.target.value.trim().toLowerCase();
      renderEvents();
    });
  } catch (error) {
    errorEl.hidden = false;
    errorEl.textContent = error.message;
  }
}

init();
