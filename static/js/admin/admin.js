/* ===== TOAST ===== */
let toastTimer;
function showToast(msg) {
    const t = document.getElementById('toast');
    document.getElementById('toast-msg').textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2400);
}

/* ===== 사이드바 토글 ===== */
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
    document.getElementById('sidebar-overlay').classList.toggle('open');
}
function closeSidebar() {
    document.querySelector('.sidebar').classList.remove('open');
    document.getElementById('sidebar-overlay').classList.remove('open');
}

/* ===== 툴팁 ===== */
const _tip = document.getElementById('v-tooltip');
function showVTooltip(e, loggedIn, anonymous, label) {
    _tip.innerHTML = `
        <div style="margin-bottom:3px;color:rgba(255,255,255,.6);font-size:.68rem;">${label}</div>
        <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:8px;height:8px;border-radius:2px;background:var(--teal);display:inline-block;"></span>
            로그인 <strong style="margin-left:auto;padding-left:12px;">${loggedIn.toLocaleString()}명</strong>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-top:2px;">
            <span style="width:8px;height:8px;border-radius:2px;background:var(--warning);display:inline-block;"></span>
            비로그인 <strong style="margin-left:auto;padding-left:12px;">${anonymous.toLocaleString()}명</strong>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,.15);margin-top:5px;padding-top:4px;display:flex;justify-content:space-between;gap:12px;">
            <span style="color:rgba(255,255,255,.6);">합계</span>
            <strong>${(loggedIn+anonymous).toLocaleString()}명</strong>
        </div>`;
    _tip.classList.add('show');
    const rect = e.currentTarget.getBoundingClientRect();
    const tipW = 160;
    let left = rect.left + rect.width/2 - tipW/2 + window.scrollX;
    let top  = rect.top - _tip.offsetHeight - 10 + window.scrollY;
    if (left < 8) left = 8;
    if (left + tipW > window.innerWidth - 8) left = window.innerWidth - tipW - 8;
    _tip.style.left  = left + 'px';
    _tip.style.top   = top  + 'px';
    _tip.style.width = tipW + 'px';
}
function hideVTooltip() { _tip.classList.remove('show'); }