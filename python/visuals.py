import chess
import time


def play_visual_game(player_white, player_black, delay=1):
    # Initialize the chess board
    board = chess.Board()
    move_number = 1
    # Main game loop
    while not board.is_game_over():
        print("\n" + "=" * 40)
        print(f"Move {move_number}")
        print(board.unicode())
        print()
        # Determine the current player and get their move
        current_player = player_white if board.turn else player_black
        move = current_player.choose_move(board)

        print("Move played:", move)

        board.push(move)
        time.sleep(delay)

        if not board.turn:
            move_number += 1

    print("\nFinal board:")
    print(board.unicode())
    print("Result:", board.result())