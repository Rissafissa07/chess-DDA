from flask import Flask, jsonify, render_template, request

from web_game import WebChessGame


app = Flask(__name__)
current_game = None
DEFAULT_MCTS_SIMULATIONS = 100


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/new-game")
def new_game():
    global current_game

    data = request.get_json(silent=True) or {}
    human_color = data.get("human_color", "white")
    opponent_type = data.get("opponent_type", "adaptive_mcts")
    simulations = DEFAULT_MCTS_SIMULATIONS

    try:
        current_game = WebChessGame(
            human_color=human_color,
            opponent_type=opponent_type,
            simulations=simulations,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    return jsonify(current_game.state())


@app.get("/api/state")
def state():
    if current_game is None:
        return jsonify({"error": "No active game."}), 404
    return jsonify(current_game.state())


@app.post("/api/move")
def move():
    if current_game is None:
        return jsonify({"error": "No active game."}), 404

    data = request.get_json(silent=True) or {}
    move_uci = data.get("move")
    if not move_uci:
        return jsonify({"error": "Missing move."}), 400

    try:
        current_game.play_human_move(move_uci)
    except ValueError as error:
        return jsonify({"error": str(error), "state": current_game.state()}), 400

    return jsonify(current_game.state())


@app.post("/api/save-log")
def save_log():
    if current_game is None:
        return jsonify({"error": "No active game."}), 404

    path = current_game.save_log()
    return jsonify({"saved": True, "path": path, "log": current_game.log_data()})


if __name__ == "__main__":
    app.run(debug=True)
