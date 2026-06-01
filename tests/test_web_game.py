import unittest

from web_game import WebChessGame


class WebChessGameTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
