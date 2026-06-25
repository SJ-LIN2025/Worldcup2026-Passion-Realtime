let bracketZoom = 1;
let isBracketDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let dragScrollLeft = 0;
let dragScrollTop = 0;
const STATE_URL = "data/state_snapshot.json";

function fmtTime(ms) {
  if (!ms) return "未更新";
  const d = new Date(ms);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}:${pad(d.getSeconds())}`;
}

function esc(s) {
  return (s ?? "").toString().replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

const TEAM_FLAGS = {
  "阿尔及利亚": "🇩🇿",
  "阿根廷": "🇦🇷",
  "澳大利亚": "🇦🇺",
  "奥地利": "🇦🇹",
  "比利时": "🇧🇪",
  "波黑": "🇧🇦",
  "巴西": "🇧🇷",
  "加拿大": "🇨🇦",
  "佛得角": "🇨🇻",
  "哥伦比亚": "🇨🇴",
  "刚果（金）": "🇨🇩",
  "克罗地亚": "🇭🇷",
  "库拉索": "🇨🇼",
  "捷克": "🇨🇿",
  "丹麦": "🇩🇰",
  "厄瓜多尔": "🇪🇨",
  "埃及": "🇪🇬",
  "英格兰": "🏴",
  "法国": "🇫🇷",
  "德国": "🇩🇪",
  "加纳": "🇬🇭",
  "海地": "🇭🇹",
  "伊朗": "🇮🇷",
  "伊拉克": "🇮🇶",
  "科特迪瓦": "🇨🇮",
  "日本": "🇯🇵",
  "墨西哥": "🇲🇽",
  "摩洛哥": "🇲🇦",
  "荷兰": "🇳🇱",
  "新西兰": "🇳🇿",
  "挪威": "🇳🇴",
  "巴拿马": "🇵🇦",
  "巴拉圭": "🇵🇾",
  "葡萄牙": "🇵🇹",
  "卡塔尔": "🇶🇦",
  "沙特阿拉伯": "🇸🇦",
  "苏格兰": "🏴",
  "塞内加尔": "🇸🇳",
  "南非": "🇿🇦",
  "韩国": "🇰🇷",
  "西班牙": "🇪🇸",
  "瑞典": "🇸🇪",
  "瑞士": "🇨🇭",
  "突尼斯": "🇹🇳",
  "土耳其": "🇹🇷",
  "美国": "🇺🇸",
  "乌拉圭": "🇺🇾",
  "乌兹别克斯坦": "🇺🇿",
};

function teamWithFlag(name) {
  const cleanName = (name || "").toString();
  if (cleanName === "英格兰") return `${esc(cleanName)} <span class="flag flag-svg flag-england" title="英格兰"></span>`;
  if (cleanName === "苏格兰") return `${esc(cleanName)} <span class="flag flag-svg flag-scotland" title="苏格兰"></span>`;
  const flag = TEAM_FLAGS[cleanName];
  if (!flag || cleanName === "待定") return esc(cleanName || "待定");
  return `${esc(cleanName)} <span class="flag" title="${esc(cleanName)}">${flag}</span>`;
}

function renderThird(state) {
  const tbody = document.getElementById("thirdTable");
  const qualified = new Set(state.qualifiedThirdGroups || []);
  const rows = state.thirdPlace || [];

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="empty">暂无小组第三数据：公开源尚未提供可解析的小组积分表，或小组赛尚未开始</td></tr>`;
    return;
  }

  tbody.innerHTML = rows
    .map((r) => {
      const yes = qualified.has(r.group);
      const badge = yes ? `<span class="badge yes">晋级</span>` : `<span class="badge no">未定</span>`;
      return `
        <tr>
          <td>${r.rank ?? ""}</td>
          <td>${esc(r.group)}</td>
          <td class="team">${teamWithFlag(r.team || "")}</td>
          <td>${r.pts ?? ""}</td>
          <td>${r.gd ?? ""}</td>
          <td>${r.gf ?? ""}</td>
          <td>${badge}</td>
        </tr>
      `;
    })
    .join("");
}

function sourceLabel(m, side) {
  const team = side === "home" ? m.home : m.away;
  if (!team) return "待定";
  const thirdTag = team.thirdFrom ? ` · ${team.thirdFrom}组第3` : "";
  return `${team.slot || ""}${thirdTag}`;
}

function bracketTeamLine(slot, name) {
  const teamName = name || "待定";
  return `
    <div class="brTeam">
      <span class="brSlot" title="${esc(slot || "待定")}">${esc(slot || "待定")}</span>
      <span class="brName" title="${esc(teamName)}">${teamWithFlag(teamName)}</span>
    </div>
  `;
}

function fmtSchedule(schedule) {
  if (!schedule?.date) return "赛程待定";
  const d = new Date(schedule.date);
  const dateText = `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const place = [schedule.venue, schedule.city].filter(Boolean).join(" · ");
  return place ? `${dateText}｜${place}` : dateText;
}

function bracketCard(matchNo, lines, muted = false, schedule = null) {
  return `
    <div class="brMatch ${muted ? "muted" : ""}">
      <div class="brNo">M${matchNo}</div>
      ${lines.map((line) => bracketTeamLine(line.slot, line.name)).join("")}
      <div class="brSchedule">${esc(fmtSchedule(schedule))}</div>
    </div>
  `;
}

function r32Card(match) {
  return bracketCard(match.match, [
    { slot: sourceLabel(match, "home"), name: match.home?.team },
    { slot: sourceLabel(match, "away"), name: match.away?.team },
  ], false, match.schedule);
}

function winnerCard(matchNo, a, b) {
  return bracketCard(matchNo, [
    { slot: `胜 M${a}`, name: "待定" },
    { slot: `胜 M${b}`, name: "待定" },
  ], true);
}

function renderColumn(title, matches, cls = "") {
  return `<div class="brCol ${cls}"><div class="brColTitle">${title}</div><div class="brColBody">${matches.join("")}</div></div>`;
}

function renderR32(state) {
  const canvas = document.getElementById("bracketCanvas");
  const r32 = state.r32 || [];
  const map = Object.fromEntries(r32.map((m) => [m.match, m]));
  const safeR32 = (no) => (map[no] ? r32Card(map[no]) : bracketCard(no, [{ slot: "待定", name: "待定" }, { slot: "待定", name: "待定" }], true));

  const columns = [
    renderColumn("32强赛", [73, 75, 74, 77, 83, 84, 81, 82].map(safeR32), "r32 left"),
    renderColumn("16强赛", [winnerCard(90, 73, 74), winnerCard(89, 75, 76), winnerCard(93, 81, 82), winnerCard(94, 83, 84)], "r16 left"),
    renderColumn("1/4决赛", [winnerCard(97, 89, 90), winnerCard(98, 93, 94)], "qf left"),
    renderColumn("半决赛", [winnerCard(101, 97, 98)], "sf left"),
    `<div class="brCol finalCol"><div class="trophy">🏆</div><div class="finalTitle">决赛</div>${winnerCard(104, 101, 102)}</div>`,
    renderColumn("半决赛", [winnerCard(102, 99, 100)], "sf right"),
    renderColumn("1/4决赛", [winnerCard(99, 91, 92), winnerCard(100, 95, 96)], "qf right"),
    renderColumn("16强赛", [winnerCard(91, 76, 78), winnerCard(92, 79, 80), winnerCard(95, 86, 88), winnerCard(96, 85, 87)], "r16 right"),
    renderColumn("32强赛", [76, 78, 79, 80, 86, 88, 85, 87].map(safeR32), "r32 right"),
  ];

  canvas.innerHTML = columns.join("");
  applyZoom();
}

function applyZoom() {
  const canvas = document.getElementById("bracketCanvas");
  if (!canvas) return;
  canvas.style.transform = `scale(${bracketZoom})`;
  canvas.style.width = `${100 / bracketZoom}%`;
  document.getElementById("zoomResetBtn").textContent = `${Math.round(bracketZoom * 100)}%`;
}

function setZoom(next) {
  bracketZoom = Math.min(2.2, Math.max(0.45, next));
  applyZoom();
}

function setupBracketGestures() {
  const viewport = document.getElementById("bracketViewport");
  if (!viewport) return;

  viewport.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const step = ev.deltaY > 0 ? -0.08 : 0.08;
    setZoom(bracketZoom + step);
  }, { passive: false });

  viewport.addEventListener("mousedown", (ev) => {
    isBracketDragging = true;
    dragStartX = ev.clientX;
    dragStartY = ev.clientY;
    dragScrollLeft = viewport.scrollLeft;
    dragScrollTop = viewport.scrollTop;
    viewport.classList.add("dragging");
  });

  window.addEventListener("mousemove", (ev) => {
    if (!isBracketDragging) return;
    ev.preventDefault();
    viewport.scrollLeft = dragScrollLeft - (ev.clientX - dragStartX);
    viewport.scrollTop = dragScrollTop - (ev.clientY - dragStartY);
  });

  window.addEventListener("mouseup", () => {
    isBracketDragging = false;
    viewport.classList.remove("dragging");
  });
}

function renderAll(state) {
  document.getElementById("updatedAt").textContent = `更新：${fmtTime(state.updatedAt)}`;
  renderThird(state);
  renderR32(state);

  if (document.getElementById("autoScroll").checked) {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

async function loadSnapshot() {
  const res = await fetch(`${STATE_URL}?t=${Date.now()}`);
  const data = await res.json();
  renderAll(data);

  const el = document.getElementById("visitStats");
  if (el) {
    el.textContent = "静态版本：已关闭后端接口服务";
  }
}

async function refresh() {
  await loadSnapshot();
}

(async function main() {
  document.getElementById("refreshBtn").addEventListener("click", refresh);
  document.getElementById("zoomOutBtn").addEventListener("click", () => setZoom(bracketZoom - 0.1));
  document.getElementById("zoomInBtn").addEventListener("click", () => setZoom(bracketZoom + 0.1));
  document.getElementById("zoomResetBtn").addEventListener("click", () => setZoom(1));
  setupBracketGestures();

  try {
    await loadSnapshot();
  } catch {
    // ignore
  }
})();
