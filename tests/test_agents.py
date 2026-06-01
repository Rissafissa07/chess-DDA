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


class MCTSPlayerMaterialRiskTests(unittest.TestCase):
    def setUp(self):
        self.player = MCTSPlayer()
        self.board = chess.Board("rnb1kb1r/pp1ppppp/7n/q1p5/2P5/3PP3/PP1B1PPP/RN1QKBNR b KQkq - 2 4")

    def penalty_for(self, move_uci):
        return self.player._bad_loss_penalty(
            self.board,
            chess.Move.from_uci(move_uci),
        )

    def test_f7f6_receives_queen_scale_penalty_for_bxa5(self):
        self.assertAlmostEqual(self.penalty_for("f7f6"), 0.9)

    def test_g7g5_receives_queen_scale_penalty_for_bxa5(self):
        self.assertAlmostEqual(self.penalty_for("g7g5"), 0.9)

    def test_safe_queen_retreats_receive_no_immediate_material_loss_penalty(self):
        for move_uci in ("a5a6", "a5b6", "a5c7", "a5d8"):
            with self.subTest(move=move_uci):
                self.assertEqual(self.penalty_for(move_uci), 0)

    def test_recapturable_sacrifice_is_penalized_less_than_free_queen_loss(self):
        self.assertLess(self.penalty_for("b8c6"), self.penalty_for("f7f6"))


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
