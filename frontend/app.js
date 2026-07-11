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

// ---- DOM references ----
const btnNewGame  = document.getElementById("btn-new-game");
const btnBattle   = document.getElementById("btn-battle");
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
}

// ---- Animation ----
async function performAnimation(pending1, pending2, p1Won) {
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
    battleDisplay.innerHTML = `
        <span style="color: ${p1Won ? '#4CAF50' : '#aaa'}">${rankName(pending1[pending1.length - 1])}</span>
        <span style="color: #aaa; font-size: 1rem">vs</span>
        <span style="color: ${p1Won ? '#aaa' : '#e94560'}">${rankName(pending2[pending2.length - 1])}</span>
    `;

    await sleep(800);

    // show winner message briefly
    battleDisplay.innerHTML = p1Won
        ? `<span style="color: #4CAF50">P1 wins!</span>`
        : `<span style="color: #e94560">P2 wins!</span>`;

    await sleep(600);

    // clean up
    battleDisplay.innerHTML = "";
    warMessage.classList.add("hidden");
    animating = false;
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
    } catch (e) {
        gameMessage.textContent = "Failed to connect to backend.";
    }
});

btnBattle.addEventListener("click", async () => {
    if (!gameActive || animating) return;

    const c1 = q1[0];
    const c2 = q2[0];

    // run battle — updates q1/q2 in place and triggers animation
    const result = battle(q1, q2);

    // wait for animation to finish before updating UI and calling backend
    await performAnimation;
    renderHands();

    // check game over
    if (q1.length === 0 || q2.length === 0) {
        gameActive = false;
        gameMessage.textContent = q1.length > 0 ? "Player 1 wins!" : "Player 2 wins!";
        updateProbability(q1.length > 0 ? 1.0 : 0.0);
        setButtonState(false);
        await apiEndGame();
        return;
    }

    // check draw
    if (result === null) {
        gameActive = false;
        gameMessage.textContent = "Draw!";
        setButtonState(false);
        await apiEndGame();
        return;
    }

    // get probability from backend
    try {
        const data = await apiStep(c1, c2);
        updateProbability(data.p1_win_prob);
    } catch (e) {
        gameMessage.textContent = "Backend error — probability unavailable.";
    }

    setButtonState(true);
});