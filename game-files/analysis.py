import numpy as np


def compute_move_error(move_info):
    move_values = move_info["move_values"]

    if move_values is None:
        return None

    # best move value
    best_value = move_values[0][1]

    # find chosen move value
    chosen_move = move_info["move"]

    chosen_value = None
    for move, value, _ in move_values:
        if move == chosen_move:
            chosen_value = value
            break

    if chosen_value is None:
        return None

    return best_value - chosen_value


def analyze_phases(game_data):
    phase_errors = {
        "opening": [],
        "middlegame": [],
        "endgame": []
    }

    for move in game_data["moves"]:
        error = compute_move_error(move)

        if error is not None:
            phase_errors[move["phase"]].append(error)

    summary = {}

    for phase, errors in phase_errors.items():
        if len(errors) == 0:
            summary[phase] = {"avg_error": None, "consistency": None}
            continue

        avg_error = np.mean(errors)
        consistency = np.std(errors)  # 🔥 key metric

        summary[phase] = {
            "avg_error": avg_error,
            "consistency": consistency
        }

    return summary