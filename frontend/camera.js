const SESSION_LOG = [];
let idImageBase64 = null;
let liveImageBase64 = null;
let activeStream = null;

function goTo(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function resetApp() {
    idImageBase64 = null;
    liveImageBase64 = null;
    stopCamera();
    goTo('screen-home');
}

function stopCamera() {
    if (activeStream) {
        activeStream.getTracks().forEach(t => t.stop());
        activeStream = null;
    }
}

async function startCamera(target) {
    stopCamera();
    const facingMode = target === 'id' ? 'environment' : 'user';
    const videoEl = document.getElementById(`video-${target}`);
    const placeholder = document.getElementById(`cam-placeholder-${target}`);
    const btnEl = document.getElementById(`btn-capture-${target}`);

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: facingMode }
        });
        activeStream = stream;
        videoEl.srcObject = stream;
        videoEl.classList.add('active');
        placeholder.style.display = 'none';
        btnEl.textContent = 'capture photo';
        btnEl.onclick = () => capturePhoto(target);
    } catch (err) {
        displayError(`camera access denied — please allow camera permission and refresh`);
        console.error('camera error:', err);
    }
}

function capturePhoto(target) {
    const videoEl = document.getElementById(`video-${target}`);
    const canvasEl = document.getElementById(`canvas-${target}`);
    canvasEl.width = videoEl.videoWidth;
    canvasEl.height = videoEl.videoHeight;
    canvasEl.getContext('2d').drawImage(videoEl, 0, 0);

    const base64 = canvasEl.toDataURL('image/jpeg', 0.9).split(',')[1];

    if (target === 'id') {
        idImageBase64 = base64;
        stopCamera();
        goTo('screen-live');
    } else {
        liveImageBase64 = base64;
        stopCamera();
        submitVerification();
    }
}

function useGallery(target) {
    document.getElementById(`gallery-${target}`).click();
}

function handleGallery(event, target) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        if (target === 'id') {
            idImageBase64 = base64;
            goTo('screen-live');
        }
    };
    reader.readAsDataURL(file);
}

async function submitVerification() {
    const ageInput = document.getElementById('age-input').value;

    if (!ageInput) {
        displayError('missing required field: age_on_id');
        return;
    }

    goTo('screen-processing');
    animateProcessing();

    try {
        const response = await fetch('/api/verify-face', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_image: idImageBase64,
                live_image: liveImageBase64
            })
        });

        const faceResult = await response.json();

        const ageResponse = await fetch('/api/estimate-age', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                live_image: liveImageBase64,
                age_on_id: parseInt(ageInput)
            })
        });

        const ageResult = await ageResponse.json();

        const docResponse = await fetch('/api/check-document', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id_image: idImageBase64
            })
        });

        const docResult = await docResponse.json();

        showResult(faceResult, ageResult, docResult, parseInt(ageInput));

    } catch (err) {
        displayError('unexpected server error');
        console.error('fetch failed:', err);
    }
}

function animateProcessing() {
    const steps = ['proc-1', 'proc-2', 'proc-3', 'proc-4', 'proc-5'];
    const labels = ['done', 'done', 'done', 'done', 'done'];
    steps.forEach((id, i) => {
        document.getElementById(id).textContent = 'waiting';
        document.getElementById(id).className = 'proc-status';
    });
    steps.forEach((id, i) => {
        setTimeout(() => {
            document.getElementById(id).textContent = 'running';
            document.getElementById(id).className = 'proc-status running';
        }, i * 600);
    });
}

function showResult(faceResult, ageResult, docResult, ageOnId) {
    const faceVerdict = faceResult.success ? faceResult.data.layers.similarity.label : 'suspicious';
    const faceScore = faceResult.success ? faceResult.data.layers.similarity.score : 0;
    const ageFlagged = ageResult.success ? ageResult.data.layers.consistency.flag : false;
    const docLabel = docResult.success ? docResult.data.layers.classifier.label : 'unknown';

    const overallVerified = faceVerdict === 'verified' && !ageFlagged && docLabel === 'real';

    const logEntry = {
        verdict: overallVerified ? 'verified' : 'suspicious',
        score: faceScore,
        time: new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    };
    SESSION_LOG.unshift(logEntry);

    if (overallVerified) {
        document.getElementById('score-fill-ok').style.width = `${Math.round(faceScore * 100)}%`;
        document.getElementById('score-num-ok').textContent = `${Math.round(faceScore * 100)}% match`;
        document.getElementById('layer-face-ok').textContent = faceVerdict;
        document.getElementById('layer-age-ok').textContent = ageFlagged ? 'flagged' : 'consistent';
        document.getElementById('layer-age-ok').className = `layer-val ${ageFlagged ? 'flag' : 'ok'}`;
        document.getElementById('layer-doc-ok').textContent = docLabel;
        launchConfetti();
        goTo('screen-verified');
    } else {
        document.getElementById('score-fill-warn').style.width = `${Math.round(faceScore * 100)}%`;
        document.getElementById('score-num-warn').textContent = `${Math.round(faceScore * 100)}% match`;
        document.getElementById('layer-face-warn').textContent = faceVerdict;
        document.getElementById('layer-age-warn').textContent = ageFlagged ? 'flagged' : 'consistent';
        document.getElementById('layer-age-warn').className = `layer-val ${ageFlagged ? 'flag' : 'ok'}`;
        document.getElementById('layer-doc-warn').textContent = docLabel;
        goTo('screen-suspicious');
    }

    renderLog();
}

function launchConfetti() {
    const container = document.getElementById('confetti-container');
    container.innerHTML = '';
    const colors = ['#a78bfa', '#4ade80', '#f472b6', '#fb923c', '#facc15', '#60a5fa'];

    for (let i = 0; i < 60; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = `${Math.random() * 100}%`;
        piece.style.top = `-10px`;
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = `${Math.random() * 0.8}s`;
        piece.style.animationDuration = `${1.2 + Math.random() * 1}s`;
        piece.style.width = `${4 + Math.random() * 6}px`;
        piece.style.height = `${4 + Math.random() * 6}px`;
        container.appendChild(piece);
    }

    setTimeout(() => { container.innerHTML = ''; }, 3000);
}

function renderLog() {
    const list = document.getElementById('log-list');
    list.innerHTML = '';
    SESSION_LOG.forEach(entry => {
        const row = document.createElement('div');
        row.className = 'log-entry';
        const isOk = entry.verdict === 'verified';
        row.innerHTML = `
            <div class="log-dot ${isOk ? 'ok' : 'warn'}"></div>
            <div class="log-verdict">${entry.verdict}</div>
            <div class="${isOk ? 'log-score-ok' : 'log-score-warn'}">${Math.round(entry.score * 100)}%</div>
            <div class="log-time">${entry.time}</div>
        `;
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
    alert(ERROR_MESSAGES[message] || message);
}