import chess
import time
from agents import PlayerModel, find_move_error


def play_game(player_white, player_black, verbose=False, delay=0.5):
    # Plays one full game between the supplied white and black players.
    board = chess.Board()
    move_history = []
    move_number = 1

    phase_data = {
    "opening": [],
    "middlegame": [],
    "endgame": []
}
    while not board.is_game_over():

        # Shows the current board when terminal output is requested.
        if verbose:
            print("\n" + "=" * 40)
            print(f"Move {move_number}")
            print(board.unicode())
            print()

        current_player = player_white if board.turn else player_black
        result = current_player.choose_move(board)

        # Supports agents that return only a move or a move plus evaluations.
        if isinstance(result, tuple):
            move, move_values = result
        else:
            move = result
            move_values = None

        adaptive_player = None

        # Finds the adaptive opponent whose player model should be updated.
        if hasattr(player_white, "player_model") and current_player is not player_white:
            adaptive_player = player_white
        elif hasattr(player_black, "player_model") and current_player is not player_black:
            adaptive_player = player_black

        move_error = None

        # Updates the adaptive model using the opponent's observed move error.
        if adaptive_player is not None:
            _, evaluated_move_values = adaptive_player.base_mcts.choose_move(board)
            move_error = find_move_error(move, evaluated_move_values)
            adaptive_player.player_model.update(move_error)

            # Keeps evaluated alternatives available for later analysis.
            if move_values is None:
                move_values = evaluated_move_values

        if verbose:
            print("Move played:", board.san(move))

        if move_number <= 10:
            phase = "opening"
        elif move_number <= 40:
            phase = "middlegame"
        else:
            phase = "endgame"

        # Stores side-to-move metadata before the board changes.
        color = "white" if board.turn else "black"
        
        # Marks whether this move came from the adaptive agent or the player.
        role = "adaptive_mcts" if hasattr(current_player, "player_model") else "player"
        
        # Records the concrete agent class for debugging and comparisons.
        agent_type = current_player.__class__.__name__
        
        board.push(move)


        # Adds a short pause for readable terminal replays.
        if verbose:
            time.sleep(delay)

        if not board.turn:
            move_number += 1
        
        # Stores the move record used by later analysis.
        move_info = {
            "color": color,
            "role": role,
            "agent_type": agent_type,
            "move": move,
            "phase": phase,
            "move_values": move_values,
            "move_error": move_error
        }

        # Prints player-model diagnostics after observed human moves.
        if adaptive_player is not None:
            print("\nPlayer model update:")
            print(f"move={move} (color={color}, role={role})")
            print(f"move_error={move_error:.3f}")
            print(f"updated_average_error={adaptive_player.player_model.average_error():.3f}")
            print(f"updated_consistency={adaptive_player.player_model.consistency():.3f}")

        move_history.append(move_info)
        phase_data[phase].append(move_info)

    # Shows the final board and result when terminal output is requested.
    if verbose:
        print("\nFinal position:")
        print(board.unicode())
        print("Result:", board.result())

    # Returns both move-level data and phase-grouped data.
    return {
    "result": board.result(),
    "num_moves": len(move_history),
    "moves": move_history,
    "phases": phase_data
}


def simulate_games(player1, player2, n_games=1, verbose=True):
    # Runs several games and collects each game summary.
    results = []

    for i in range(n_games):
        print(f"\n=== Game {i+1} ===")
        results.append(play_game(player1, player2, verbose=verbose))

    return results
