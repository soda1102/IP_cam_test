/* ===== AI 동물 탐지 통계 ===== */
async function loadAiStats() {
    const res  = await fetch('/admin/api/ai_stats');
    const data = await res.json();

    /* 누적 프로그레스바 */
    const t = data.totals;
    const maxVal = Math.max(t.boar, t.deer, t.racoon, 1);

    document.getElementById('total-boar').textContent   = t.boar.toLocaleString() + '건';
    document.getElementById('total-deer').textContent   = t.deer.toLocaleString() + '건';
    document.getElementById('total-racoon').textContent = t.racoon.toLocaleString() + '건';

    // 애니메이션을 위해 약간 딜레이
    setTimeout(() => {
        document.getElementById('bar-boar').style.width   = (t.boar   / maxVal * 100) + '%';
        document.getElementById('bar-deer').style.width   = (t.deer   / maxVal * 100) + '%';
        document.getElementById('bar-racoon').style.width = (t.racoon / maxVal * 100) + '%';
    }, 100);

    /* 라인차트 */
    drawLineChart(data.trend);
}

function drawLineChart(trend) {
    const canvas = document.getElementById('animal-line-chart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // 캔버스 크기 설정
    const W = canvas.offsetWidth;
    const H = 160;
    canvas.width  = W;
    canvas.height = H;

    if (!trend || trend.length === 0) {
        ctx.fillStyle = '#aaa';
        ctx.font = '13px Pretendard, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('데이터가 없습니다.', W / 2, H / 2);
        return;
    }

    const PAD = { top: 12, right: 16, bottom: 32, left: 36 };
    const chartW = W - PAD.left - PAD.right;
    const chartH = H - PAD.top - PAD.bottom;

    const maxY = Math.max(
        ...trend.map(d => Math.max(d.boar, d.deer, d.racoon)), 1
    );

    const xStep = chartW / Math.max(trend.length - 1, 1);

    const getX = i  => PAD.left + i * xStep;
    const getY = v  => PAD.top + chartH - (v / maxY) * chartH;

    // 스타일
    const colors = {
        boar:   getComputedStyle(document.documentElement).getPropertyValue('--danger').trim()  || '#e74c3c',
        deer:   getComputedStyle(document.documentElement).getPropertyValue('--warning').trim() || '#f39c12',
        racoon: getComputedStyle(document.documentElement).getPropertyValue('--teal').trim()    || '#20828A',
    };

    // 그리드 라인
    ctx.strokeStyle = 'rgba(0,0,0,0.06)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = PAD.top + (chartH / 4) * i;
        ctx.beginPath();
        ctx.moveTo(PAD.left, y);
        ctx.lineTo(PAD.left + chartW, y);
        ctx.stroke();
        // y축 라벨
        ctx.fillStyle = '#aaa';
        ctx.font = '10px Pretendard, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(Math.round(maxY - (maxY / 4) * i) + '건', PAD.left - 4, y + 4);
    }

    // 각 동물 라인 그리기
    ['boar', 'deer', 'racoon'].forEach(key => {
        ctx.beginPath();
        ctx.strokeStyle = colors[key];
        ctx.lineWidth   = 2.5;
        ctx.lineJoin    = 'round';
        ctx.lineCap     = 'round';

        trend.forEach((d, i) => {
            const x = getX(i);
            const y = getY(d[key]);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();

        // 데이터 포인트 점
        trend.forEach((d, i) => {
            ctx.beginPath();
            ctx.arc(getX(i), getY(d[key]), 3, 0, Math.PI * 2);
            ctx.fillStyle = colors[key];
            ctx.fill();
        });
    });

    // x축 날짜 라벨
    ctx.fillStyle = '#aaa';
    ctx.font = '9px Pretendard, sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(trend.length / 7));
    trend.forEach((d, i) => {
        if (i % step === 0 || i === trend.length - 1) {
            const label = d.date.slice(5); // MM-DD
            ctx.fillText(label, getX(i), H - 8);
        }
    });
}

/* 초기 실행 */
loadAiStats();

/* 창 크기 바뀌면 차트 다시 그림 */
window.addEventListener('resize', loadAiStats);