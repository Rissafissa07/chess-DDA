const pieceSymbols = {
  K: "♔",
  Q: "♕",
  R: "♖",
  B: "♗",
  N: "♘",
  P: "♙",
  k: "♚",
  q: "♛",
  r: "♜",
  b: "♝",
  n: "♞",
  p: "♟",
};

let gameState = null;
let selectedSquare = null;
let hoveredLegalDestination = null;
let isBusy = false;

const boardElement = document.querySelector("#board");
const boardShellElement = document.querySelector("#board-shell");
const boardAlertElement = document.querySelector("#board-alert");
const messageElement = document.querySelector("#message");
const humanColorInput = document.querySelector("#human-color");
const opponentTypeInput = document.querySelector("#opponent-type");
const newGameButton = document.querySelector("#new-game");
const saveLogButton = document.querySelector("#save-log");
const replayLogFileInput = document.querySelector("#replay-log-file");
const replayUntilPlyInput = document.querySelector("#replay-until-ply");
const startReplayButton = document.querySelector("#start-replay");

newGameButton.addEventListener("click", startNewGame);
saveLogButton.addEventListener("click", saveLog);
startReplayButton.addEventListener("click", startReplayExperiment);

async function startNewGame() {
  const response = await fetch("/api/new-game", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      human_color: humanColorInput.value,
      opponent_type: opponentTypeInput.value,
    }),
  });
  await applyResponse(response, "New game started.");
}

async function saveLog() {
  const response = await fetch("/api/save-log", { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    showMessage(data.error || "Could not save log.");
    return;
  }
  showMessage(`Saved log to ${data.path}`);
}

async function startReplayExperiment() {
  const file = replayLogFileInput.files[0];
  if (!file) {
    showMessage("Choose a saved JSON log.");
    return;
  }

  let replayLog = null;
  try {
    replayLog = JSON.parse(await file.text());
  } catch (error) {
    showMessage("Could not read replay log JSON.");
    return;
  }

  const response = await fetch("/api/start-replay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      log: replayLog,
      replay_source: file.name,
      replay_until_ply: replayUntilPlyInput.value,
    }),
  });
  await applyResponse(response, "Replay experiment started.");
}

async function makeMove(move) {
  setBusy(true);
  showMessage("Opponent thinking...");

  try {
    const response = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ move }),
    });
    await applyResponse(response, "Move played.");
  } catch (error) {
    showMessage("Move request failed.");
  } finally {
    setBusy(false);
  }
}

async function applyResponse(response, successMessage) {
  const data = await response.json();
  if (!response.ok) {
    if (data.state) {
      gameState = data.state;
      render();
    }
    showMessage(data.error || "Request failed.");
    return;
  }

  gameState = data;
  selectedSquare = null;
  hoveredLegalDestination = null;
  render();
  showMessage(successMessage);
}

function render() {
  renderBoard();
  renderBoardAlert();
  renderStatus();
  renderMoveLog();
  updateControls();
}

function renderBoard() {
  boardElement.innerHTML = "";
  if (!gameState) {
    return;
  }

  const rows = gameState.human_color === "black"
    ? [...gameState.board].reverse().map((row) => [...row].reverse())
    : gameState.board;

  for (const [rowIndex, row] of rows.entries()) {
    for (const [columnIndex, square] of row.entries()) {
      const button = document.createElement("button");
      button.className = "square";
      button.dataset.square = square.square;
      button.setAttribute("aria-label", square.square);

      const file = square.square.charCodeAt(0) - "a".charCodeAt(0);
      const rank = Number(square.square[1]);
      if ((file + rank) % 2 === 0) {
        button.classList.add("dark");
      } else {
        button.classList.add("light");
      }

      if (square.square === selectedSquare) {
        button.classList.add("selected");
      }
      if (isLegalDestination(square.square)) {
        button.classList.add("legal-target");
      }
      if (square.square === hoveredLegalDestination && isLegalDestination(square.square)) {
        button.classList.add("legal-move-hover");
      }

      if (square.piece) {
        const piece = document.createElement("span");
        piece.className = "piece";
        piece.textContent = pieceSymbols[square.piece];
        button.appendChild(piece);
      }

      if (columnIndex === 0) {
        const rankLabel = document.createElement("span");
        rankLabel.className = "coordinate rank-coordinate";
        rankLabel.textContent = square.square[1];
        button.appendChild(rankLabel);
      }

      if (rowIndex === rows.length - 1) {
        const fileLabel = document.createElement("span");
        fileLabel.className = "coordinate file-coordinate";
        fileLabel.textContent = square.square[0];
        button.appendChild(fileLabel);
      }

      button.addEventListener("click", () => handleSquareClick(square.square));
      button.addEventListener("mouseenter", (event) => handleSquareMouseEnter(event, square.square));
      button.addEventListener("mouseleave", handleSquareMouseLeave);
      button.draggable = false;
      boardElement.appendChild(button);
    }
  }
}

function handleSquareClick(square) {
  if (isBusy || !gameState || gameState.current_role !== "human" || gameState.status !== "ongoing" && gameState.status !== "ongoing: check") {
    return;
  }

  if (!selectedSquare) {
    selectedSquare = square;
    hoveredLegalDestination = null;
    renderBoard();
    return;
  }

  const move = selectedSquare + square;
  if (isLegalMove(move)) {
    makeMove(move);
    return;
  }

  showMessage("Illegal move");
  selectedSquare = square;
  hoveredLegalDestination = null;
  renderBoard();
}

function handleSquareMouseEnter(event, square) {
  if (!isLegalDestination(square)) {
    return;
  }

  hoveredLegalDestination = square;
  event.currentTarget.classList.add("legal-move-hover");
}

function handleSquareMouseLeave(event) {
  if (hoveredLegalDestination === null) {
    return;
  }

  hoveredLegalDestination = null;
  event.currentTarget.classList.remove("legal-move-hover");
}

function canStartMoveFrom(square, piece) {
  if (!piece || isBusy || !gameState || gameState.current_role !== "human" || isGameOver()) {
    return false;
  }
  return gameState.legal_moves.some((move) => move.startsWith(square));
}

function isGameOver() {
  return Boolean(gameState?.result) || ["checkmate", "stalemate", "draw"].includes(gameState?.status);
}

function isLegalMove(move) {
  return gameState.legal_moves.includes(move) || gameState.legal_moves.includes(move + "q");
}

function isLegalDestination(square) {
  if (!selectedSquare || !gameState) {
    return false;
  }
  return gameState.legal_moves.some((move) => move.startsWith(selectedSquare + square));
}

function renderStatus() {
  document.querySelector("#status").textContent = gameState?.status || "No game";
  document.querySelector("#turn").textContent = gameState ? `${gameState.turn} (${gameState.current_role})` : "-";
  document.querySelector("#white-role").textContent = gameState?.white_role || "-";
  document.querySelector("#black-role").textContent = gameState?.black_role || "-";
  document.querySelector("#num-moves").textContent = gameState?.num_moves ?? 0;
  document.querySelector("#result").textContent = gameState?.result || "-";
}

function renderBoardAlert() {
  boardAlertElement.textContent = "";
  boardAlertElement.className = "board-alert";
  boardShellElement.classList.toggle("game-over", false);

  if (!gameState) {
    return;
  }

  if (gameState.status === "ongoing: check") {
    boardAlertElement.textContent = "CHECK";
    boardAlertElement.classList.add("visible", "check-alert");
    return;
  }

  if (gameState.status === "checkmate") {
    boardAlertElement.textContent = "CHECKMATE";
    boardAlertElement.classList.add("visible", "game-over-alert");
    boardShellElement.classList.add("game-over");
    return;
  }

  if (gameState.status === "stalemate") {
    boardAlertElement.textContent = "STALEMATE";
    boardAlertElement.classList.add("visible", "game-over-alert");
    boardShellElement.classList.add("game-over");
    return;
  }

  if (gameState.status === "draw") {
    boardAlertElement.textContent = "DRAW";
    boardAlertElement.classList.add("visible", "game-over-alert");
    boardShellElement.classList.add("game-over");
  }
}

function renderMoveLog() {
  const moveLog = document.querySelector("#move-log");
  moveLog.innerHTML = "";
  if (!gameState) {
    return;
  }

  gameState.moves.forEach((moveInfo, index) => {
    const item = document.createElement("li");
    item.className = "move-log-entry";
    if (index === gameState.moves.length - 1) {
      item.classList.add("latest");
    }

    const error = moveInfo.move_error === null || moveInfo.move_error === undefined
      ? "-"
      : moveInfo.move_error.toFixed(3);

    item.innerHTML = `
      <span class="move-main">${moveInfo.move}</span>
      <span class="move-meta">${moveInfo.color} | ${moveInfo.role}</span>
      <span class="move-phase">${moveInfo.phase}</span>
      <span class="move-error">error ${error}</span>
    `;
    moveLog.appendChild(item);
  });

  moveLog.scrollTop = moveLog.scrollHeight;
}

function showMessage(message) {
  messageElement.textContent = message;
}

function setBusy(busy) {
  isBusy = busy;
  updateControls();
}

function updateControls() {
  newGameButton.disabled = isBusy;
  saveLogButton.disabled = isBusy;
  startReplayButton.disabled = isBusy;
  boardElement.classList.toggle("busy", isBusy);
}
