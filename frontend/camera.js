const SESSION_LOG = [];
let idImageBase64 = null;
let liveImageBase64 = null;
let activeStream = null;
let particleCanvas = null;
let particleCtx = null;
let particles = [];
let particleAnimFrame = null;

function initParticles() {
    particleCanvas = document.getElementById('particle-canvas');
    particleCtx = particleCanvas.getContext('2d');
    particleCanvas.width = window.innerWidth;
    particleCanvas.height = window.innerHeight;
    particles = [];
    for (let i = 0; i < 60; i++) {
        particles.push({
            x: Math.random() * particleCanvas.width,
            y: Math.random() * particleCanvas.height,
            r: Math.random() * 1.8 + 0.3,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4,
            a: Math.random() * Math.PI * 2
        });
    }
    drawParticles();
}

function drawParticles() {
    const W = particleCanvas.width;
    const H = particleCanvas.height;
    particleCtx.clearRect(0, 0, W, H);
    particles.forEach(p => {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1;
        if (p.y < 0 || p.y > H) p.vy *= -1;
        p.a += 0.015;
        const alpha = (Math.sin(p.a) + 1) / 2 * 0.5 + 0.1;
        particleCtx.beginPath();
        particleCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        particleCtx.fillStyle = `rgba(167,139,250,${alpha})`;
        particleCtx.fill();
    });
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const d = Math.sqrt(dx * dx + dy * dy);
            if (d < 80) {
                particleCtx.beginPath();
                particleCtx.moveTo(particles[i].x, particles[i].y);
                particleCtx.lineTo(particles[j].x, particles[j].y);
                particleCtx.strokeStyle = `rgba(109,40,217,${0.12 * (1 - d / 80)})`;
                particleCtx.lineWidth = 0.5;
                particleCtx.stroke();
            }
        }
    }
    particleAnimFrame = requestAnimationFrame(drawParticles);
}

function stopParticles() {
    if (particleAnimFrame) { cancelAnimationFrame(particleAnimFrame); particleAnimFrame = null; }
    if (particleCanvas) particleCanvas.classList.remove('active');
}

function startParticles() {
    if (!particleCanvas) initParticles();
    particleCanvas.classList.add('active');
    if (!particleAnimFrame) drawParticles();
}

function goTo(screenId) {
    const current = document.querySelector('.screen.active');
    const next = document.getElementById(screenId);
    if (current && current !== next) {
        current.classList.add('screen-transition-out');
        setTimeout(() => {
            current.classList.remove('active', 'screen-transition-out');
            next.classList.add('active', 'screen-transition-in');
            setTimeout(() => next.classList.remove('screen-transition-in'), 350);
        }, 280);
    } else {
        next.classList.add('active');
    }
    if (screenId === 'screen-home') startParticles();
    else stopParticles();
}

function startVerification() {
    stopParticles();
    goTo('screen-scan-id');
}

function resetApp() {
    idImageBase64 = null;
    liveImageBase64 = null;
    stopCamera();
    resetCameraUI('id');
    resetCameraUI('live');
    document.getElementById('age-input').value = '';
    ['face', 'age', 'doc'].forEach(name => {
        ['ok', 'warn'].forEach(type => {
            const card = document.getElementById(`lcard-${name}-${type}`);
            if (card) card.classList.remove('visible');
        });
    });
    goTo('screen-home');
}

function resetCameraUI(target) {
    const videoEl = document.getElementById(`video-${target}`);
    const placeholder = document.getElementById(`cam-placeholder-${target}`);
    const btnEl = document.getElementById(`btn-capture-${target}`);
    const previewEl = document.getElementById(`preview-${target}`);
    const retakeRow = document.getElementById(`retake-row-${target}`);
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
    if (activeStream) {
        activeStream.getTracks().forEach(t => t.stop());
        activeStream = null;
    }
}

async function startCamera(target) {
    if (target === 'live') {
        const ageInput = document.getElementById('age-input').value;
        const ageNum = parseInt(ageInput);
        if (!ageInput || isNaN(ageNum)) {
            document.getElementById('age-input').focus();
            document.getElementById('age-input').style.border = '1px solid #f87171';
            setTimeout(() => { document.getElementById('age-input').style.border = ''; }, 2000);
            return;
        }
        if (ageNum < 1 || ageNum > 120) {
            document.getElementById('age-input').value = '';
            document.getElementById('age-input').placeholder = 'enter age between 1-120';
            document.getElementById('age-input').style.border = '1px solid #f87171';
            setTimeout(() => {
                document.getElementById('age-input').style.border = '';
                document.getElementById('age-input').placeholder = 'enter age first';
            }, 2000);
            return;
        }
    }

    stopCamera();
    const videoEl = document.getElementById(`video-${target}`);
    const placeholder = document.getElementById(`cam-placeholder-${target}`);
    const btnEl = document.getElementById(`btn-capture-${target}`);

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
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
    const videoEl = document.getElementById(`video-${target}`);
    const canvasEl = document.getElementById(`canvas-${target}`);
    const scale = 2;
    canvasEl.width = videoEl.videoWidth * scale;
    canvasEl.height = videoEl.videoHeight * scale;
    const ctx = canvasEl.getContext('2d');
    ctx.scale(scale, scale);
    ctx.drawImage(videoEl, 0, 0);

    const base64 = canvasEl.toDataURL('image/jpeg', 0.95).split(',')[1];
    stopCamera();

    videoEl.classList.remove('active');
    const placeholder = document.getElementById(`cam-placeholder-${target}`);
    placeholder.style.display = 'none';

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
        placeholder.style.display = 'flex';
    };
}

function useGallery(target) {
    document.getElementById(`gallery-${target}`).click();
}

function handleGallery(event, target) {
    const file = event.target.files[0];
    if (!file) return;

    const isVideo = file.type.startsWith('video/');
    const placeholder = document.getElementById(`cam-placeholder-${target}`);
    const previewEl = document.getElementById(`preview-${target}`);
    const videoPreviewEl = document.getElementById(`video-preview-${target}`);
    const retakeRow = document.getElementById(`retake-row-${target}`);
    const btnEl = document.getElementById(`btn-capture-${target}`);
    const url = URL.createObjectURL(file);

    placeholder.style.display = 'none';

    if (isVideo) {
        videoPreviewEl.innerHTML = '';
        const v = document.createElement('video');
        v.src = url;
        v.autoplay = true;
        v.muted = true;
        v.loop = true;
        v.playsInline = true;
        v.setAttribute('playsinline', '');
        v.setAttribute('webkit-playsinline', '');
        v.style.cssText = 'width:100%;height:100%;object-fit:cover;display:block;';
        videoPreviewEl.style.cssText = 'display:block;width:100%;height:100%;position:absolute;top:0;left:0;';
        videoPreviewEl.appendChild(v);
        v.load();
        v.play().catch(() => {});

        previewEl.style.display = 'none';
        retakeRow.style.display = 'flex';
        btnEl.style.display = 'none';

        v.addEventListener('loadeddata', () => {
            const tmpCanvas = document.createElement('canvas');
            tmpCanvas.width = v.videoWidth || 640;
            tmpCanvas.height = v.videoHeight || 480;
            tmpCanvas.getContext('2d').drawImage(v, 0, 0, tmpCanvas.width, tmpCanvas.height);
            const base64 = tmpCanvas.toDataURL('image/jpeg', 0.95).split(',')[1];

            document.getElementById(`btn-use-${target}`).onclick = () => {
                if (target === 'id') {
                    idImageBase64 = base64;
                    videoPreviewEl.innerHTML = '';
                    videoPreviewEl.style.display = 'none';
                    retakeRow.style.display = 'none';
                    btnEl.style.display = 'block';
                    goTo('screen-live');
                } else {
                    liveImageBase64 = base64;
                    submitVerification();
                }
            };
        }, { once: true });

    } else {
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(',')[1];
            previewEl.src = e.target.result;
            previewEl.style.display = 'block';
            retakeRow.style.display = 'flex';
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
        };
        reader.readAsDataURL(file);
    }

    document.getElementById(`btn-retake-${target}`).onclick = () => {
        previewEl.style.display = 'none';
        if (videoPreviewEl) { videoPreviewEl.innerHTML = ''; videoPreviewEl.style.display = 'none'; }
        retakeRow.style.display = 'none';
        btnEl.style.display = 'block';
        btnEl.textContent = 'open camera';
        btnEl.onclick = () => startCamera(target);
        placeholder.style.display = 'flex';
        event.target.value = '';
    };
}

async function submitVerification() {
    const ageInput = document.getElementById('age-input').value;
    if (!ageInput) { displayError('missing required field: age_on_id'); return; }
    goTo('screen-processing');
    animateProcessing();
    try {
        const response = await fetch('/api/verify-face', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_image: idImageBase64, live_image: liveImageBase64 })
        });
        const faceResult = await response.json();
        const ageResponse = await fetch('/api/estimate-age', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ live_image: liveImageBase64, age_on_id: parseInt(ageInput) })
        });
        const ageResult = await ageResponse.json();
        const docResponse = await fetch('/api/check-document', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_image: idImageBase64 })
        });
        const docResult = await docResponse.json();
        showResult(faceResult, ageResult, docResult, parseInt(ageInput));
    } catch (err) {
        displayError('unexpected server error');
        console.error('fetch failed:', err);
    }
}

function animateProcessing() {
    const rows = ['proc-row-1','proc-row-2','proc-row-3','proc-row-4','proc-row-5'];
    const statuses = ['proc-1','proc-2','proc-3','proc-4','proc-5'];
    const dots = ['proc-dot-1','proc-dot-2','proc-dot-3','proc-dot-4','proc-dot-5'];
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

function getAgeVerdictText(ageResult, ageOnId) {
    if (!ageResult.success) return 'age check unavailable';
    const gap = ageResult.data.layers.consistency.gap;
    const absGap = Math.round(Math.abs(gap));
    if (absGap <= 3) return 'age consistent';
    const estimatedAge = ageResult.data.layers.age_model.estimated_age;
    if (estimatedAge < ageOnId) return `appears ${absGap} yrs younger than stated`;
    return `appears ${absGap} yrs older than stated`;
}

function showResult(faceResult, ageResult, docResult, ageOnId) {
    const faceVerdict = faceResult.success ? faceResult.data.layers.similarity.label : 'suspicious';
    const rawScore = faceResult.success ? faceResult.data.layers.similarity.score : 0;
    const faceScorePercent = Math.min(Math.round(rawScore * 100), 100);
    const ageFlagged = ageResult.success ? ageResult.data.layers.consistency.flag : false;
    const ageGap = ageResult.success ? ageResult.data.layers.consistency.gap : null;
    const docLabel = docResult.success ? docResult.data.layers.classifier.label : 'unknown';
    const docScore = docResult.success ? Math.round(docResult.data.layers.classifier.score * 100) : null;
    const docDeviation = docResult.success ? docResult.data.layers.geometric_analysis.deviation_score : null;
    const docZones = docResult.success ? docResult.data.layers.zone_detection : null;
    const overallVerified = faceVerdict === 'verified' && docLabel !== 'fake';

    const logEntry = {
        verdict: overallVerified ? 'verified' : 'suspicious',
        score: faceScorePercent,
        time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    };
    SESSION_LOG.unshift(logEntry);

    const ageText = getAgeVerdictText(ageResult, ageOnId);
    const ageGapLabel = ageGap !== null ? `gap ${Math.round(Math.abs(ageGap))}y` : '—';
    const docScoreText = docScore !== null ? `${docScore}%` : 'pending';
    const ageBarWidth = ageFlagged ? 20 : 88;
    const docBarWidth = docLabel === 'real' ? 92 : docLabel === 'unknown' ? 35 : 8;
    const deviationText = docDeviation !== null ? docDeviation.toFixed(3) : '—';
    const zonesText = docZones ? Object.entries(docZones).map(([k,v]) => `${k}: ${v ? '✓' : '✗'}`).join(' · ') : '—';

    if (overallVerified) {
        flashScreen('#4ade80');
        setTimeout(() => {
            goTo('screen-verified');
            setTimeout(() => {
                document.getElementById('score-fill-ok').style.width = `${faceScorePercent}%`;
                document.getElementById('score-num-ok').textContent = `${faceScorePercent}% match`;
            }, 150);
            document.getElementById('layer-face-ok').textContent = faceVerdict;
            document.getElementById('layer-face-score-ok').textContent = `${faceScorePercent}%`;
            document.getElementById('layer-age-ok').textContent = ageText;
            document.getElementById('layer-age-ok').className = `layer-card-val ${ageFlagged ? 'flag' : 'ok'}`;
            document.getElementById('layer-age-score-ok').textContent = ageGapLabel;
            document.getElementById('layer-doc-ok').textContent = docLabel;
            document.getElementById('layer-doc-score-ok').textContent = docScoreText;
            const dbg = document.getElementById('debug-panel-ok');
            if (dbg) dbg.textContent = `classifier: ${docScoreText} · deviation: ${deviationText} · zones: ${zonesText}`;
            setTimeout(() => { document.getElementById('lcard-face-ok').classList.add('visible'); setTimeout(() => { document.getElementById('layer-face-bar-ok').style.width = `${faceScorePercent}%`; }, 150); }, 300);
            setTimeout(() => { document.getElementById('lcard-age-ok').classList.add('visible'); setTimeout(() => { document.getElementById('layer-age-bar-ok').style.width = `${ageBarWidth}%`; }, 150); }, 550);
            setTimeout(() => { document.getElementById('lcard-doc-ok').classList.add('visible'); setTimeout(() => { document.getElementById('layer-doc-bar-ok').style.width = `${docBarWidth}%`; }, 150); launchConfetti(); }, 800);
        }, 250);
    } else {
        flashScreen('#f87171');
        setTimeout(() => {
            goTo('screen-suspicious');
            setTimeout(() => {
                document.getElementById('score-fill-warn').style.width = `${faceScorePercent}%`;
                document.getElementById('score-num-warn').textContent = `${faceScorePercent}% match`;
            }, 150);
            document.getElementById('layer-face-warn').textContent = faceVerdict;
            document.getElementById('layer-face-score-warn').textContent = `${faceScorePercent}%`;
            document.getElementById('layer-age-warn').textContent = ageText;
            document.getElementById('layer-age-warn').className = `layer-card-val ${ageFlagged ? 'flag' : 'ok'}`;
            document.getElementById('layer-age-score-warn').textContent = ageGapLabel;
            document.getElementById('layer-doc-warn').textContent = docLabel;
            document.getElementById('layer-doc-score-warn').textContent = docScoreText;
            const dbg = document.getElementById('debug-panel-warn');
            if (dbg) dbg.textContent = `classifier: ${docScoreText} · deviation: ${deviationText} · zones: ${zonesText}`;
            setTimeout(() => { document.getElementById('lcard-face-warn').classList.add('visible'); setTimeout(() => { document.getElementById('layer-face-bar-warn').style.width = `${faceScorePercent}%`; }, 150); }, 300);
            setTimeout(() => { document.getElementById('lcard-age-warn').classList.add('visible'); setTimeout(() => { document.getElementById('layer-age-bar-warn').style.width = `${ageBarWidth}%`; }, 150); }, 550);
            setTimeout(() => { document.getElementById('lcard-doc-warn').classList.add('visible'); setTimeout(() => { document.getElementById('layer-doc-bar-warn').style.width = `${docBarWidth}%`; }, 150); }, 800);
        }, 250);
    }
    renderLog();
}

function launchConfetti() {
    const container = document.getElementById('confetti-container');
    container.innerHTML = '';
    const colors = ['#a78bfa', '#4ade80', '#f472b6', '#fb923c', '#facc15', '#60a5fa', '#34d399'];
    for (let i = 0; i < 100; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = `${Math.random() * 100}%`;
        piece.style.top = `-20px`;
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = `${Math.random() * 1.2}s`;
        piece.style.animationDuration = `${1.8 + Math.random() * 1.5}s`;
        piece.style.width = `${4 + Math.random() * 9}px`;
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
        row.innerHTML = `<div class="log-dot ${isOk ? 'ok' : 'warn'}"></div><div class="log-verdict">${entry.verdict}</div><div class="${isOk ? 'log-score-ok' : 'log-score-warn'}">${entry.score}%</div><div class="log-time">${entry.time}</div>`;
        list.appendChild(row);
    });
}

function displayError(message) {
    const ERROR_MESSAGES = {
        'No face detected in ID photo': 'could not find a face on the ID — please retake',
        'No face detected in live photo': 'could not detect your face — please look at the camera',
        'Document perspective correction failed': 'ID image is too angled — please retake',
        'No document zones detected': 'could not read the ID document — please retake',
        'Model inference failed': 'system error — please try again',
        'Invalid image format': 'image format not supported — please retake',
        'missing required field: age_on_id': 'please enter the age shown on the ID',
        'Model not loaded — weights file missing': 'system not ready — contact support',
        'Unexpected server error': 'something went wrong — please try again'
    };
    alert(ERROR_MESSAGES[message] || 'something went wrong — please try again');
}

window.addEventListener('load', () => { initParticles(); startParticles(); });