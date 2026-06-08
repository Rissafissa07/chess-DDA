import unittest
from unittest.mock import patch

import chess

from web_game import WebChessGame


class WebChessGameTests(unittest.TestCase):
    def replay_log(self):
        return {
            "white_role": "human",
            "black_role": "adaptive_mcts",
            "moves": [
                {
                    "color": "white",
                    "role": "human",
                    "agent_type": "Human",
                    "move": "e2e4",
                    "phase": "opening",
                    "move_values": None,
                    "move_error": 0.2,
                },
                {
                    "color": "black",
                    "role": "adaptive_mcts",
                    "agent_type": "AdaptiveMCTSPlayer",
                    "move": "e7e5",
                    "phase": "opening",
                    "move_values": None,
                    "move_error": None,
                },
                {
                    "color": "white",
                    "role": "human",
                    "agent_type": "Human",
                    "move": "g1f3",
                    "phase": "opening",
                    "move_values": None,
                    "move_error": 0.1,
                },
            ],
        }

    def test_adaptive_role_is_separate_from_color(self):
        game = WebChessGame(human_color="white", opponent_type="adaptive_mcts", simulations=1)

        self.assertEqual(game.white_role, "human")
        self.assertEqual(game.black_role, "adaptive_mcts")

    def test_best_mcts_role_is_logged_separately_from_color(self):
        game = WebChessGame(human_color="black", opponent_type="best_mcts", simulations=1)
        first_move = game.log_data()["moves"][0]

        self.assertEqual(game.white_role, "best_mcts")
        self.assertEqual(game.black_role, "human")
        self.assertEqual(first_move["color"], "white")
        self.assertEqual(first_move["role"], "best_mcts")
        self.assertEqual(first_move["agent_type"], "BestMCTSPlayer")

    def test_adaptive_move_log_includes_decision_fields(self):
        game = WebChessGame(human_color="white", opponent_type="adaptive_mcts", simulations=1)
        move_values = [
            (chess.Move.from_uci("g8f6"), 1.00, 12),
            (chess.Move.from_uci("d7d5"), 0.92, 10),
            (chess.Move.from_uci("e7e5"), 0.60, 8),
        ]
        game.adaptive_player.base_mcts.choose_move = (
            lambda board: (move_values[0][0], move_values)
        )
        game.adaptive_player.base_mcts._bad_loss_penalty = lambda board, move: 0

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(game.adaptive_player, "_print_adaptive_debug"),
        ):
            game.play_human_move("e2e4")

        adaptive_move = game.log_data()["moves"][-1]
        expected_fields = {
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
        }

        self.assertEqual(adaptive_move["role"], "adaptive_mcts")
        self.assertTrue(expected_fields.issubset(adaptive_move.keys()))

    def test_adaptive_move_log_records_error_rank_and_cap_counts(self):
        game = WebChessGame(human_color="white", opponent_type="adaptive_mcts", simulations=1)
        move_values = [
            (chess.Move.from_uci("g8f6"), 1.00, 12),
            (chess.Move.from_uci("d7d5"), 0.92, 10),
            (chess.Move.from_uci("e7e5"), 0.60, 8),
        ]
        game.adaptive_player.base_mcts.choose_move = (
            lambda board: (move_values[0][0], move_values)
        )
        game.adaptive_player.base_mcts._bad_loss_penalty = lambda board, move: 0

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(game.adaptive_player, "_print_adaptive_debug"),
        ):
            game.play_human_move("e2e4")

        adaptive_move = game.log_data()["moves"][-1]

        self.assertEqual(adaptive_move["move"], "d7d5")
        self.assertEqual(adaptive_move["selected_move_rank"], 2)
        self.assertEqual(adaptive_move["best_move_value"], 1.00)
        self.assertEqual(adaptive_move["selected_move_value"], 0.92)
        self.assertAlmostEqual(
            adaptive_move["selected_move_error"],
            adaptive_move["best_move_value"] - adaptive_move["selected_move_value"],
        )
        self.assertLessEqual(
            adaptive_move["candidate_count_after_cap"],
            adaptive_move["candidate_count"],
        )

    def test_replay_reconstructs_board_state(self):
        game = WebChessGame.from_replay_log(
            self.replay_log(),
            replay_until_ply=2,
            replay_source="game-one.json",
            simulations=1,
        )
        expected_board = chess.Board()
        expected_board.push_uci("e2e4")
        expected_board.push_uci("e7e5")

        self.assertEqual(game.board.fen(), expected_board.fen())
        self.assertEqual(game.current_role(), "human")
        self.assertEqual(game.white_role, "human")
        self.assertEqual(game.black_role, "adaptive_mcts")

    def test_replay_restores_human_move_errors(self):
        game = WebChessGame.from_replay_log(
            self.replay_log(),
            replay_until_ply=2,
            replay_source="game-one.json",
            simulations=1,
        )

        self.assertEqual(game.adaptive_player.player_model.errors, [0.2])

    def test_replay_rejects_bot_turn_replay_point(self):
        with self.assertRaisesRegex(ValueError, "human player's turn"):
            WebChessGame.from_replay_log(
                self.replay_log(),
                replay_until_ply=1,
                replay_source="game-one.json",
                simulations=1,
            )

    def test_replay_log_includes_experiment_metadata(self):
        game = WebChessGame.from_replay_log(
            self.replay_log(),
            replay_until_ply=2,
            replay_source="game-one.json",
            simulations=1,
        )
        log_data = game.log_data()

        self.assertEqual(log_data["mode"], "replay_experiment")
        self.assertEqual(log_data["replay_source"], "game-one.json")
        self.assertEqual(log_data["replay_until_ply"], 2)
        self.assertEqual(log_data["replay_start_fen"], game.board.fen())


if __name__ == "__main__":
    unittest.main()
