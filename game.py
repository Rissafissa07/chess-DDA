import chess
import time
from agents import PlayerModel, find_move_error


def play_game(player_white, player_black, verbose=False, delay=0.5):
    board = chess.Board()
    move_history = []
    move_number = 1

    phase_data = {
    "opening": [],
    "middlegame": [],
    "endgame": []
}
    while not board.is_game_over():

        if verbose:
            print("\n" + "=" * 40)
            print(f"Move {move_number}")
            print(board.unicode())
            print()

        current_player = player_white if board.turn else player_black
        result = current_player.choose_move(board)
        if isinstance(result, tuple):
            move, move_values = result
        else:
            move = result
            move_values = None

        adaptive_player = None
        # Determine if the current player is adaptive and calculate move error if so
        # We check if the current player has a player_model attribute to identify if it's an adaptive player.
        if hasattr(player_white, "player_model") and current_player is not player_white:
            adaptive_player = player_white
        elif hasattr(player_black, "player_model") and current_player is not player_black:
            adaptive_player = player_black
        # If the current player is adaptive, we will calculate the move error based on the move values returned by the MCTS and update the player's model.
        move_error = None

        if adaptive_player is not None: # Only calculate move error and update model if the current player is adaptive
            _, evaluated_move_values = adaptive_player.base_mcts.choose_move(board)
            move_error = find_move_error(move, evaluated_move_values)
            adaptive_player.player_model.update(move_error)

            # Store these values so analysis.py can also analyze opponent moves.
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

        # Capture color before moving
        color = "white" if board.turn else "black"
        
        # Determine role based on whether current player has player_model
        role = "adaptive_mcts" if hasattr(current_player, "player_model") else "player"
        
        # Optional agent type for debugging/testing
        agent_type = current_player.__class__.__name__
        
        board.push(move)


        # Delay after move for better visualization if verbose mode is on
        if verbose:
            time.sleep(delay)

        if not board.turn:
            move_number += 1
        
        # Store move information for analysis, including the move error and move values if available
        move_info = {
            "color": color,
            "role": role,
            "agent_type": agent_type,
            "move": move,
            "phase": phase,
            "move_values": move_values,
            "move_error": move_error
        }

        # For debugging: print the move error and updated player model stats after each move if the current player is adaptive
        if adaptive_player is not None:
            print("\nPlayer model update:")
            print(f"move={move} (color={color}, role={role})")
            print(f"move_error={move_error:.3f}")
            print(f"updated_average_error={adaptive_player.player_model.average_error():.3f}")
            print(f"updated_consistency={adaptive_player.player_model.consistency():.3f}")

        move_history.append(move_info)
        phase_data[phase].append(move_info)
    # Game is over, print final board and result if verbose
    if verbose:
        print("\nFinal position:")
        print(board.unicode())
        print("Result:", board.result())

    return {
    "result": board.result(),
    "num_moves": len(move_history),
    "moves": move_history,
    "phases": phase_data
}


def simulate_games(player1, player2, n_games=1, verbose=True):
    results = []

    for i in range(n_games):
        print(f"\n=== Game {i+1} ===")
        results.append(play_game(player1, player2, verbose=verbose))

    return results