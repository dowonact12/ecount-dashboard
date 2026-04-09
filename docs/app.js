let DATA = { items: [], updated_at: null };
let sortKey = "prod_cd";
let sortAsc = true;

async function load() {
  try {
    const res = await fetch(`inventory.json?t=${Date.now()}`);
    DATA = await res.json();
    document.getElementById("updated").textContent =
      "업데이트: " + new Date(DATA.updated_at).toLocaleString("ko-KR");
    buildFilters();
    render();
  } catch (e) {
    document.getElementById("tbody").innerHTML =
      `<tr><td colspan="8" class="empty">데이터를 불러올 수 없습니다. (${e.message})<br>
       PC에서 fetch_inventory.py 를 먼저 실행해주세요.</td></tr>`;
  }
}

function buildFilters() {
  const whs = [...new Set(DATA.items.map(i => i.wh_des).filter(Boolean))].sort();
  const cls = [...new Set(DATA.items.map(i => i.class_name).filter(Boolean))].sort();
  const whSel = document.getElementById("wh-filter");
  const clSel = document.getElementById("class-filter");
  whSel.innerHTML = '<option value="">전체 창고</option>' + whs.map(w => `<option>${w}</option>`).join("");
  clSel.innerHTML = '<option value="">전체 분류</option>' + cls.map(c => `<option>${c}</option>`).join("");
}

function getFiltered() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const wh = document.getElementById("wh-filter").value;
  const cl = document.getElementById("class-filter").value;
  const lowOnly = document.getElementById("low-only").checked;

  let rows = DATA.items.filter(i => {
    if (wh && i.wh_des !== wh) return false;
    if (cl && i.class_name !== cl) return false;
    if (lowOnly && !(i.qty < i.safe_qty && i.safe_qty > 0)) return false;
    if (q) {
      const hay = `${i.prod_cd} ${i.prod_des} ${i.class_name}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  rows.sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (typeof av === "number" && typeof bv === "number") return sortAsc ? av - bv : bv - av;
    return sortAsc ? String(av).localeCompare(String(bv), "ko") : String(bv).localeCompare(String(av), "ko");
  });
  return rows;
}

function render() {
  const rows = getFiltered();
  const tb = document.getElementById("tbody");

  // 통계 (전체 기준)
  const items = DATA.items;
  document.getElementById("stat-items").textContent = new Set(items.map(i => i.prod_cd)).size.toLocaleString();
  document.getElementById("stat-qty").textContent = items.reduce((s, i) => s + i.qty, 0).toLocaleString();
  document.getElementById("stat-low").textContent = items.filter(i => i.qty < i.safe_qty && i.safe_qty > 0).length.toLocaleString();
  document.getElementById("stat-wh").textContent = new Set(items.map(i => i.wh_des).filter(Boolean)).size.toLocaleString();
  document.getElementById("count").textContent = rows.length.toLocaleString();

  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="8" class="empty">표시할 데이터가 없습니다.</td></tr>`;
    return;
  }

  tb.innerHTML = rows.map(i => {
    let badge = `<span class="badge ok">정상</span>`;
    if (i.qty <= 0) badge = `<span class="badge zero">품절</span>`;
    else if (i.safe_qty > 0 && i.qty < i.safe_qty) badge = `<span class="badge low">미달</span>`;
    return `<tr>
      <td>${esc(i.prod_cd)}</td>
      <td>${esc(i.prod_des)}</td>
      <td>${esc(i.class_name)}</td>
      <td>${esc(i.wh_des)}</td>
      <td class="num">${i.qty.toLocaleString()}</td>
      <td class="num">${i.safe_qty ? i.safe_qty.toLocaleString() : "-"}</td>
      <td>${esc(i.unit)}</td>
      <td>${badge}</td>
    </tr>`;
  }).join("");
}

function esc(s) { return String(s || "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }

document.getElementById("search").addEventListener("input", render);
document.getElementById("wh-filter").addEventListener("change", render);
document.getElementById("class-filter").addEventListener("change", render);
document.getElementById("low-only").addEventListener("change", render);
document.getElementById("refresh").addEventListener("click", load);
document.querySelectorAll("th[data-sort]").forEach(th => {
  th.addEventListener("click", () => {
    const k = th.dataset.sort;
    if (sortKey === k) sortAsc = !sortAsc;
    else { sortKey = k; sortAsc = true; }
    render();
  });
});

load();
setInterval(load, 60000); // 1분마다 자동 재조회
