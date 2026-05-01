const SESSION_LOG = [];
let idImageBase64 = null;
let liveImageBase64 = null;
let activeStream = null;

let sessionMinAge = null;
let lastResultScreen = 'screen-verified';

let auroraCanvas, auroraCtx, auroraTime = 0, auroraFrame = null;

// ── AUDIO ──────────────────────────────────────────────────────
let audioCtx = null;
let analyzeInterval = null;
let isAnalyzingSound = false;

function getAC() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
}

function playClickSound() {
    const ac = getAC();
    const osc = ac.createOscillator();
    const g = ac.createGain();
    osc.connect(g); g.connect(ac.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(600, ac.currentTime);
    osc.frequency.exponentialRampToValueAtTime(300, ac.currentTime + 0.08);
    g.gain.setValueAtTime(0.15, ac.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.08);
    osc.start(); osc.stop(ac.currentTime + 0.1);
}

function playDeniedSound() {
    const ac = getAC();
    [[440, 0], [330, 0.13], [220, 0.26]].forEach(([freq, offset]) => {
        const osc = ac.createOscillator();
        const g = ac.createGain();
        osc.connect(g); g.connect(ac.destination);
        osc.type = 'sine'; osc.frequency.value = freq;
        const t = ac.currentTime + offset;
        g.gain.setValueAtTime(0, t);
        g.gain.linearRampToValueAtTime(0.22, t + 0.01);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
        osc.start(t); osc.stop(t + 0.15);
    });
}

function playApprovedSound() {
    const ac = getAC();
    [523, 659, 784, 1047].forEach((freq, i) => {
        const osc = ac.createOscillator();
        const g = ac.createGain();
        osc.connect(g); g.connect(ac.destination);
        osc.type = 'sine'; osc.frequency.value = freq;
        const t = ac.currentTime + i * 0.11;
        g.gain.setValueAtTime(0, t);
        g.gain.linearRampToValueAtTime(0.2, t + 0.02);
        g.gain.exponentialRampToValueAtTime(0.001, t + 0.28);
        osc.start(t); osc.stop(t + 0.3);
    });
}

function startAnalyzingSound() {
    if (isAnalyzingSound) return;
    const ac = getAC();
    isAnalyzingSound = true;
    const freqs = [400, 500, 630, 800, 1000, 1260];
    let i = 0;
    function fire() {
        if (!isAnalyzingSound) return;
        const osc = ac.createOscillator();
        const g = ac.createGain();
        osc.connect(g); g.connect(ac.destination);
        osc.type = 'sine'; osc.frequency.value = freqs[i % freqs.length];
        g.gain.setValueAtTime(0.12, ac.currentTime);
        g.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.09);
        osc.start(); osc.stop(ac.currentTime + 0.12);
        i++;
        if (i >= freqs.length) { i = 0; analyzeInterval = setTimeout(fire, 800); }
        else analyzeInterval = setTimeout(fire, 110);
    }
    fire();
}

function stopAnalyzingSound() {
    isAnalyzingSound = false;
    clearTimeout(analyzeInterval);
}
// ──────────────────────────────────────────────────────────────

function initAurora() {
    auroraCanvas = document.getElementById('aurora-canvas');
    if (!auroraCanvas) return;
    auroraCtx = auroraCanvas.getContext('2d');
    resizeAurora();
    window.addEventListener('resize', resizeAurora);
    tickAurora();
}

function resizeAurora() {
    if (!auroraCanvas) return;
    auroraCanvas.width = window.innerWidth;
    auroraCanvas.height = window.innerHeight;
}

function drawAuroraBg() {
    const W = auroraCanvas.width, H = auroraCanvas.height;
    const t = auroraTime;
    auroraCtx.clearRect(0, 0, W, H);

    const base = auroraCtx.createLinearGradient(0, 0, 0, H);
    base.addColorStop(0, '#02020c');
    base.addColorStop(1, '#05050f');
    auroraCtx.fillStyle = base;
    auroraCtx.fillRect(0, 0, W, H);

    const orbs = [
        { cx: 0.15 + Math.sin(t * 0.6) * 0.1,  cy: 0.18 + Math.cos(t * 0.4) * 0.08, r: 0.38, c1: 'rgba(109,40,217,0.18)',  c2: 'rgba(109,40,217,0)' },
        { cx: 0.82 + Math.sin(t * 0.5) * 0.08,  cy: 0.22 + Math.cos(t * 0.7) * 0.07, r: 0.32, c1: 'rgba(219,39,119,0.13)',  c2: 'rgba(219,39,119,0)' },
        { cx: 0.5  + Math.sin(t * 0.3) * 0.15,  cy: 0.65 + Math.cos(t * 0.5) * 0.1,  r: 0.45, c1: 'rgba(37,99,235,0.10)',   c2: 'rgba(37,99,235,0)' },
        { cx: 0.7  + Math.sin(t * 0.8) * 0.07,  cy: 0.5  + Math.cos(t * 0.6) * 0.12, r: 0.28, c1: 'rgba(167,139,250,0.09)', c2: 'rgba(167,139,250,0)' },
    ];
    orbs.forEach(o => {
        const gx = o.cx * W, gy = o.cy * H, gr = o.r * Math.max(W, H);
        const g = auroraCtx.createRadialGradient(gx, gy, 0, gx, gy, gr);
        g.addColorStop(0, o.c1);
        g.addColorStop(1, o.c2);
        auroraCtx.fillStyle = g;
        auroraCtx.fillRect(0, 0, W, H);
    });

    if (!auroraCanvas._stars) {
        auroraCanvas._stars = Array.from({ length: 80 }, () => ({
            x: Math.random(), y: Math.random(),
            r: Math.random() * 0.9 + 0.2,
            phase: Math.random() * Math.PI * 2
        }));
    }
    auroraCanvas._stars.forEach(s => {
        const alpha = (Math.sin(t * 1.2 + s.phase) + 1) / 2 * 0.5 + 0.1;
        auroraCtx.beginPath();
        auroraCtx.arc(s.x * W, s.y * H, s.r, 0, Math.PI * 2);
        auroraCtx.fillStyle = `rgba(200,190,255,${alpha})`;
        auroraCtx.fill();
    });
}

function tickAurora() {
    auroraTime += 0.005;
    drawAuroraBg();
    auroraFrame = requestAnimationFrame(tickAurora);
}

function stopAurora() {
    if (auroraFrame) { cancelAnimationFrame(auroraFrame); auroraFrame = null; }
}

function startAurora() {
    if (!auroraCanvas) initAurora();
    if (!auroraFrame) tickAurora();
}

function goTo(screenId) {
    const current = document.querySelector('.screen.active');
    const next = document.getElementById(screenId);
    const isResult = screenId === 'screen-verified' || screenId === 'screen-suspicious';

    if (current && current !== next) {
        if (isResult) {
            current.classList.add('screen-explode-out');
            setTimeout(() => {
                current.classList.remove('active', 'screen-explode-out');
                next.classList.add('active', 'screen-slam-in');
                setTimeout(() => next.classList.remove('screen-slam-in'), 800);
            }, 500);
        } else {
            current.classList.add('screen-transition-out');
            setTimeout(() => {
                current.classList.remove('active', 'screen-transition-out');
                next.classList.add('active', 'screen-transition-in');
                setTimeout(() => next.classList.remove('screen-transition-in'), 350);
            }, 280);
        }
    } else {
        next.classList.add('active');
    }
    if (screenId === 'screen-home') startAurora();
    else stopAurora();
}

function startVerification() {
    if (sessionMinAge !== null) {
        goTo('screen-scan-id');
        return;
    }
    const minAgeInput = document.getElementById('min-age-input').value;
    const minAge = parseInt(minAgeInput);
    if (!minAgeInput || isNaN(minAge) || minAge < 1 || minAge > 120) {
        const el = document.getElementById('min-age-input');
        el.style.border = '1px solid #f87171';
        el.placeholder = 'enter age 1-120';
        setTimeout(() => { el.style.border = ''; el.placeholder = '18'; }, 2000);
        return;
    }
    sessionMinAge = minAge;
    stopAurora();
    goTo('screen-scan-id');
}

function resetApp() {
    idImageBase64 = null;
    liveImageBase64 = null;
    stopCamera();
    resetCameraUI('id');
    resetCameraUI('live');
    document.getElementById('age-input').value = '';
    ['face', 'age', 'doc', 'agestatus'].forEach(name => {
        ['ok', 'warn'].forEach(type => {
            const card = document.getElementById(`lcard-${name}-${type}`);
            if (card) card.classList.remove('visible');
        });
    });
    goTo('screen-scan-id');
}

function restartSession() {
    SESSION_LOG.length = 0;
    sessionMinAge = null;
    idImageBase64 = null;
    liveImageBase64 = null;
    stopCamera();
    resetCameraUI('id');
    resetCameraUI('live');
    document.getElementById('age-input').value = '';
    document.getElementById('min-age-input').value = '';
    ['face', 'age', 'doc', 'agestatus'].forEach(name => {
        ['ok', 'warn'].forEach(type => {
            const card = document.getElementById(`lcard-${name}-${type}`);
            if (card) card.classList.remove('visible');
        });
    });
    renderLog();
    goTo('screen-home');
}

function resetCameraUI(target) {
    const videoEl        = document.getElementById(`video-${target}`);
    const placeholder    = document.getElementById(`cam-placeholder-${target}`);
    const btnEl          = document.getElementById(`btn-capture-${target}`);
    const previewEl      = document.getElementById(`preview-${target}`);
    const retakeRow      = document.getElementById(`retake-row-${target}`);
    const videoPreviewEl = document.getElementById(`video-preview-${target}`);

    videoEl.classList.remove('active');
    placeholder.style.display = 'flex';
    btnEl.textContent = 'open camera';
    btnEl.style.display = 'block';
    btnEl.onclick = () => startCamera(target);

    if (previewEl) previewEl.style.display = 'none';
    if (retakeRow) retakeRow.style.display = 'none';
    if (videoPreviewEl) { videoPreviewEl.innerHTML = ''; videoPreviewEl.style.display = 'none'; }
}

function stopCamera() {
    if (activeStream) { activeStream.getTracks().forEach(t => t.stop()); activeStream = null; }
}

async function startCamera(target) {
    stopCamera();
    const videoEl     = document.getElementById(`video-${target}`);
    const placeholder = document.getElementById(`cam-placeholder-${target}`);
    const btnEl       = document.getElementById(`btn-capture-${target}`);
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }
        });
        activeStream = stream;
        videoEl.srcObject = stream;
        videoEl.classList.add('active');
        placeholder.style.display = 'none';
        btnEl.textContent = 'capture photo';
        btnEl.onclick = () => capturePhoto(target);
    } catch (err) {
        displayError('camera access denied — please allow camera permission and refresh');
    }
}

function capturePhoto(target) {
    const videoEl  = document.getElementById(`video-${target}`);
    const canvasEl = document.getElementById(`canvas-${target}`);
    const scale = 2;
    canvasEl.width  = videoEl.videoWidth  * scale;
    canvasEl.height = videoEl.videoHeight * scale;
    const ctx = canvasEl.getContext('2d');
    ctx.scale(scale, scale);
    ctx.drawImage(videoEl, 0, 0);
    const base64 = canvasEl.toDataURL('image/jpeg', 0.95).split(',')[1];
    stopCamera();

    videoEl.classList.remove('active');
    document.getElementById(`cam-placeholder-${target}`).style.display = 'none';

    const previewEl = document.getElementById(`preview-${target}`);
    previewEl.src = `data:image/jpeg;base64,${base64}`;
    previewEl.style.display = 'block';

    const retakeRow = document.getElementById(`retake-row-${target}`);
    retakeRow.style.display = 'flex';

    const btnEl = document.getElementById(`btn-capture-${target}`);
    btnEl.style.display = 'none';

    document.getElementById(`btn-use-${target}`).onclick = () => {
        if (target === 'id') {
            idImageBase64 = base64;
            previewEl.style.display = 'none';
            retakeRow.style.display = 'none';
            btnEl.style.display = 'block';
            goTo('screen-live');
        } else {
            liveImageBase64 = base64;
            submitVerification();
        }
    };

    document.getElementById(`btn-retake-${target}`).onclick = () => {
        previewEl.style.display = 'none';
        retakeRow.style.display = 'none';
        btnEl.style.display = 'block';
        btnEl.textContent = 'open camera';
        btnEl.onclick = () => startCamera(target);
        document.getElementById(`cam-placeholder-${target}`).style.display = 'flex';
    };
}

function useGallery(target) { document.getElementById(`gallery-${target}`).click(); }

function handleGallery(event, target) {
    const file = event.target.files[0];
    if (!file) return;
    const isVideo        = file.type.startsWith('video/');
    const placeholder    = document.getElementById(`cam-placeholder-${target}`);
    const previewEl      = document.getElementById(`preview-${target}`);
    const videoPreviewEl = document.getElementById(`video-preview-${target}`);
    const retakeRow      = document.getElementById(`retake-row-${target}`);
    const btnEl          = document.getElementById(`btn-capture-${target}`);
    const url = URL.createObjectURL(file);
    placeholder.style.display = 'none';

    if (isVideo) {
        videoPreviewEl.innerHTML = '';
        const v = document.createElement('video');
        v.src = url; v.autoplay = true; v.muted = true; v.loop = true; v.playsInline = true;
        v.setAttribute('playsinline', ''); v.setAttribute('webkit-playsinline', '');
        v.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
        videoPreviewEl.style.cssText = 'display:block;width:100%;height:100%;position:absolute;top:0;left:0;';
        videoPreviewEl.appendChild(v); v.load(); v.play().catch(() => {});
        previewEl.style.display = 'none'; retakeRow.style.display = 'flex'; btnEl.style.display = 'none';
        v.addEventListener('loadeddata', () => {
            const tmp = document.createElement('canvas');
            tmp.width = v.videoWidth || 640; tmp.height = v.videoHeight || 480;
            tmp.getContext('2d').drawImage(v, 0, 0, tmp.width, tmp.height);
            const base64 = tmp.toDataURL('image/jpeg', 0.95).split(',')[1];
            document.getElementById(`btn-use-${target}`).onclick = () => {
                if (target === 'id') {
                    idImageBase64 = base64;
                    videoPreviewEl.innerHTML = ''; videoPreviewEl.style.display = 'none';
                    retakeRow.style.display = 'none'; btnEl.style.display = 'block';
                    goTo('screen-live');
                } else { liveImageBase64 = base64; submitVerification(); }
            };
        }, { once: true });
    } else {
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(',')[1];
            previewEl.src = e.target.result; previewEl.style.display = 'block';
            retakeRow.style.display = 'flex'; btnEl.style.display = 'none';
            document.getElementById(`btn-use-${target}`).onclick = () => {
                if (target === 'id') {
                    idImageBase64 = base64;
                    previewEl.style.display = 'none'; retakeRow.style.display = 'none';
                    btnEl.style.display = 'block'; goTo('screen-live');
                } else { liveImageBase64 = base64; submitVerification(); }
            };
        };
        reader.readAsDataURL(file);
    }

    document.getElementById(`btn-retake-${target}`).onclick = () => {
        previewEl.style.display = 'none';
        if (videoPreviewEl) { videoPreviewEl.innerHTML = ''; videoPreviewEl.style.display = 'none'; }
        retakeRow.style.display = 'none'; btnEl.style.display = 'block';
        btnEl.textContent = 'open camera'; btnEl.onclick = () => startCamera(target);
        placeholder.style.display = 'flex'; event.target.value = '';
    };
}

async function submitVerification() {
    const ageInput = document.getElementById('age-input').value || '0';
    goTo('screen-processing');
    animateProcessing();
    startAnalyzingSound();
    try {
        const minAge = sessionMinAge || 18;
        const [faceRes, ageRes, docRes] = await Promise.all([
            fetch('/api/verify-face',    { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ id_image: idImageBase64, live_image: liveImageBase64 }) }).then(r => r.json()),
            fetch('/api/estimate-age',   { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ live_image: liveImageBase64, age_on_id: parseInt(ageInput) }) }).then(r => r.json()),
            fetch('/api/check-document', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ id_image: idImageBase64, min_age: minAge }) }).then(r => r.json()),
        ]);
        stopAnalyzingSound();
        showResult(faceRes, ageRes, docRes, parseInt(ageInput));
    } catch (err) {
        stopAnalyzingSound();
        displayError('unexpected server error');
        console.error('fetch failed:', err);
    }
}

function animateProcessing() {
    const rows     = ['proc-row-1','proc-row-2','proc-row-3','proc-row-4','proc-row-5'];
    const statuses = ['proc-1','proc-2','proc-3','proc-4','proc-5'];
    const dots     = ['proc-dot-1','proc-dot-2','proc-dot-3','proc-dot-4','proc-dot-5'];
    const progress = document.getElementById('top-progress');
    rows.forEach(id => document.getElementById(id).classList.remove('active'));
    statuses.forEach(id => { document.getElementById(id).textContent = 'waiting'; document.getElementById(id).className = 'proc-status'; });
    dots.forEach(id => { document.getElementById(id).className = 'proc-dot'; });
    if (progress) progress.style.width = '0%';
    rows.forEach((rowId, i) => {
        setTimeout(() => {
            document.getElementById(rowId).classList.add('active');
            document.getElementById(statuses[i]).textContent = 'running';
            document.getElementById(statuses[i]).className = 'proc-status running';
            document.getElementById(dots[i]).className = 'proc-dot running';
            if (progress) progress.style.width = `${((i + 1) / rows.length) * 100}%`;
        }, i * 700);
        setTimeout(() => {
            document.getElementById(statuses[i]).textContent = 'done';
            document.getElementById(statuses[i]).className = 'proc-status done';
            document.getElementById(dots[i]).className = 'proc-dot done';
        }, i * 700 + 500);
    });
}

function flashScreen(color) {
    const overlay = document.getElementById('flash-overlay');
    overlay.style.background = color;
    overlay.style.opacity = '0.4';
    setTimeout(() => { overlay.style.opacity = '0'; }, 400);
}

function getDocInfo(docResult) {
    if (!docResult.success) return { label: 'unknown', displayText: 'unknown', colorClass: '', mrzUnderaged: false };
    const mrzDetail = docResult.data.layers.classifier.mrz_detail || null;
    const verdict = mrzDetail ? mrzDetail.verdict : null;
    if (verdict === 'FAKE') return { label: 'fake', displayText: 'fake', colorClass: 'warn', mrzUnderaged: false, ageUnknown: true };
    if (verdict === 'UNDERAGE') return { label: 'real', displayText: 'real', colorClass: 'ok', mrzUnderaged: true };
    if (verdict === 'REAL') return { label: 'real', displayText: 'real', colorClass: 'ok', mrzUnderaged: false };
    return { label: 'unknown', displayText: 'unknown', colorClass: '', mrzUnderaged: false };
}

function showResult(faceResult, ageResult, docResult, ageOnId) {
    const faceVerdict      = faceResult.success ? faceResult.data.layers.similarity.label : 'not matching';
    const rawScore         = faceResult.success ? faceResult.data.layers.similarity.score : 0;
    const faceScorePercent = Math.min(Math.round(rawScore * 100), 100);
    const docInfo          = getDocInfo(docResult);

    const estimatedAge = ageResult.success ? ageResult.data.layers.age_model.estimated_age : null;
    const looksYoungerThanMrz = false;

    const overallVerified = faceVerdict === 'verified' && docInfo.label !== 'fake' && !docInfo.mrzUnderaged;

    SESSION_LOG.unshift({
        verdict: overallVerified ? 'verified' : 'denied',
        score: faceScorePercent,
        time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    });

    const suffix   = overallVerified ? 'ok' : 'warn';
    const minAgeEl = document.getElementById(`display-min-age-${suffix}`);
    if (minAgeEl) {
        if (!overallVerified) {
            const reasons = [];
            if (faceVerdict !== 'verified') reasons.push('face mismatch');
            if (docInfo.label === 'fake') reasons.push('fake document');
            if (docInfo.mrzUnderaged) reasons.push('underaged');
            minAgeEl.textContent = reasons.length > 0 ? reasons.join(' · ') : 'manual check';
        } else {
            minAgeEl.textContent = `min age ${sessionMinAge || 18}`;
        }
    }

    if (overallVerified) { flashScreen('#4ade80'); playApprovedSound(); lastResultScreen = 'screen-verified'; }
    else                 { flashScreen('#f87171'); playDeniedSound();   lastResultScreen = 'screen-suspicious'; }

    setTimeout(() => {
        goTo(overallVerified ? 'screen-verified' : 'screen-suspicious');

        const faceValEl = document.getElementById(`layer-face-${suffix}`);
        faceValEl.textContent = faceVerdict === 'verified' ? 'verified' : 'not matching';
        faceValEl.className   = `layer-card-val ${faceVerdict === 'verified' ? 'ok' : 'warn'}`;
        document.getElementById(`layer-face-score-${suffix}`).textContent = `${faceScorePercent}%`;

        const docValEl = document.getElementById(`layer-doc-${suffix}`);
        docValEl.textContent = docInfo.displayText;
        docValEl.className   = `layer-card-val ${docInfo.colorClass}`;
        document.getElementById(`layer-doc-score-${suffix}`).textContent = '';

        const ageStatusEl = document.getElementById(`layer-agestatus-${suffix}`);
        const ageStatusScoreEl = document.getElementById(`layer-agestatus-score-${suffix}`);
        if (ageStatusEl) {
            if (docInfo.ageUnknown) {
                ageStatusEl.textContent = '—';
                ageStatusEl.className   = `layer-card-val`;
            } else {
                ageStatusEl.textContent = docInfo.mrzUnderaged ? 'underaged' : 'of age';
                ageStatusEl.className   = `layer-card-val ${docInfo.mrzUnderaged ? 'warn' : 'ok'}`;
            }
        }
        if (ageStatusScoreEl) ageStatusScoreEl.textContent = `min ${sessionMinAge || 18}`;

        const ageCard = document.getElementById(`lcard-age-${suffix}`);
        if (ageCard) {
            if (estimatedAge === null) {
                ageCard.style.display = 'none';
            } else {
                ageCard.style.display = 'block';
                const ageValEl = document.getElementById(`layer-age-${suffix}`);
                ageValEl.textContent = looksYoungerThanMrz
                    ? `looks younger · about ${Math.round(estimatedAge)}`
                    : `about ${Math.round(estimatedAge)} years old`;
                ageValEl.className = `layer-card-val ${looksYoungerThanMrz ? 'flag' : 'ok'}`;
                document.getElementById(`layer-age-score-${suffix}`).textContent = looksYoungerThanMrz ? 'flag for mgr' : '';
            }
        }

        setTimeout(() => {
            document.getElementById(`lcard-face-${suffix}`).classList.add('visible');
            setTimeout(() => {
                const faceBarEl = document.getElementById(`layer-face-bar-${suffix}`);
                faceBarEl.className = `layer-card-bar-fill ${faceVerdict === 'verified' ? 'ok' : 'warn'}`;
                faceBarEl.style.width = `${faceScorePercent}%`;
            }, 150);
        }, 300);
        setTimeout(() => { document.getElementById(`lcard-doc-${suffix}`).classList.add('visible'); }, 500);
        setTimeout(() => {
            const ageCard = document.getElementById(`lcard-age-${suffix}`);
            if (ageCard && ageCard.style.display !== 'none') ageCard.classList.add('visible');
        }, 700);
        setTimeout(() => {
            document.getElementById(`lcard-agestatus-${suffix}`).classList.add('visible');
            if (overallVerified) launchConfetti();
        }, 900);
    }, 250);

    renderLog();
}

function launchConfetti() {
    const container = document.getElementById('confetti-container');
    container.innerHTML = '';
    const colors = ['#a78bfa','#4ade80','#f472b6','#fb923c','#facc15','#60a5fa','#34d399'];
    for (let i = 0; i < 100; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left   = `${Math.random() * 100}%`;
        piece.style.top    = `-20px`;
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay    = `${Math.random() * 1.2}s`;
        piece.style.animationDuration = `${1.8 + Math.random() * 1.5}s`;
        piece.style.width  = `${4 + Math.random() * 9}px`;
        piece.style.height = `${4 + Math.random() * 9}px`;
        piece.style.transform = `rotate(${Math.random() * 360}deg)`;
        container.appendChild(piece);
    }
    setTimeout(() => { container.innerHTML = ''; }, 5000);
}

function renderLog() {
    const list = document.getElementById('log-list');
    list.innerHTML = '';
    SESSION_LOG.forEach(entry => {
        const row = document.createElement('div');
        row.className = 'log-entry';
        const isOk = entry.verdict === 'verified';
        const scoreText = entry.score !== null && entry.score !== undefined ? `${entry.score}%` : '—';
        row.innerHTML = `
            <div class="log-photo-wrap">
                ${entry.photo ? `<img src="${entry.photo}" class="log-photo" />` : `<div class="log-photo-placeholder"></div>`}
                <div class="log-status-dot ${isOk ? 'ok' : 'warn'}"></div>
            </div>
            <div class="log-verdict">${entry.verdict}</div>
            <div class="${isOk ? 'log-score-ok' : 'log-score-warn'}">${scoreText}</div>
            <div class="log-time">${entry.time}</div>
        `;
        list.appendChild(row);
    });
}

function displayError(message) {
    const MAP = {
        'No face detected in ID photo':            'could not find a face on the ID — please retake',
        'No face detected in live photo':           'could not detect your face — please look at the camera',
        'Document perspective correction failed':   'ID image is too angled — please retake',
        'No document zones detected':               'could not read the ID document — please retake',
        'Model inference failed':                   'system error — please try again',
        'Invalid image format':                     'image format not supported — please retake',
        'missing required field: age_on_id':        'please enter the age shown on the ID',
        'Model not loaded — weights file missing':  'system not ready — contact support',
        'Unexpected server error':                  'something went wrong — please try again',
        'camera access denied — please allow camera permission and refresh': 'camera access denied — allow permission and refresh',
        'unexpected server error':                  'something went wrong — please try again',
    };
    const msg = MAP[message] || 'something went wrong — please try again';
    const existing = document.getElementById('error-overlay');
    if (existing) existing.remove();
    const overlay = document.createElement('div');
    overlay.id = 'error-overlay';
    overlay.style.cssText = `
        position:fixed;top:0;left:0;width:100%;height:100%;
        background:rgba(5,5,8,0.93);z-index:9999;
        display:flex;flex-direction:column;align-items:center;justify-content:center;
        padding:32px;gap:20px;
    `;
    overlay.innerHTML = `
        <div style="width:64px;height:64px;border-radius:50%;background:#1a0505;border:1px solid #7f1d1d;display:flex;align-items:center;justify-content:center;font-size:28px;">⚠️</div>
        <div style="font-size:16px;color:#f87171;text-align:center;line-height:1.7;max-width:290px;">${msg}</div>
        <button onclick="document.getElementById('error-overlay').remove();goTo('screen-scan-id');"
            style="margin-top:8px;background:#6d28d9;color:#fff;border:none;border-radius:14px;padding:16px 0;font-size:15px;cursor:pointer;width:100%;max-width:290px;font-weight:500;">
            ← go back
        </button>
    `;
    document.body.appendChild(overlay);
}

window.addEventListener('load', () => { initAurora(); startAurora(); });