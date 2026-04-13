import chess
import time


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

        if verbose:
            print("Move played:", board.san(move))

        if move_number <= 10:
            phase = "opening"
        elif move_number <= 40:
            phase = "middlegame"
        else:
            phase = "endgame"

        board.push(move)



        if verbose:
            time.sleep(delay)

        if not board.turn:
            move_number += 1
        
        move_info = {
            "player": board.turn,
            "move": move,
            "phase": phase,
            "move_values": move_values
        }

        move_history.append(move_info)
        phase_data[phase].append(move_info)

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