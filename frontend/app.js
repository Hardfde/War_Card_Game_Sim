    // ---- Constants ----
    const API = "http://localhost:8000";
    const RANK_NAMES = {
        11: "J", 12: "Q", 13: "K", 14: "A"
    };

    // ---- Game state ----
    let q1 = [];
    let q2 = [];
    let gameActive = false;
    let animating = false;
    let playing = false;
    let playTimer = null;

    // ---- DOM references ----
    const btnNewGame  = document.getElementById("btn-new-game");
    const btnBattle   = document.getElementById("btn-battle");
    const btnPlayPause  = document.getElementById("btn-play-pause");
    const speedSlider   = document.getElementById("speed-slider");
    const speedLabel    = document.getElementById("speed-label");
    const p1Hand      = document.getElementById("p1-hand");
    const p2Hand      = document.getElementById("p2-hand");
    const p1Count     = document.getElementById("p1-card-count");
    const p2Count     = document.getElementById("p2-card-count");
    const battleDisplay = document.getElementById("battle-display");
    const warMessage  = document.getElementById("war-message");
    const probBarP1   = document.getElementById("prob-bar-p1");
    const probBarP2   = document.getElementById("prob-bar-p2");
    const p1ProbLabel = document.getElementById("p1-prob-label");
    const p2ProbLabel = document.getElementById("p2-prob-label");
    const gameMessage = document.getElementById("game-message");

    // ---- Helpers ----
    function rankName(r) {
        return RANK_NAMES[r] || String(r);
    }

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function setButtonState(battleEnabled) {
        btnBattle.disabled = !battleEnabled || animating;
    }

    // speed slider value is battles/sec — convert to ms delay between battles
    function getDelayMs() {
        return Math.round(1000 / parseInt(speedSlider.value));
    }

    // ---- Rendering ----
    function renderHand(container, cards, highlightIndex = -1) {
        container.innerHTML = "";
        const SHOW = 12;
        const visible = cards.slice(0, SHOW);

        visible.forEach((rank, i) => {
            const pip = document.createElement("div");
            pip.className = "card-pip" + (i === highlightIndex ? " highlight" : "");
            pip.textContent = rankName(rank);
            container.appendChild(pip);
        });

        if (cards.length > SHOW) {
            const more = document.createElement("span");
            more.textContent = `+${cards.length - SHOW} more`;
            more.style.fontSize = "12px";
            more.style.color = "#aaa";
            more.style.alignSelf = "center";
            container.appendChild(more);
        }
    }

    function renderHands() {
        renderHand(p1Hand, q1);
        renderHand(p2Hand, q2);
        p1Count.textContent = `${q1.length} cards`;
        p2Count.textContent = `${q2.length} cards`;
    }

    function updateProbability(p1WinProb) {
        const p1Pct = Math.round(p1WinProb * 100);
        const p2Pct = 100 - p1Pct;
        probBarP1.style.width = p1Pct + "%";
        probBarP2.style.width = p2Pct + "%";
        p1ProbLabel.textContent = `P1: ${p1Pct}%`;
        p2ProbLabel.textContent = `P2: ${p2Pct}%`;
        updateGraph(p1WinProb);
    }

    // ---- Animation ----
    async function performAnimation(pending1, pending2, p1Won) {
        if (!gameActive) return;
        animating = true;
        setButtonState(false);

        // show war message if applicable
        if (pending1.length > 1) {
            warMessage.classList.remove("hidden");
            await sleep(600);
        }

        // highlight the deciding cards in each hand briefly
        // pending lists contain cards that have already left the queues
        // so we just display them in the battle zone
        if (!gameActive) return;
        battleDisplay.innerHTML = `
            <span style="color: ${p1Won ? '#4CAF50' : '#aaa'}">${rankName(pending1[pending1.length - 1])}</span>
            <span style="color: #aaa; font-size: 1rem">vs</span>
            <span style="color: ${p1Won ? '#aaa' : '#e94560'}">${rankName(pending2[pending2.length - 1])}</span>
        `;

        await sleep(800);

        // show winner message briefly
        if (!gameActive) return;
        battleDisplay.innerHTML = p1Won
            ? `<span style="color: #4CAF50">P1 wins!</span>`
            : `<span style="color: #e94560">P2 wins!</span>`;

        await sleep(600);

        // clean up
        battleDisplay.innerHTML = "";
        warMessage.classList.add("hidden");
        animating = false;
        if (!playing && gameActive) {
            btnBattle.disabled = false;
        }
    }

    // ---- Graph constants ----
    const WINDOW         = 100;
    const GRAPH_PAD_LEFT   = 40;
    const GRAPH_PAD_RIGHT  = 10;
    const GRAPH_PAD_TOP    = 10;
    const GRAPH_PAD_BOTTOM = 30;

    // ---- Graph state ----
    let probHistory  = [];      // full history, grows unbounded
    let showFullHistory = false;
    let offscreen    = null;
    let offscreenCtx = null;

    // ---- Graph DOM ----
    const axesCanvas = document.getElementById("graph-axes");
    const lineCanvas = document.getElementById("graph-line");
    const axesCtx    = axesCanvas.getContext("2d");
    const lineCtx    = lineCanvas.getContext("2d");
    const btnHistory = document.getElementById("btn-history");
    const turnLabel  = document.getElementById("turn-label");


    // ---- Graph helpers ----

    // sync both canvas pixel resolutions to their CSS display size
    // must be called before any drawing — setting .width clears the canvas
    function syncCanvasSize() {
        const W = axesCanvas.offsetWidth;
        const H = axesCanvas.offsetHeight;
        axesCanvas.width  = W; axesCanvas.height = H;
        lineCanvas.width  = W; lineCanvas.height = H;
    }

    function getDrawDims() {
        return {
            W: axesCanvas.width,
            H: axesCanvas.height,
            drawW: axesCanvas.width  - GRAPH_PAD_LEFT - GRAPH_PAD_RIGHT,
            drawH: axesCanvas.height - GRAPH_PAD_TOP  - GRAPH_PAD_BOTTOM,
        };
    }

    // converts a probability value to a y pixel coordinate
    function probToY(prob, drawH) {
        return GRAPH_PAD_TOP + drawH * (1 - prob);
    }

    // converts a data index to an x pixel coordinate
    // n is the total number of points being displayed
    function indexToX(i, n, drawW) {
        return GRAPH_PAD_LEFT + (i / Math.max(n - 1, 1)) * drawW;
    }


    // ---- Axes canvas ----
    // redrawn whenever x-scale changes

    function drawAxes(data) {
    const { W, H, drawW, drawH } = getDrawDims();
 
    // clear only — background comes from CSS on the wrapper
    axesCtx.clearRect(0, 0, W, H);
 
    // ---- y-axis labels and horizontal reference lines ----
    axesCtx.font         = "11px sans-serif";
    axesCtx.textBaseline = "middle";
    axesCtx.textAlign    = "right";
 
    [0, 25, 50, 75, 100].forEach(pct => {
        const y = probToY(pct / 100, drawH);
 
        axesCtx.fillStyle = "#aaa";
        axesCtx.fillText(pct + "%", GRAPH_PAD_LEFT - 6, y);
 
        // 50% line is brighter and thicker as a reference
        axesCtx.strokeStyle = pct === 50 ? "#555" : "#2a2a4a";
        axesCtx.lineWidth   = pct === 50 ? 1.5 : 0.5;
        axesCtx.beginPath();
        axesCtx.moveTo(GRAPH_PAD_LEFT, y);
        axesCtx.lineTo(W - GRAPH_PAD_RIGHT, y);
        axesCtx.stroke();
    });
 
    // ---- x-axis labels ----
    // step size scales with history length so labels don't get crowded
    const n = data.length;
    const step = n < 10  ? 1
               : n < 100 ? 10
               : n < 500 ? 50
               : 100;
 
    axesCtx.fillStyle    = "#aaa";
    axesCtx.textAlign    = "center";
    axesCtx.textBaseline = "top";
 
    data.forEach((_, i) => {
        const turn = i + 1;   // 1-based turn number
        if (turn === 1 || turn % step === 0) {
            const x = indexToX(i, n, drawW);
            axesCtx.fillText(turn, x, GRAPH_PAD_TOP + drawH + 6);
        }
    });
}
 
 
// ---- Line canvas ----
 
function drawLine(data) {
    const { W, H, drawW, drawH } = getDrawDims();
    lineCtx.clearRect(0, 0, W, H);
 
    if (data.length < 2) return;
 
    const midY   = probToY(0.5, drawH);
    const firstX = indexToX(0, data.length, drawW);
    const lastX  = indexToX(data.length - 1, data.length, drawW);
 
    // build path once — line across top, then close back along the 50% midline
    // closing at midY rather than the bottom means fills are relative to 50%
    function buildPath(ctx) {
        ctx.beginPath();
        data.forEach((prob, i) => {
            const x = indexToX(i, data.length, drawW);
            const y = probToY(prob, drawH);
            if (i === 0) ctx.moveTo(x, y);
            else         ctx.lineTo(x, y);
        });
        ctx.lineTo(lastX,  midY);   // close right edge down/up to 50% line
        ctx.lineTo(firstX, midY);   // across 50% line back to start
        ctx.closePath();
    }
 
    // ---- blue fill above 50% ----
    // clip to the region above midY so only the above-50% portion fills blue
    lineCtx.save();
    lineCtx.beginPath();
    lineCtx.rect(GRAPH_PAD_LEFT, GRAPH_PAD_TOP, drawW, midY - GRAPH_PAD_TOP);
    lineCtx.clip();
    buildPath(lineCtx);
    lineCtx.fillStyle = "rgba(74, 144, 217, 0.3)";
    lineCtx.fill();
    lineCtx.restore();
 
    // ---- red fill below 50% ----
    // clip to the region below midY
    lineCtx.save();
    lineCtx.beginPath();
    lineCtx.rect(GRAPH_PAD_LEFT, midY, drawW, GRAPH_PAD_TOP + drawH - midY);
    lineCtx.clip();
    buildPath(lineCtx);
    lineCtx.fillStyle = "rgba(233, 69, 96, 0.3)";
    lineCtx.fill();
    lineCtx.restore();
 
    // ---- stroke the line on top of the fills ----
    lineCtx.beginPath();
    data.forEach((prob, i) => {
        const x = indexToX(i, data.length, drawW);
        const y = probToY(prob, drawH);
        if (i === 0) lineCtx.moveTo(x, y);
        else         lineCtx.lineTo(x, y);
    });
    lineCtx.strokeStyle = "#4a90d9";
    lineCtx.lineWidth   = 2;
    lineCtx.lineJoin    = "round";
    lineCtx.stroke();
 
    // ---- dot at current (rightmost) point ----
    const lastProb = data[data.length - 1];
    lineCtx.fillStyle = "#4a90d9";
    lineCtx.beginPath();
    lineCtx.arc(lastX, probToY(lastProb, drawH), 5, 0, Math.PI * 2);
    lineCtx.fill();
}


    // ---- Main graph update — called every turn ----

    function updateGraph(newProb) {
        probHistory.push(newProb);
        turnLabel.textContent = `Turn ${probHistory.length}`;
        syncCanvasSize();
        drawAxes(probHistory);
        drawLine(probHistory);
    }   

    function clearGraph() {
        probHistory = [];
        syncCanvasSize();
        axesCtx.clearRect(0, 0, axesCanvas.width, axesCanvas.height);
        lineCtx.clearRect(0, 0, lineCanvas.width, lineCanvas.height);
        turnLabel.textContent = "Turn 0";
    }


    // ---- Game logic ----
    async function battle(q1, q2, pending1 = [], pending2 = []) {
        const c1 = q1.shift();
        const c2 = q2.shift();

        pending1 = [...pending1, c1];
        pending2 = [...pending2, c2];

        if (c1 > c2) {
            q1.push(...pending1, ...pending2);
            performAnimation(pending1, pending2, true);
            return;
        }

        if (c1 < c2) {
            q2.push(...pending2, ...pending1);
            performAnimation(pending1, pending2, false);
            return;
        }

        // tie — war
        if (q1.length < 4 && q2.length < 4) {
            return null;
        }
        if (q1.length < 4) {
            q2.push(...pending2, ...pending1, ...q1);
            q1.length = 0;
            return;
        }
        if (q2.length < 4) {
            q1.push(...pending1, ...pending2, ...q2);
            q2.length = 0;
            return;
        }

        for (let i = 0; i < 3; i++) {
            pending1.push(q1.shift());
            pending2.push(q2.shift());
        }

        return battle(q1, q2, pending1, pending2);
    }

    async function endGame(message, finalProb) {
        gameActive = false;
        gameMessage.textContent = message;
        updateProbability(finalProb);
        btnBattle.disabled    = true;
        btnPlayPause.disabled = true;
        playing = false;
        btnPlayPause.textContent = "Play";
        clearTimeout(playTimer);
        playTimer = null;
        await apiEndGame();
    }

    // ---- API calls ----
    async function apiNewGame(q1, q2) {
        const response = await fetch(`${API}/game/new`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ q1, q2 })
        });
        if (!response.ok) throw new Error(`/game/new failed: ${response.status}`);
        return response.json();
    }

    async function apiStep(c1, c2) {
        const response = await fetch(`${API}/game/step`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ c1, c2 })
        });
        if (!response.ok) throw new Error(`/game/step failed: ${response.status}`);
        return response.json();
    }

    async function apiEndGame() {
        await fetch(`${API}/game/end`, { method: "POST" });
    }

    // ---- Button handlers ----
    btnNewGame.addEventListener("click", async () => {
        gameMessage.textContent = "";
        battleDisplay.innerHTML = "";
        clearGraph();

        // build and shuffle deck on frontend
        const deck = [];
        for (let rank = 2; rank <= 14; rank++) {
            for (let i = 0; i < 4; i++) deck.push(rank);
        }
        // fisher-yates shuffle
        for (let i = deck.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [deck[i], deck[j]] = [deck[j], deck[i]];
        }

        q1 = deck.slice(0, 26);
        q2 = deck.slice(26);

        try {
            await apiNewGame(q1, q2);
            gameActive = true;
            updateProbability(0.5);
            renderHands();
            setButtonState(true);
            btnPlayPause.disabled = false;

        } catch (e) {
            gameMessage.textContent = "Failed to connect to backend.";
        }
    });

    btnBattle.addEventListener("click", async () => {
        if (!gameActive || animating || playing) return;

        
        const c1 = q1[0];
        const c2 = q2[0];

        // run battle — updates q1/q2 in place and triggers animation
        const result = await battle(q1, q2);
        // wait for animation to finish before updating UI and calling backend
        renderHands();

        // check draw
        if (result === null) {
            endGame("Draw!", 0.5);
            return;
        }

        // check game over
        if (q1.length === 0 || q2.length === 0) {
            const p1Wins = q1.length > 0;
                endGame(p1Wins ? "Player 1 wins!" : "Player 2 wins!", p1Wins ? 1.0 : 0.0);
                return;
        }

        // get probability from backend
        try {
            const data = await apiStep(c1, c2);
            updateProbability(data.p1_win_prob);
        } catch (e) {
            gameMessage.textContent = "Backend error — probability unavailable.";
        }
        btnBattle.disabled = false;
    });


    btnPlayPause.addEventListener("click", () => {
        if (!gameActive) return;

        if (playing) {
            // pause
            playing = false;
            clearTimeout(playTimer);
            playTimer = null;
            btnPlayPause.textContent = "Play";
            return;
        }

        // play
        playing = true;
        btnPlayPause.textContent = "Pause";

        async function scheduleNext() {
            if (!playing || !gameActive) return;

            const c1 = q1[0];
            const c2 = q2[0];
            const result = await battle(q1, q2);
            renderHands();

            if (result === null) {
                endGame("Draw!", 0.5);
                return;
            }

            if (q1.length === 0 || q2.length === 0) {
                const p1Wins = q1.length > 0;
                endGame(p1Wins ? "Player 1 wins!" : "Player 2 wins!", p1Wins ? 1.0 : 0.0);
                return;
            }

            try {
                const data = await apiStep(c1, c2);
                updateProbability(data.p1_win_prob);
            } catch (e) {
                gameMessage.textContent = "Backend error — probability unavailable.";
            }

            playTimer = setTimeout(scheduleNext, getDelayMs());
        }

        scheduleNext();
    });

    // update speed label live as slider moves
    speedSlider.addEventListener("input", () => {
        speedLabel.textContent = speedSlider.value;
    });