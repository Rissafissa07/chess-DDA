import json
import os
from datetime import datetime

import chess

from agents import AdaptiveMCTSPlayer, BestMCTSPlayer, find_move_error


adaptive_log_fields = (
    "selected_move_rank",
    "selected_move_value",
    "best_move_value",
    "selected_move_error",
    "target_error",
    "temperature",
    "dynamic_error_cap",
    "candidate_count",
    "candidate_count_after_cap",
    "chosen_move_passed_cap",
    "player_avg_error",
    "player_recent_error",
    "player_consistency",
)


class WebChessGame:
    def __init__(
        self,
        human_color="white",
        opponent_type="adaptive_mcts",
        simulations=100,
        autoplay=True,
        mode="normal",
        replay_source=None,
        replay_until_ply=None,
        replay_start_fen=None,
    ):
        if human_color not in ("white", "black"):
            raise ValueError("human_color must be 'white' or 'black'")
        if opponent_type not in ("adaptive_mcts", "best_mcts"):
            raise ValueError("opponent_type must be 'adaptive_mcts' or 'best_mcts'")

        self.board = chess.Board()
        self.opponent_role = opponent_type
        if opponent_type == "adaptive_mcts":
            self.opponent_player = AdaptiveMCTSPlayer(simulations=simulations)
            self.adaptive_player = self.opponent_player
            self.evaluation_mcts = self.adaptive_player.base_mcts
        else:
            self.opponent_player = BestMCTSPlayer(simulations=simulations)
            self.adaptive_player = None
            self.evaluation_mcts = self.opponent_player

        self.white_role = "human" if human_color == "white" else opponent_type
        self.black_role = "human" if human_color == "black" else opponent_type
        self.move_history = []
        self.phase_data = {
            "opening": [],
            "middlegame": [],
            "endgame": [],
        }
        self.mode = mode
        self.replay_source = replay_source
        self.replay_until_ply = replay_until_ply
        self.replay_start_fen = replay_start_fen

        if autoplay and self.current_role() == self.opponent_role:
            self.play_opponent_move()

    @classmethod
    def from_replay_log(
        cls,
        log_data,
        replay_until_ply,
        replay_source=None,
        simulations=100,
    ):
        moves = log_data.get("moves", [])
        if replay_until_ply < 0 or replay_until_ply > len(moves):
            raise ValueError("replay_until_ply must be between 0 and the number of logged moves.")

        white_role = log_data.get("white_role")
        black_role = log_data.get("black_role")
        if white_role == "human" and black_role in ("adaptive_mcts", "best_mcts"):
            human_color = "white"
            opponent_type = black_role
        elif black_role == "human" and white_role in ("adaptive_mcts", "best_mcts"):
            human_color = "black"
            opponent_type = white_role
        else:
            raise ValueError("Replay log must contain one human role and one supported opponent role.")

        game = cls(
            human_color=human_color,
            opponent_type=opponent_type,
            simulations=simulations,
            autoplay=False,
            mode="replay_experiment",
            replay_source=replay_source,
            replay_until_ply=replay_until_ply,
        )

        for move_info in moves[:replay_until_ply]:
            game.push_replayed_move(move_info)
            if (
                game.adaptive_player is not None
                and move_info.get("role") == "human"
                and move_info.get("move_error") is not None
            ):
                game.adaptive_player.player_model.update(move_info["move_error"])

        game.replay_start_fen = game.board.fen()
        if game.current_role() != "human":
            raise ValueError("Replay point must end on the human player's turn.")

        return game

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

        _, move_values = self.evaluation_mcts.choose_move(self.board.copy())
        move_error = find_move_error(move, move_values)
        if self.adaptive_player is not None:
            self.adaptive_player.player_model.update(move_error)

        self.push_logged_move(
            move=move,
            role="human",
            agent_type="Human",
            move_values=move_values,
            move_error=move_error,
        )

        if not self.board.is_game_over(claim_draw=True) and self.current_role() == self.opponent_role:
            self.play_opponent_move()

    def play_opponent_move(self):
        if self.board.is_game_over(claim_draw=True):
            return
        if self.current_role() != self.opponent_role:
            return

        result = self.opponent_player.choose_move(self.board.copy())
        if isinstance(result, tuple):
            move, move_values = result
        else:
            move = result
            move_values = None

        self.push_logged_move(
            move=move,
            role=self.opponent_role,
            agent_type=self.opponent_player.__class__.__name__,
            move_values=move_values,
            move_error=None,
            adaptive_decision_info=(
                self.adaptive_player.last_decision_info
                if self.opponent_role == "adaptive_mcts"
                else None
            ),
        )

    def play_adaptive_move(self):
        if self.opponent_role == "adaptive_mcts":
            self.play_opponent_move()

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

    def push_logged_move(
        self,
        move,
        role,
        agent_type,
        move_values,
        move_error,
        adaptive_decision_info=None,
    ):
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
        if role == "adaptive_mcts" and adaptive_decision_info is not None:
            move_info.update(adaptive_decision_info)

        self.board.push(move)
        self.move_history.append(move_info)
        self.phase_data[phase].append(move_info)

    def push_replayed_move(self, move_info):
        try:
            move = chess.Move.from_uci(move_info["move"])
        except (KeyError, ValueError) as error:
            raise ValueError("Replay log contains an invalid move.") from error

        if move not in self.board.legal_moves:
            raise ValueError("Replay log contains a move that is illegal in sequence.")

        phase = move_info.get("phase", self.phase_for_current_move())
        replayed_move_info = {
            "color": move_info.get("color", self.current_color()),
            "role": move_info.get("role", self.current_role()),
            "agent_type": move_info.get("agent_type", "Unknown"),
            "move": move,
            "phase": phase,
            "move_values": self.deserialize_move_values(move_info.get("move_values")),
            "move_error": move_info.get("move_error"),
        }
        for field in adaptive_log_fields:
            if field in move_info:
                replayed_move_info[field] = move_info[field]

        self.board.push(move)
        self.move_history.append(replayed_move_info)
        self.phase_data.setdefault(phase, []).append(replayed_move_info)

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
        serialized_info = {
            "color": move_info["color"],
            "role": move_info["role"],
            "agent_type": move_info["agent_type"],
            "move": move_info["move"].uci(),
            "phase": move_info["phase"],
            "move_values": self.serialize_move_values(move_info["move_values"]),
            "move_error": move_info["move_error"],
        }
        for field in adaptive_log_fields:
            if field in move_info:
                serialized_info[field] = move_info[field]
        return serialized_info

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

    def deserialize_move_values(self, move_values):
        if move_values is None:
            return None
        deserialized_values = []
        for move_value in move_values:
            if isinstance(move_value, dict):
                move = move_value["move"]
                value = move_value["value"]
                visits = move_value["visits"]
            else:
                move, value, visits = move_value
            deserialized_values.append((chess.Move.from_uci(move), value, visits))
        return deserialized_values

    def log_data(self):
        serialized_moves = [self.serialize_move_info(move) for move in self.move_history]
        data = {
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
        if self.mode != "normal":
            data.update({
                "mode": self.mode,
                "replay_source": self.replay_source,
                "replay_until_ply": self.replay_until_ply,
                "replay_start_fen": self.replay_start_fen,
            })
        return data

    def save_log(self, logs_dir="logs"):
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(logs_dir, f"game_log_{timestamp}.json")

        with open(path, "w", encoding="utf-8") as log_file:
            json.dump(self.log_data(), log_file, indent=2)

        return path
