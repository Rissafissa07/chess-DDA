import unittest
from unittest.mock import patch

import chess

from agents import AdaptiveMCTSPlayer, BestMCTSPlayer, MCTSPlayer


class BestMCTSPlayerTests(unittest.TestCase):
    def test_choose_move_returns_first_move_value(self):
        move_values = [
            (chess.Move.from_uci("e2e4"), 0.75, 12),
            (chess.Move.from_uci("d2d4"), 0.50, 8),
        ]

        with patch.object(MCTSPlayer, "choose_move", return_value=(move_values[1][0], move_values)):
            chosen_move, returned_move_values = BestMCTSPlayer().choose_move(chess.Board())

        self.assertEqual(chosen_move, move_values[0][0])
        self.assertIs(returned_move_values, move_values)


class AdaptiveMCTSPlayerTests(unittest.TestCase):
    def setUp(self):
        self.move_values = [
            (chess.Move.from_uci("e2e4"), 0.75, 12),
            (chess.Move.from_uci("d2d4"), 0.70, 11),
            (chess.Move.from_uci("g1f3"), 0.65, 10),
            (chess.Move.from_uci("c2c4"), 0.60, 9),
            (chess.Move.from_uci("b1c3"), 0.55, 8),
            (chess.Move.from_uci("e2e3"), 0.50, 7),
        ]

    def test_default_top_k_is_five(self):
        self.assertEqual(AdaptiveMCTSPlayer().top_k, 5)

    def test_choose_move_only_scores_move_values_top_k_slice(self):
        player = AdaptiveMCTSPlayer(top_k=3)
        player.base_mcts.choose_move = lambda board: (self.move_values[0][0], self.move_values)

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(player, "_print_adaptive_debug") as print_debug,
        ):
            selected_move, returned_move_values = player.choose_move(chess.Board())

        scored_moves = print_debug.call_args.kwargs["scored_moves"]
        scored_candidates = [move for move, _, _, _, _ in scored_moves]

        self.assertEqual(scored_candidates, [move for move, _, _ in self.move_values[:3]])
        self.assertIn(selected_move, scored_candidates)
        self.assertIs(returned_move_values, self.move_values)


if __name__ == "__main__":
    unittest.main()
