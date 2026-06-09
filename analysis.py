import numpy as np


def compute_move_error(move_info):
    # Calculates how far the chosen move was from the top-ranked move.
    move_values = move_info["move_values"]

    if move_values is None:
        return None

    # Uses the first ranked move as the reference value.
    best_value = move_values[0][1]

    # Finds the value assigned to the move that was actually played.
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
    # Groups move errors by game phase for summary statistics.
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
        # Keeps empty phases explicit in the output.
        if len(errors) == 0:
            summary[phase] = {"avg_error": None, "consistency": None}
            continue

        # Average error shows move quality; standard deviation shows consistency.
        avg_error = np.mean(errors)
        consistency = np.std(errors)  

        summary[phase] = {
            "avg_error": avg_error,
            "consistency": consistency
        }

    return summary
