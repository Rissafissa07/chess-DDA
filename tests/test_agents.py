import unittest
from unittest.mock import patch

import chess

from agents import AdaptiveMCTSPlayer, BestMCTSPlayer, MCTSNode, MCTSPlayer


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


class MCTSPlayerOpeningBonusTests(unittest.TestCase):
    def setUp(self):
        self.player = MCTSPlayer()

    def test_opening_bonus_is_zero_after_fullmove_eight(self):
        board = chess.Board()
        board.fullmove_number = 9

        self.assertEqual(self.player._opening_bonus(board, chess.Move.from_uci("g1f3")), 0)

    def test_developing_knight_scores_above_edge_pawn_move(self):
        board = chess.Board()

        self.assertGreater(
            self.player._opening_bonus(board, chess.Move.from_uci("g1f3")),
            self.player._opening_bonus(board, chess.Move.from_uci("a2a3")),
        )

    def test_centre_pawn_move_receives_bonus(self):
        board = chess.Board()

        self.assertEqual(
            self.player._opening_bonus(board, chess.Move.from_uci("e2e4")),
            self.player.centre_pawn_bonus,
        )

    def test_castling_receives_bonus(self):
        board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")

        self.assertEqual(
            self.player._opening_bonus(board, chess.Move.from_uci("e1g1")),
            self.player.castling_bonus,
        )

    def test_early_queen_move_receives_penalty(self):
        board = chess.Board()
        board.push_uci("e2e4")
        board.push_uci("e7e5")

        self.assertEqual(
            self.player._opening_bonus(board, chess.Move.from_uci("d1h5")),
            -self.player.early_queen_move_penalty,
        )

    def test_repeating_developed_piece_move_receives_penalty(self):
        board = chess.Board()
        board.push_uci("g1f3")
        board.push_uci("g8f6")

        self.assertEqual(
            self.player._opening_bonus(board, chess.Move.from_uci("f3g1")),
            -self.player.repeated_piece_move_penalty,
        )


class MCTSPlayerStaticEvalTests(unittest.TestCase):
    def setUp(self):
        self.player = MCTSPlayer()

    def test_material_advantage_is_positive_and_disadvantage_is_negative(self):
        board = chess.Board("7k/8/8/8/8/8/Q7/7K w - - 0 1")

        self.assertGreater(self.player._static_eval(board, chess.WHITE), 0)
        self.assertLess(self.player._static_eval(board, chess.BLACK), 0)

    def test_static_eval_is_symmetric_between_players(self):
        board = chess.Board("7k/8/8/8/8/8/Q7/7K w - - 0 1")

        self.assertAlmostEqual(
            self.player._static_eval(board, chess.WHITE),
            -self.player._static_eval(board, chess.BLACK),
        )

    def test_terminal_scores_handle_checkmate_and_draw(self):
        checkmate = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        stalemate = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        draw = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")

        self.assertEqual(self.player._static_eval(checkmate, chess.WHITE), 1)
        self.assertEqual(self.player._static_eval(checkmate, chess.BLACK), -1)
        self.assertEqual(self.player._static_eval(stalemate, chess.WHITE), 0)
        self.assertEqual(self.player._static_eval(draw, chess.WHITE), 0)

    def test_rollout_uses_terminal_result_before_static_cutoff(self):
        checkmate = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 0 1")
        self.player.rollout_depth = 30

        with patch.object(self.player, "_static_eval", return_value=-0.5) as static_eval:
            result = self.player.rollout(checkmate)

        self.assertEqual(result, 1)
        static_eval.assert_not_called()

    def test_rollout_stops_at_depth_and_uses_static_cutoff(self):
        board = chess.Board()
        self.player.rollout_depth = 2

        with (
            patch("agents.random.choice", side_effect=lambda moves: moves[0]) as choice,
            patch.object(self.player, "_static_eval", return_value=0.25) as static_eval,
        ):
            result = self.player.rollout(board)

        self.assertEqual(result, 0.25)
        self.assertEqual(choice.call_count, 2)
        static_eval.assert_called_once()

    def test_rollout_static_cutoff_keeps_white_positive_sign_convention(self):
        white_advantage = chess.Board("7k/8/8/8/8/8/Q7/7K w - - 0 1")
        black_advantage = chess.Board("7k/8/q7/8/8/8/8/7K w - - 0 1")
        self.player.rollout_depth = 0

        self.assertGreater(self.player.rollout(white_advantage), 0)
        self.assertLess(self.player.rollout(black_advantage), 0)

    def test_free_queen_capture_ranks_above_quiet_move_with_tied_rollouts(self):
        board = chess.Board("rnb1kb1r/pp1pp1pp/5p1n/q1p5/2P5/3PP3/PP1B1PPP/RN1QKBNR w KQkq - 0 5")
        capture = chess.Move.from_uci("d2a5")
        quiet_move = chess.Move.from_uci("a2a3")
        player = MCTSPlayer(simulations=1)

        def add_tied_children(root):
            for move in (capture, quiet_move):
                child_board = root.board.copy()
                child_board.push(move)
                child = MCTSNode(child_board, parent=root, move=move)
                child.visits = 1
                root.children.append(child)

        player.simulate = add_tied_children

        _, move_values = player.choose_move(board)
        ranked_moves = [move for move, _, _ in move_values]

        self.assertLess(ranked_moves.index(capture), ranked_moves.index(quiet_move))

    def test_mobility_advantage_increases_feature_score(self):
        open_board = chess.Board("7k/8/8/8/8/8/Q7/7K w - - 0 1")
        restricted_board = chess.Board("7k/8/8/8/8/8/P7/7K w - - 0 1")

        self.assertGreater(
            self.player._mobility(open_board, chess.WHITE),
            self.player._mobility(restricted_board, chess.WHITE),
        )

    def test_bishop_pair_adds_bonus(self):
        bishop_pair = chess.Board("7k/8/8/8/8/8/8/2B2B1K w - - 0 1")
        single_bishop = chess.Board("7k/8/8/8/8/8/8/2B4K w - - 0 1")

        self.assertGreater(
            self.player._bishop_pair_score(bishop_pair, chess.WHITE),
            self.player._bishop_pair_score(single_bishop, chess.WHITE),
        )

    def test_doubled_and_isolated_pawns_increase_penalty(self):
        weak_pawns = chess.Board("7k/8/8/8/8/P7/P7/7K w - - 0 1")
        connected_pawns = chess.Board("7k/8/8/8/8/8/PP6/7K w - - 0 1")

        self.assertGreater(
            self.player._pawn_structure_penalty(weak_pawns, chess.WHITE),
            self.player._pawn_structure_penalty(connected_pawns, chess.WHITE),
        )

    def test_advanced_passed_pawn_scores_higher_than_distant_passed_pawn(self):
        advanced_pawn = chess.Board("7k/8/3P4/8/8/8/8/7K w - - 0 1")
        distant_pawn = chess.Board("7k/8/8/8/8/3P4/8/7K w - - 0 1")

        self.assertGreater(
            self.player._passed_pawn_score(advanced_pawn, chess.WHITE),
            self.player._passed_pawn_score(distant_pawn, chess.WHITE),
        )

    def test_blocked_passed_pawn_scores_lower_than_unblocked_passed_pawn(self):
        unblocked_pawn = chess.Board("7k/8/3P4/8/8/8/8/7K w - - 0 1")
        blocked_pawn = chess.Board("7k/3n4/3P4/8/8/8/8/7K w - - 0 1")

        self.assertLess(
            self.player._passed_pawn_score(blocked_pawn, chess.WHITE),
            self.player._passed_pawn_score(unblocked_pawn, chess.WHITE),
        )

    def test_enemy_advanced_passed_pawn_lowers_evaluated_side_score(self):
        quiet_position = chess.Board("7k/8/8/8/8/8/8/7K w - - 0 1")
        enemy_passer = chess.Board("7k/8/8/8/8/8/3p4/7K w - - 0 1")

        self.assertLess(
            self.player._passed_pawn_score(enemy_passer, chess.WHITE),
            self.player._passed_pawn_score(quiet_position, chess.WHITE),
        )

    def test_enemy_queen_pressure_near_king_lowers_score(self):
        safe_king = chess.Board("6k1/8/8/q7/8/8/8/6K1 w - - 0 1")
        pressured_king = chess.Board("6k1/8/2q5/8/8/8/8/6K1 w - - 0 1")

        self.assertLess(
            self.player._king_pressure_score(pressured_king, chess.WHITE),
            self.player._king_pressure_score(safe_king, chess.WHITE),
        )

    def test_reducing_king_pressure_improves_score(self):
        pressured_king = chess.Board("6k1/8/2q5/8/8/8/8/6K1 w - - 0 1")
        reduced_pressure = chess.Board("6k1/8/8/q7/8/8/8/6K1 w - - 0 1")

        self.assertGreater(
            self.player._king_pressure_score(reduced_pressure, chess.WHITE),
            self.player._king_pressure_score(pressured_king, chess.WHITE),
        )

    def test_creating_pressure_around_enemy_king_improves_score(self):
        distant_queen = chess.Board("6k1/8/8/8/Q7/8/8/6K1 w - - 0 1")
        attacking_queen = chess.Board("6k1/8/8/8/8/2Q5/8/6K1 w - - 0 1")

        self.assertGreater(
            self.player._king_pressure_score(attacking_queen, chess.WHITE),
            self.player._king_pressure_score(distant_queen, chess.WHITE),
        )

    def test_direct_checking_pressure_scores_above_distant_attack(self):
        distant_queen = chess.Board("6k1/8/8/8/Q7/8/8/6K1 w - - 0 1")
        checking_queen = chess.Board("6k1/8/8/8/8/1Q6/8/6K1 b - - 0 1")

        self.assertGreater(
            self.player._king_pressure_score(checking_queen, chess.WHITE),
            self.player._king_pressure_score(distant_queen, chess.WHITE),
        )

    def test_random_piece_movement_far_from_king_is_not_rewarded(self):
        rook_on_a3 = chess.Board("6k1/8/8/8/8/R7/8/6K1 w - - 0 1")
        rook_on_b3 = chess.Board("6k1/8/8/8/8/1R6/8/6K1 w - - 0 1")

        self.assertEqual(
            self.player._king_pressure_score(rook_on_a3, chess.WHITE),
            self.player._king_pressure_score(rook_on_b3, chess.WHITE),
        )

    def test_centre_control_increases_feature_score(self):
        central_knight = chess.Board("7k/8/8/8/8/2N5/8/7K w - - 0 1")
        edge_knight = chess.Board("7k/8/8/8/8/N7/8/7K w - - 0 1")

        self.assertGreater(
            self.player._centre_control(central_knight, chess.WHITE),
            self.player._centre_control(edge_knight, chess.WHITE),
        )

    def test_castled_king_increases_king_safety_score(self):
        castled_king = chess.Board("7k/8/8/8/8/8/8/6K1 w - - 0 1")
        exposed_king = chess.Board("7k/8/8/8/8/8/8/4K3 w - - 0 1")

        self.assertGreater(
            self.player._king_safety_score(castled_king, chess.WHITE),
            self.player._king_safety_score(exposed_king, chess.WHITE),
        )

    def test_developed_minor_piece_increases_opening_feature_score(self):
        undeveloped = chess.Board()
        developed = chess.Board()
        developed.push_uci("g1f3")
        developed.push_uci("g8f6")

        self.assertGreater(
            self.player._developed_minor_score(developed, chess.WHITE),
            self.player._developed_minor_score(undeveloped, chess.WHITE),
        )

    def test_attacking_enemy_queen_scores_higher_than_attacking_enemy_pawn(self):
        queen_target = chess.Board("q6k/8/8/8/8/8/8/R6K w - - 0 1")
        pawn_target = chess.Board("7k/p7/8/8/8/8/8/R6K w - - 0 1")

        self.assertGreater(
            self.player._piece_pressure_score(queen_target, chess.WHITE),
            self.player._piece_pressure_score(pawn_target, chess.WHITE),
        )

    def test_attacking_undefended_piece_scores_higher_than_attacking_defended_piece(self):
        undefended_queen = chess.Board("q6k/8/8/8/8/8/8/R6K w - - 0 1")
        defended_queen = chess.Board("qr5k/8/8/8/8/8/8/R6K w - - 0 1")

        self.assertGreater(
            self.player._piece_pressure_score(undefended_queen, chess.WHITE),
            self.player._piece_pressure_score(defended_queen, chess.WHITE),
        )

    def test_own_attacked_piece_lowers_score(self):
        safe_queen = chess.Board("7k/8/8/8/8/8/8/Q6K w - - 0 1")
        attacked_queen = chess.Board("r6k/8/8/8/8/8/8/Q6K w - - 0 1")

        self.assertLess(
            self.player._piece_pressure_score(attacked_queen, chess.WHITE),
            self.player._piece_pressure_score(safe_queen, chess.WHITE),
        )

    def test_own_undefended_attacked_piece_lowers_score_more(self):
        undefended_queen = chess.Board("r6k/8/8/8/8/8/8/Q6K w - - 0 1")
        defended_queen = chess.Board("r6k/8/8/8/8/8/8/QR5K w - - 0 1")

        self.assertLess(
            self.player._piece_pressure_score(undefended_queen, chess.WHITE),
            self.player._piece_pressure_score(defended_queen, chess.WHITE),
        )

    def test_move_creating_queen_attack_ranks_above_quiet_move_with_tied_rollouts(self):
        board = chess.Board("1q5k/8/8/8/8/8/8/R6K w - - 0 1")
        queen_attack = chess.Move.from_uci("a1b1")
        quiet_move = chess.Move.from_uci("a1a2")
        player = MCTSPlayer(simulations=1)
        player._bad_loss_penalty = lambda current_board, move: 0
        player._opening_bonus = lambda current_board, move: 0

        def add_tied_children(root):
            for move in (queen_attack, quiet_move):
                child_board = root.board.copy()
                child_board.push(move)
                child = MCTSNode(child_board, parent=root, move=move)
                child.visits = 1
                root.children.append(child)

        player.simulate = add_tied_children

        _, move_values = player.choose_move(board)
        ranked_moves = [move for move, _, _ in move_values]

        self.assertLess(ranked_moves.index(queen_attack), ranked_moves.index(quiet_move))

    def test_move_blocking_dangerous_passed_pawn_ranks_above_quiet_move_with_tied_rollouts(self):
        board = chess.Board("6k1/7r/3P4/8/8/8/8/6K1 b - - 0 1")
        block_pawn = chess.Move.from_uci("h7d7")
        quiet_move = chess.Move.from_uci("h7h8")
        player = MCTSPlayer(simulations=1)
        player._bad_loss_penalty = lambda current_board, move: 0
        player._opening_bonus = lambda current_board, move: 0

        def add_tied_children(root):
            for move in (block_pawn, quiet_move):
                child_board = root.board.copy()
                child_board.push(move)
                child = MCTSNode(child_board, parent=root, move=move)
                child.visits = 1
                root.children.append(child)

        player.simulate = add_tied_children

        _, move_values = player.choose_move(board)
        ranked_moves = [move for move, _, _ in move_values]

        self.assertLess(ranked_moves.index(block_pawn), ranked_moves.index(quiet_move))


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

    def test_one_early_blunder_does_not_loosen_error_cap_too_much(self):
        player = AdaptiveMCTSPlayer()
        player.player_model.update(0.90)

        self.assertEqual(player._dynamic_error_cap(), player.min_error_cap)

    def test_repeated_poor_moves_increase_error_cap(self):
        player = AdaptiveMCTSPlayer()
        for error in (0.22, 0.24, 0.26, 0.28):
            player.player_model.update(error)

        self.assertGreater(player._dynamic_error_cap(), player.min_error_cap)
        self.assertLessEqual(player._dynamic_error_cap(), player.max_error_cap)

    def test_consistent_low_error_play_keeps_error_cap_strict(self):
        player = AdaptiveMCTSPlayer()
        for error in (0.02, 0.03, 0.02, 0.03):
            player.player_model.update(error)

        self.assertEqual(player._dynamic_error_cap(), player.min_error_cap)

    def test_inconsistent_play_increases_error_cap_but_does_not_exceed_maximum(self):
        player = AdaptiveMCTSPlayer()
        for error in (0.0, 0.60, 0.0, 0.60):
            player.player_model.update(error)

        self.assertEqual(player._dynamic_error_cap(), player.max_error_cap)

    def test_opening_board_keeps_dynamic_error_cap_strict_despite_high_errors(self):
        player = AdaptiveMCTSPlayer()
        for error in (0.22, 0.24, 0.26, 0.28):
            player.player_model.update(error)

        self.assertEqual(player._dynamic_error_cap(chess.Board()), player.min_error_cap)

    def test_middlegame_board_allows_dynamic_error_cap_to_increase(self):
        board = chess.Board()
        board.fullmove_number = 9
        player = AdaptiveMCTSPlayer()
        for error in (0.22, 0.24, 0.26, 0.28):
            player.player_model.update(error)

        self.assertGreater(player._dynamic_error_cap(board), player.min_error_cap)

    def test_strong_player_opening_keeps_dynamic_error_cap_strict(self):
        player = AdaptiveMCTSPlayer()
        for error in (0.02, 0.03, 0.02, 0.03):
            player.player_model.update(error)

        self.assertEqual(player._dynamic_error_cap(chess.Board()), player.min_error_cap)

    def test_opening_candidate_filtering_uses_strict_cap(self):
        player = AdaptiveMCTSPlayer(top_k=5)
        move_values = [
            (chess.Move.from_uci("e2e4"), 1.00, 12),
            (chess.Move.from_uci("d2d4"), 0.92, 11),
            (chess.Move.from_uci("g1f3"), 0.83, 10),
            (chess.Move.from_uci("c2c4"), 0.75, 9),
            (chess.Move.from_uci("b1c3"), 0.70, 8),
        ]
        for error in (0.22, 0.24, 0.26, 0.28):
            player.player_model.update(error)
        player.base_mcts.choose_move = lambda board: (move_values[0][0], move_values)
        player.base_mcts._bad_loss_penalty = lambda board, move: 0

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(player, "_print_adaptive_debug") as print_debug,
        ):
            selected_move, _ = player.choose_move(chess.Board())

        scored_moves = print_debug.call_args.kwargs["scored_moves"]
        scored_candidates = [move for move, _, _, _, _ in scored_moves]

        self.assertEqual(scored_candidates, [move for move, _, _ in move_values[:2]])
        self.assertIn(selected_move, scored_candidates)

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

    def test_candidates_above_error_cap_are_not_sampled(self):
        player = AdaptiveMCTSPlayer(top_k=5)
        move_values = [
            (chess.Move.from_uci("e2e4"), 1.00, 12),
            (chess.Move.from_uci("d2d4"), 0.92, 11),
            (chess.Move.from_uci("g1f3"), 0.83, 10),
            (chess.Move.from_uci("c2c4"), 0.65, 9),
        ]
        player.base_mcts.choose_move = lambda board: (move_values[0][0], move_values)

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(player, "_print_adaptive_debug") as print_debug,
        ):
            selected_move, _ = player.choose_move(chess.Board())

        scored_moves = print_debug.call_args.kwargs["scored_moves"]
        scored_candidates = [move for move, _, _, _, _ in scored_moves]

        self.assertEqual(scored_candidates, [move for move, _, _ in move_values[:2]])
        self.assertIn(selected_move, scored_candidates)

    def test_error_cap_fallback_keeps_best_remaining_candidate_if_all_exceed_cap(self):
        player = AdaptiveMCTSPlayer(top_k=3)
        move_values = [
            (chess.Move.from_uci("e2e4"), 1.00, 12),
            (chess.Move.from_uci("d2d4"), 0.70, 11),
            (chess.Move.from_uci("g1f3"), 0.60, 10),
        ]
        player.base_mcts.choose_move = lambda board: (move_values[0][0], move_values)
        player.base_mcts._bad_loss_penalty = (
            lambda board, move: 0.9 if move == move_values[0][0] else 0
        )

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(player, "_print_adaptive_debug") as print_debug,
        ):
            selected_move, _ = player.choose_move(chess.Board())

        scored_moves = print_debug.call_args.kwargs["scored_moves"]
        scored_candidates = [move for move, _, _, _, _ in scored_moves]

        self.assertEqual(scored_candidates, [move_values[1][0]])
        self.assertEqual(selected_move, move_values[1][0])

    def test_h4_queen_hanging_move_is_severe_and_queen_retreats_are_safe(self):
        board = chess.Board("rnb1k1nr/1ppp1ppp/8/p1b1P3/P6q/2N1P1P1/1PPBQP1P/R3KBNR b KQkq - 0 8")
        player = AdaptiveMCTSPlayer()
        threshold = player.severe_material_risk_threshold

        self.assertGreaterEqual(
            player.base_mcts._bad_loss_penalty(board, chess.Move.from_uci("g8e7")),
            threshold,
        )
        for move_uci in ("h4d8", "h4e7", "h4g5", "h4b4"):
            with self.subTest(move=move_uci):
                self.assertLess(
                    player.base_mcts._bad_loss_penalty(board, chess.Move.from_uci(move_uci)),
                    threshold,
                )

    def test_severe_candidate_is_not_sampled_when_safe_candidates_exist(self):
        board = chess.Board("rnb1k1nr/1ppp1ppp/8/p1b1P3/P6q/2N1P1P1/1PPBQP1P/R3KBNR b KQkq - 0 8")
        player = AdaptiveMCTSPlayer(top_k=5)
        move_values = [
            (chess.Move.from_uci("h4d8"), 0.0, 2),
            (chess.Move.from_uci("h4e7"), 0.0, 2),
            (chess.Move.from_uci("h4g5"), 0.0, 2),
            (chess.Move.from_uci("h4b4"), 0.0, 2),
            (chess.Move.from_uci("g8e7"), -0.466667, 3),
        ]
        player.base_mcts.choose_move = lambda current_board: (move_values[0][0], move_values)

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(player, "_print_adaptive_debug") as print_debug,
        ):
            selected_move, _ = player.choose_move(board)

        scored_moves = print_debug.call_args.kwargs["scored_moves"]
        scored_candidates = [move for move, _, _, _, _ in scored_moves]

        self.assertNotIn(chess.Move.from_uci("g8e7"), scored_candidates)
        self.assertNotEqual(selected_move, chess.Move.from_uci("g8e7"))

    def test_all_severe_candidates_fall_back_to_original_top_k(self):
        player = AdaptiveMCTSPlayer(top_k=3)
        move_values = self.move_values[:3]
        player.base_mcts.choose_move = lambda board: (move_values[0][0], move_values)
        player.base_mcts._bad_loss_penalty = lambda board, move: 0.9

        with (
            patch("agents.random.random", return_value=0.999999),
            patch.object(player, "_print_adaptive_debug") as print_debug,
        ):
            selected_move, _ = player.choose_move(chess.Board())

        scored_moves = print_debug.call_args.kwargs["scored_moves"]
        scored_candidates = [move for move, _, _, _, _ in scored_moves]

        self.assertEqual(scored_candidates, [move for move, _, _ in move_values])
        self.assertEqual(selected_move, move_values[-1][0])


if __name__ == "__main__":
    unittest.main()
