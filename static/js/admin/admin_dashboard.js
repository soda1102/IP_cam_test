/* 오늘 날짜 */
const today = new Date();
document.getElementById('today-date').textContent =
    today.toLocaleDateString('ko-KR', { year:'numeric', month:'long', day:'numeric' }) + ' 기준 실시간 집계';

/* 방문자 차트 */
async function loadVisitors(range) {
    ['today','week','month'].forEach(r => {
        const btn = document.getElementById('vbtn-' + r);
        const active = r === range;
        btn.style.background  = active ? 'var(--teal)' : '';
        btn.style.color       = active ? '#fff' : '';
        btn.style.borderColor = active ? 'var(--teal)' : '';
    });
    const res  = await fetch('/admin/api/visitors');
    const data = await res.json();
    const summary = document.getElementById('visitor-today-summary');
    const chart   = document.getElementById('visitor-chart');
    const legend  = document.getElementById('visitor-legend');

    if (range === 'today') {
        const d = data.today;
        document.getElementById('v-total').textContent    = d.total.toLocaleString();
        document.getElementById('v-loggedin').textContent = d.logged_in.toLocaleString();
        document.getElementById('v-anon').textContent     = d.anonymous.toLocaleString();
        summary.style.display = 'grid';
        chart.style.display   = 'none';
        legend.style.display  = 'none';
    } else if (range === 'week') {
        summary.style.display = 'none';
        chart.style.display   = 'flex';
        legend.style.display  = 'flex';
        const slots = [];
        for (let i = 6; i >= 0; i--) {
            const d = new Date(); d.setDate(d.getDate() - i);
            const key   = d.toISOString().slice(0, 10);
            const label = (d.getMonth()+1) + '/' + d.getDate();
            slots.push({ key, label, logged_in:0, anonymous:0, total:0 });
        }
        (data.week||[]).forEach(r => {
            const slot = slots.find(s => s.key === r.date);
            if (slot) { slot.logged_in = r.logged_in; slot.anonymous = r.anonymous; slot.total = r.total; }
        });
        chart.dataset.range = 'week';
        renderBarChart(chart, slots);
    } else {
        summary.style.display = 'none';
        chart.style.display   = 'flex';
        legend.style.display  = 'flex';
        const now = new Date();
        const slots = [];
        for (let i = 11; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth()-i, 1);
            const key   = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0');
            const label = (d.getMonth()+1) + '월';
            slots.push({ key, label, logged_in:0, anonymous:0, total:0 });
        }
        (data.month||[]).forEach(r => {
            const monthKey = r.date.slice(0, 7);
            const slot = slots.find(s => s.key === monthKey);
            if (slot) { slot.logged_in += r.logged_in; slot.anonymous += r.anonymous; slot.total += r.total; }
        });
        const firstDataIdx = slots.findIndex(s => s.total > 0);
        const trimmed = firstDataIdx >= 0 ? slots.slice(firstDataIdx) : slots.slice(-1);
        chart.dataset.range = 'month';
        renderBarChart(chart, trimmed);
    }
}

function renderBarChart(container, slots) {
    const max = Math.max(...slots.map(s => s.total), 1);
    if (slots.every(s => s.total === 0)) {
        container.innerHTML = '<div style="color:var(--text-muted);font-size:.85rem;font-weight:600;align-self:center;width:100%;text-align:center;">데이터가 없습니다.</div>';
        return;
    }
    const flexStyle = container.dataset.range === 'week'
        ? 'flex:1;min-width:0;' : 'flex:0 0 44px;width:44px;';
    container.innerHTML = slots.map((s, i) => {
        const hLogin = Math.max(Math.round((s.logged_in / max) * 110), s.logged_in > 0 ? 2 : 0);
        const hAnon  = Math.max(Math.round((s.anonymous / max) * 110), s.anonymous > 0 ? 2 : 0);
        return `
        <div style="${flexStyle}display:flex;flex-direction:column;align-items:center;gap:4px;position:relative;"
             onmouseenter="showVTooltip(event,${s.logged_in},${s.anonymous},'${s.label}')"
             onmouseleave="hideVTooltip()">
            <div style="width:100%;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:110px;gap:1px;">
                <div style="width:100%;height:${hAnon}px;background:var(--warning);border-radius:3px 3px 0 0;opacity:.75;"></div>
                <div style="width:100%;height:${hLogin}px;background:var(--teal);border-radius:3px 3px 0 0;opacity:.85;"></div>
            </div>
            <span style="font-size:.62rem;color:var(--text-muted);font-weight:600;white-space:nowrap;">${s.label}</span>
        </div>`;
    }).join('');
}

loadVisitors('today');