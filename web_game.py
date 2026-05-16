import json
import os
from datetime import datetime

import chess

from agents import AdaptiveMCTSPlayer, find_move_error


class WebChessGame:
    def __init__(self, human_color="white", simulations=100):
        if human_color not in ("white", "black"):
            raise ValueError("human_color must be 'white' or 'black'")

        self.board = chess.Board()
        self.adaptive_player = AdaptiveMCTSPlayer(simulations=simulations)
        self.white_role = "human" if human_color == "white" else "adaptive_mcts"
        self.black_role = "human" if human_color == "black" else "adaptive_mcts"
        self.move_history = []
        self.phase_data = {
            "opening": [],
            "middlegame": [],
            "endgame": [],
        }

        if self.current_role() == "adaptive_mcts":
            self.play_adaptive_move()

    def current_color(self):
        return "white" if self.board.turn == chess.WHITE else "black"

    def current_role(self):
        return self.white_role if self.board.turn == chess.WHITE else self.black_role

    def human_color(self):
        return "white" if self.white_role == "human" else "black"

    def phase_for_current_move(self):
        move_number = self.board.fullmove_number
        if move_number <= 10:
            return "opening"
        if move_number <= 40:
            return "middlegame"
        return "endgame"

    def legal_moves(self):
        if self.board.is_game_over(claim_draw=True) or self.current_role() != "human":
            return []
        return [move.uci() for move in self.board.legal_moves]

    def play_human_move(self, move_uci):
        if self.board.is_game_over(claim_draw=True):
            raise ValueError("The game is already over.")
        if self.current_role() != "human":
            raise ValueError("It is not the human player's turn.")

        move = self.parse_legal_move(move_uci)

        _, move_values = self.adaptive_player.base_mcts.choose_move(self.board.copy())
        move_error = find_move_error(move, move_values)
        self.adaptive_player.player_model.update(move_error)

        self.push_logged_move(
            move=move,
            role="human",
            agent_type="Human",
            move_values=move_values,
            move_error=move_error,
        )

        if not self.board.is_game_over(claim_draw=True) and self.current_role() == "adaptive_mcts":
            self.play_adaptive_move()

    def play_adaptive_move(self):
        if self.board.is_game_over(claim_draw=True):
            return
        if self.current_role() != "adaptive_mcts":
            return

        result = self.adaptive_player.choose_move(self.board.copy())
        if isinstance(result, tuple):
            move, move_values = result
        else:
            move = result
            move_values = None

        self.push_logged_move(
            move=move,
            role="adaptive_mcts",
            agent_type="AdaptiveMCTSPlayer",
            move_values=move_values,
            move_error=None,
        )

    def parse_legal_move(self, move_uci):
        candidate_uci = move_uci.strip().lower()
        candidates = [candidate_uci]
        if len(candidate_uci) == 4:
            candidates.append(candidate_uci + "q")

        for candidate in candidates:
            try:
                move = chess.Move.from_uci(candidate)
            except ValueError:
                continue
            if move in self.board.legal_moves:
                return move

        raise ValueError("Illegal move.")

    def push_logged_move(self, move, role, agent_type, move_values, move_error):
        color = self.current_color()
        phase = self.phase_for_current_move()

        move_info = {
            "color": color,
            "role": role,
            "agent_type": agent_type,
            "move": move,
            "phase": phase,
            "move_values": move_values,
            "move_error": move_error,
        }

        self.board.push(move)
        self.move_history.append(move_info)
        self.phase_data[phase].append(move_info)

    def status(self):
        if self.board.is_checkmate():
            return "checkmate"
        if self.board.is_stalemate():
            return "stalemate"
        if self.board.is_insufficient_material():
            return "draw"
        if self.board.can_claim_threefold_repetition() or self.board.can_claim_fifty_moves():
            return "draw"
        if self.board.is_game_over(claim_draw=True):
            return "draw"
        if self.board.is_check():
            return "ongoing: check"
        return "ongoing"

    def state(self):
        return {
            "board": self.board_array(),
            "fen": self.board.fen(),
            "turn": self.current_color(),
            "current_role": self.current_role(),
            "human_color": self.human_color(),
            "white_role": self.white_role,
            "black_role": self.black_role,
            "legal_moves": self.legal_moves(),
            "status": self.status(),
            "result": self.board.result(claim_draw=True) if self.board.is_game_over(claim_draw=True) else None,
            "num_moves": len(self.move_history),
            "moves": [self.serialize_move_info(move) for move in self.move_history],
        }

    def board_array(self):
        squares = []
        for rank in range(7, -1, -1):
            row = []
            for file_index in range(8):
                square = chess.square(file_index, rank)
                piece = self.board.piece_at(square)
                row.append({
                    "square": chess.square_name(square),
                    "piece": piece.symbol() if piece else None,
                })
            squares.append(row)
        return squares

    def serialize_move_info(self, move_info):
        return {
            "color": move_info["color"],
            "role": move_info["role"],
            "agent_type": move_info["agent_type"],
            "move": move_info["move"].uci(),
            "phase": move_info["phase"],
            "move_values": self.serialize_move_values(move_info["move_values"]),
            "move_error": move_info["move_error"],
        }

    def serialize_move_values(self, move_values):
        if move_values is None:
            return None
        return [
            {
                "move": move.uci(),
                "value": value,
                "visits": visits,
            }
            for move, value, visits in move_values
        ]

    def log_data(self):
        serialized_moves = [self.serialize_move_info(move) for move in self.move_history]
        return {
            "result": self.board.result(claim_draw=True) if self.board.is_game_over(claim_draw=True) else None,
            "num_moves": len(serialized_moves),
            "white_role": self.white_role,
            "black_role": self.black_role,
            "moves": serialized_moves,
            "phases": {
                phase: [self.serialize_move_info(move) for move in moves]
                for phase, moves in self.phase_data.items()
            },
        }

    def save_log(self, logs_dir="logs"):
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(logs_dir, f"game_log_{timestamp}.json")

        with open(path, "w", encoding="utf-8") as log_file:
            json.dump(self.log_data(), log_file, indent=2)

        return path
