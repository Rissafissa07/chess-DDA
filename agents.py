import chess
import random
import math


class RandomPlayer:
    def choose_move(self, board):
        # Selects any legal move with equal probability.
        return random.choice(list(board.legal_moves))

class PlayerModel:
    # Stores observed human move errors for adaptive strength matching.
    def __init__(self):
        self.errors = []

    def update(self, error):
        # Adds one observed player error when available.
        if error is not None:
            self.errors.append(error)

    def average_error(self):
        # Returns neutral error before observations exist.
        if len(self.errors) == 0:
            return 0

        return sum(self.errors) / len(self.errors)

    def consistency(self):
        # Measures variation in the player's observed errors.
        if len(self.errors) < 2:
            return 0

        # Uses standard deviation as the consistency estimate.
        avg = self.average_error()
        squared_differences = [(error - avg) ** 2 for error in self.errors]
        variance = sum(squared_differences) / len(squared_differences)

        return math.sqrt(variance)

    def blunder_rate(self, threshold=0.5):
        # Counts how often errors exceed the blunder threshold.
        if len(self.errors) == 0:
            return 0

        blunders = [error for error in self.errors if error >= threshold]
        return len(blunders) / len(self.errors)

def find_move_error(chosen_move, move_values):
    # Calculates the value gap between the best move and the chosen move.
    if move_values is None or len(move_values) == 0:
        return None

    # Uses sorted move values, where the first move is the best candidate.
    best_value = move_values[0][1]
    chosen_value = None

    for move, value, visits in move_values:
        if move == chosen_move:
            chosen_value = value
            break

    if chosen_value is None:
        return None

    return best_value - chosen_value

class MCTSNode:
    # Represents one searched position in the MCTS tree.
    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.wins = 0

    def uct_score(self, c=1.4):
        # Balances explored strong nodes with less explored nodes.
        if self.visits == 0: 
            return float("inf")
        return (self.wins / self.visits) + c * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )


class MCTSPlayer:
    # Provides the base MCTS search plus root-level chess evaluation.
    # Uses simple piece values for immediate material-risk checks.
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }

    # Uses slightly tuned values for positional static evaluation.
    static_piece_values = {
        chess.PAWN: 1.0,
        chess.KNIGHT: 3.2,
        chess.BISHOP: 3.3,
        chess.ROOK: 5.0,
        chess.QUEEN: 9.0,
    }

    # Controls how strongly each evaluation layer affects ranking.
    material_risk_weight = 0.1 # Material-loss penalty
    root_static_eval_weight = 0.35 # Root static-eval blend
    static_eval_scale = 6.0 # Static-eval scaling
    mobility_weight = 0.03 # Piece mobility
    centre_control_weight = 0.10 # Centre control
    bishop_pair_bonus = 0.20 # Bishop pair bonus
    castling_rights_bonus = 0.10 # Keep castling rights
    castled_king_bonus = 0.25 # Castled king bonus
    developed_minor_bonus = 0.10 # Developed minor pieces
    doubled_pawn_penalty = 0.12 # Doubled pawns
    isolated_pawn_penalty = 0.10 # Isolated pawns
    passed_pawn_base_bonus = 0.08 # Passed pawn bonus
    passed_pawn_advance_bonus = 0.04 # Advanced passer bonus
    blocked_passed_pawn_multiplier = 0.45 # Blocked passer reduction
    king_pressure_attack_weight = 0.04 # King attack pressure
    king_pressure_near_king_weight = 0.06 # Near-king pressure
    king_pressure_direct_check_weight = 0.12 # Direct check pressure
    own_king_pressure_penalty = 0.06 # Own king pressure
    own_king_direct_check_penalty = 0.12 # Own king in check
    attacked_piece_weight = 0.04 # Attacking enemy pieces
    undefended_attacked_piece_weight = 0.08 # Attacking loose pieces
    own_attacked_piece_penalty = 0.04 # Own attacked pieces
    own_undefended_attacked_piece_penalty = 0.08 # Own loose pieces
    opening_max_fullmove = 8 # Opening phase limit
    develop_minor_bonus = 0.08 # Opening development
    centre_pawn_bonus = 0.06 # Central pawns
    central_minor_bonus = 0.04 # Central minor pieces
    castling_bonus = 0.12 # Opening castling
    early_queen_move_penalty = 0.10 # Early queen moves
    repeated_piece_move_penalty = 0.06 # Repeated opening moves
    rollout_depth = 30 # Rollout cutoff depth

    def __init__(self, simulations=200):
        # Sets the search budget used for each move choice.
        self.simulations = simulations

    def choose_move(self, board):
        # Builds a search tree from the current board position.
        root = MCTSNode(board.copy())

        # Runs repeated MCTS simulations from the root.
        for _ in range(self.simulations):
            self.simulate(root)

        # Falls back when no searchable child was created.
        if not root.children:
            return random.choice(list(board.legal_moves))

        # Keeps the raw MCTS best child available for comparison.
        best_child = max(
            root.children,
            key=lambda c: (c.wins / c.visits) if c.visits > 0 else float("-inf")
        )
        
        move_values = []

        # Combines rollout value, static evaluation, safety, and opening bias.
        for child in root.children:
            if child.visits > 0:
                # Uses average simulated result as the MCTS value.
                mcts_value = child.wins / child.visits
                bad_loss_penalty = self._bad_loss_penalty(board, child.move)
                opening_bonus = self._opening_bonus(board, child.move)
                candidate_board = board.copy()
                candidate_board.push(child.move)
                static_value = self._static_eval(candidate_board, board.turn)
                value = (
                    mcts_value
                    + self.root_static_eval_weight * static_value
                    - bad_loss_penalty
                    + opening_bonus
                )
            else:
                continue  # Skip unvisited nodes

            move_values.append((child.move, value, child.visits))

        # Sorts candidates from strongest to weakest.
        move_values.sort(key=lambda x: x[1], reverse=True)

        # Prints the top candidates for analysis during playtests.
        print("\nMove evaluations:")
        for move, value, visits in move_values[:5]:
            print(f"{move} -> value={value:.3f}, visits={visits}")

        # Returns the top-ranked move plus all ranked candidates.
        best_move = move_values[0][0]
        return best_move, move_values

    def _material_balance(self, board, color):
        # Calculates simple material balance for one side.
        own_material = sum(
            len(board.pieces(piece_type, color)) * value
            for piece_type, value in self.piece_values.items()
        )
        opponent_material = sum(
            len(board.pieces(piece_type, not color)) * value
            for piece_type, value in self.piece_values.items()
        )
        return own_material - opponent_material

    def _best_immediate_compensation(self, board, color):
        # Finds the best immediate reply after a material loss.
        best_gain = 0
        starting_balance = self._material_balance(board, color)

        for move in board.legal_moves:
            response_board = board.copy()
            response_board.push(move)

            if response_board.is_checkmate():
                return float("inf")

            material_gain = self._material_balance(response_board, color) - starting_balance
            best_gain = max(best_gain, material_gain)

        return best_gain

    def _bad_loss_penalty(self, board, candidate_move):
        # Penalizes moves that allow large uncompensated material loss.
        root_player = board.turn
        starting_balance = self._material_balance(board, root_player)
        candidate_board = board.copy()
        candidate_board.push(candidate_move)

        if candidate_board.is_checkmate():
            return 0

        # Credits material won by the candidate before checking replies.
        candidate_gain = max(
            0,
            self._material_balance(candidate_board, root_player) - starting_balance,
        )
        worst_uncompensated_loss = 0

        # Checks each opponent reply for immediate tactical punishment.
        for reply in candidate_board.legal_moves:
            reply_board = candidate_board.copy()
            reply_board.push(reply)

            immediate_loss = (
                self._material_balance(candidate_board, root_player)
                - self._material_balance(reply_board, root_player)
            )
            if immediate_loss <= 0:
                continue

            # Allows tactics if the loss can be immediately compensated.
            compensation = self._best_immediate_compensation(reply_board, root_player)
            uncompensated_loss = max(0, immediate_loss - candidate_gain - compensation)
            worst_uncompensated_loss = max(worst_uncompensated_loss, uncompensated_loss)

        return self.material_risk_weight * worst_uncompensated_loss

    def _opening_bonus(self, board, candidate_move):
        # Applies small opening-principle nudges at the root only.
        if board.fullmove_number > self.opening_max_fullmove:
            return 0

        piece = board.piece_at(candidate_move.from_square)
        if piece is None:
            return 0

        bonus = 0
        starting_rank = 0 if piece.color == chess.WHITE else 7
        central_pawn_squares = {chess.D4, chess.E4, chess.D5, chess.E5}
        central_knight_squares = {chess.C3, chess.F3, chess.C6, chess.F6}

        # Rewards first-time development of knights and bishops.
        if (
            piece.piece_type in (chess.KNIGHT, chess.BISHOP)
            and chess.square_rank(candidate_move.from_square) == starting_rank
        ):
            bonus += self.develop_minor_bonus

        # Rewards early central pawn control.
        if piece.piece_type == chess.PAWN and candidate_move.to_square in central_pawn_squares:
            bonus += self.centre_pawn_bonus

        # Rewards common central knight development squares.
        if piece.piece_type == chess.KNIGHT and candidate_move.to_square in central_knight_squares:
            bonus += self.central_minor_bonus

        # Rewards castling as an opening safety improvement.
        if board.is_castling(candidate_move):
            bonus += self.castling_bonus

        # Discourages early queen wandering in the opening.
        if piece.piece_type == chess.QUEEN:
            bonus -= self.early_queen_move_penalty

        if (
            len(board.move_stack) >= 2
            and candidate_move.from_square == board.move_stack[-2].to_square
        ):
            # Discourages moving the same piece twice in the opening.
            bonus -= self.repeated_piece_move_penalty

        return bonus

    def _static_eval(self, board, root_player):
        # Converts the positional score difference into a bounded value.
        if board.is_checkmate():
            return 1 if board.turn != root_player else -1
        if board.is_game_over(claim_draw=True):
            return 0

        root_score = self._static_score_for_color(board, root_player)
        opponent_score = self._static_score_for_color(board, not root_player)
        return math.tanh((root_score - opponent_score) / self.static_eval_scale)

    def _static_score_for_color(self, board, color):
        # Combines lightweight chess features for one side.
        return (
            self._static_material(board, color)
            + self.mobility_weight * self._mobility(board, color)
            + self.centre_control_weight * self._centre_control(board, color)
            + self._bishop_pair_score(board, color)
            + self._king_safety_score(board, color)
            + self._developed_minor_score(board, color)
            + self._piece_pressure_score(board, color)
            + self._passed_pawn_score(board, color)
            + self._king_pressure_score(board, color)
            - self._pawn_structure_penalty(board, color)
        )

    def _static_material(self, board, color):
        # Scores material using tuned static piece values.
        return sum(
            len(board.pieces(piece_type, color)) * value
            for piece_type, value in self.static_piece_values.items()
        )

    def _mobility(self, board, color):
        # Counts legal moves available to the given side.
        mobility_board = board.copy(stack=False)
        mobility_board.turn = color
        return mobility_board.legal_moves.count()

    def _centre_control(self, board, color):
        # Counts attacked central squares.
        central_squares = (chess.D4, chess.E4, chess.D5, chess.E5)
        return sum(bool(board.attackers(color, square)) for square in central_squares)

    def _bishop_pair_score(self, board, color):
        # Rewards keeping both bishops.
        if len(board.pieces(chess.BISHOP, color)) >= 2:
            return self.bishop_pair_bonus
        return 0

    def _king_safety_score(self, board, color):
        # Rewards castling rights and already castled king positions.
        king_square = board.king(color)
        castled_squares = (
            {chess.G1, chess.C1}
            if color == chess.WHITE
            else {chess.G8, chess.C8}
        )

        score = 0

        # Rewards the king being on common castled squares.
        if king_square in castled_squares:
            score += self.castled_king_bonus

        # Rewards retaining either castling option.
        if board.has_kingside_castling_rights(color):
            score += self.castling_rights_bonus
        if board.has_queenside_castling_rights(color):
            score += self.castling_rights_bonus
        return score

    def _developed_minor_score(self, board, color):
        # Rewards opening development of knights and bishops.
        if board.fullmove_number > self.opening_max_fullmove:
            return 0

        starting_squares = (
            (chess.B1, chess.G1, chess.C1, chess.F1)
            if color == chess.WHITE
            else (chess.B8, chess.G8, chess.C8, chess.F8)
        )
        undeveloped_minors = sum(
            board.piece_type_at(square) in (chess.KNIGHT, chess.BISHOP)
            and board.color_at(square) == color
            for square in starting_squares
        )
        developed_minors = 4 - undeveloped_minors
        return self.developed_minor_bonus * developed_minors

    def _pawn_structure_penalty(self, board, color):
        # Penalizes doubled and isolated pawns.
        pawns_by_file = [
            len(board.pieces(chess.PAWN, color) & chess.BB_FILES[file_index])
            for file_index in range(8)
        ]
        doubled_pawns = sum(max(0, pawn_count - 1) for pawn_count in pawns_by_file)
        isolated_pawns = sum(
            pawn_count
            for file_index, pawn_count in enumerate(pawns_by_file)
            if pawn_count > 0
            and (file_index == 0 or pawns_by_file[file_index - 1] == 0)
            and (file_index == 7 or pawns_by_file[file_index + 1] == 0)
        )
        return (
            self.doubled_pawn_penalty * doubled_pawns
            + self.isolated_pawn_penalty * isolated_pawns
        )

    def _passed_pawn_score(self, board, color):
        # Rewards own passed pawns and penalizes enemy passed pawns.
        def passed_pawn_value(square, pawn_color):
            # Gives more value to advanced passed pawns.
            rank = chess.square_rank(square)
            file_index = chess.square_file(square)
            if pawn_color == chess.WHITE:
                advancement = rank - 1
                front_rank = rank + 1
            else:
                advancement = 6 - rank
                front_rank = rank - 1

            advancement = max(0, min(5, advancement))
            value = (
                self.passed_pawn_base_bonus
                + self.passed_pawn_advance_bonus * advancement
            )

            if 0 <= front_rank <= 7:
                front_square = chess.square(file_index, front_rank)
                if board.piece_at(front_square) is not None:
                    # Reduces value when the passer is blocked.
                    value *= self.blocked_passed_pawn_multiplier

            return value

        own_score = sum(
            passed_pawn_value(square, color)
            for square in board.pieces(chess.PAWN, color)
            if self._is_passed_pawn(board, square, color)
        )
        enemy_score = sum(
            passed_pawn_value(square, not color)
            for square in board.pieces(chess.PAWN, not color)
            if self._is_passed_pawn(board, square, not color)
        )
        return own_score - enemy_score

    def _is_passed_pawn(self, board, square, color):
        # Checks for enemy pawns ahead on the same or adjacent files.
        file_index = chess.square_file(square)
        rank = chess.square_rank(square)
        adjacent_files = range(max(0, file_index - 1), min(7, file_index + 1) + 1)

        for enemy_square in board.pieces(chess.PAWN, not color):
            # Ignores enemy pawns too far away to stop the passer.
            enemy_file = chess.square_file(enemy_square)
            if enemy_file not in adjacent_files:
                continue

            enemy_rank = chess.square_rank(enemy_square)

            # Blocks White passers with enemy pawns ahead.
            if color == chess.WHITE and enemy_rank > rank:
                return False

            # Blocks Black passers with enemy pawns ahead.
            if color == chess.BLACK and enemy_rank < rank:
                return False

        return True

    def _king_pressure_score(self, board, color):
        # Rewards pressure on the enemy king and penalizes own king pressure.
        attacking_score = self._pressure_against_king(
            board,
            king_color=not color,
            attacking_color=color,
            pressure_weight=self.king_pressure_attack_weight,
            direct_check_weight=self.king_pressure_direct_check_weight,
        )
        defensive_penalty = self._pressure_against_king(
            board,
            king_color=color,
            attacking_color=not color,
            pressure_weight=self.own_king_pressure_penalty,
            direct_check_weight=self.own_king_direct_check_penalty,
        )
        return attacking_score - defensive_penalty

    def _pressure_against_king(
        self,
        board,
        king_color,
        attacking_color,
        pressure_weight,
        direct_check_weight,
    ):
        # Scores attacks on squares around a king.
        king_square = board.king(king_color)
        if king_square is None:
            return 0

        pressure_piece_weights = {
            chess.KNIGHT: 1.0,
            chess.BISHOP: 1.0,
            chess.ROOK: 1.2,
            chess.QUEEN: 1.5,
        }

        # Uses the eight squares around the king as the danger zone.
        king_zone = chess.SquareSet(chess.BB_KING_ATTACKS[king_square])
        pressure_score = 0
        unique_attackers = set()

        # Counts attacks into the king's surrounding zone.
        for target_square in king_zone:
            for attacker_square in board.attackers(attacking_color, target_square):
                piece = board.piece_at(attacker_square)
                if piece is None or piece.piece_type not in pressure_piece_weights:
                    continue

                unique_attackers.add(attacker_square)
                pressure_score += pressure_weight * pressure_piece_weights[piece.piece_type]

        # Adds extra weight for direct attacks on the king square.
        for attacker_square in board.attackers(attacking_color, king_square):
            piece = board.piece_at(attacker_square)
            if piece is None or piece.piece_type not in pressure_piece_weights:
                continue

            unique_attackers.add(attacker_square)
            pressure_score += direct_check_weight * pressure_piece_weights[piece.piece_type]

        # Rewards coordinated pressure from multiple attackers.
        if len(unique_attackers) > 1:
            pressure_score += self.king_pressure_near_king_weight * (len(unique_attackers) - 1)

        return pressure_score

    def _piece_pressure_score(self, board, color):
        # Scores attacks on enemy pieces and danger to own pieces.
        score = 0
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.KING:
                continue

            piece_value = self.static_piece_values[piece.piece_type]
            attacked_by_color = bool(board.attackers(color, square))
            attacked_by_opponent = bool(board.attackers(not color, square))
            defended = bool(board.attackers(piece.color, square))

            # Rewards attacks, especially against undefended pieces.
            if piece.color != color and attacked_by_color:
                score += self.attacked_piece_weight * piece_value
                if not defended:
                    score += self.undefended_attacked_piece_weight * piece_value

            # Penalizes own pieces that are attacked or loose.
            if piece.color == color and attacked_by_opponent:
                score -= self.own_attacked_piece_penalty * piece_value
                if not defended:
                    score -= self.own_undefended_attacked_piece_penalty * piece_value

        return score

    def simulate(self, node):
        # Performs one full MCTS iteration.
        current = node

        # Selection: follows the highest UCT child.
        while current.children:
            current = max(current.children, key=lambda c: c.uct_score())

        # Expansion: adds all legal child positions once.
        if not current.board.is_game_over():
            for move in current.board.legal_moves:
                new_board = current.board.copy()
                new_board.push(move)
                child = MCTSNode(new_board, parent=current, move=move)
                current.children.append(child)

            current = random.choice(current.children)

        # Simulation: estimates the leaf with rollout plus static cutoff.
        result = self.rollout(current.board.copy())

        # Backpropagation: stores the result from the root player's view.
        root_player = node.board.turn
        root_value = result if root_player == chess.WHITE else -result

        while current is not None:
            current.visits += 1
            current.wins += root_value

            current = current.parent

    def rollout(self, board):
        # Plays random moves until the depth cutoff or a terminal position.
        for _ in range(self.rollout_depth):
            if board.is_game_over(claim_draw=True):
                break

            move = random.choice(list(board.legal_moves))
            board.push(move)

        # Uses static evaluation when the rollout stops before game end.
        if not board.is_game_over(claim_draw=True):
            return self._static_eval(board, chess.WHITE)

        # Converts terminal chess result into a numeric score.
        result = board.result(claim_draw=True)

        if result == "1-0":
            return 1
        elif result == "0-1":
            return -1
        else:
            return 0

class BestMCTSPlayer(MCTSPlayer):
    # Always selects the strongest ranked MCTS candidate.
    def choose_move(self, board):
        result = super().choose_move(board)

        if not isinstance(result, tuple):
            return result

        _, move_values = result
        return move_values[0][0], move_values

class AdaptiveMCTSPlayer:
    # Selects among strong candidates based on the player's observed errors.
    # Keeps safety and adaptation limits configurable.
    severe_material_risk_threshold = 0.5
    min_error_cap = 0.12
    max_error_cap = 0.30
    consistency_margin_weight = 0.5
    max_consistency_margin = 0.12
    minimum_model_observations = 4
    model_error_window = 6

    def __init__(self, simulations=200, top_k=5):
        # Keeps adaptive selection separate from base MCTS ranking.
        self.simulations = simulations
        self.top_k = top_k
        self.base_mcts = MCTSPlayer(simulations=simulations)
        self.player_model = PlayerModel() 
        self.last_decision_info = None

    def choose_move(self, board):
        # Resets logging data for the current decision.
        self.last_decision_info = None
        best_move, move_values = self.base_mcts.choose_move(board)

        if move_values is None or len(move_values) == 0:
            return random.choice(list(board.legal_moves))
        
        best_value = move_values[0][1]

        # Uses player history to set the desired move-quality gap.
        target_error = self.player_model.average_error()
        consistency_threshold = self.player_model.consistency()

        # Converts consistency into randomness around the target error.
        temperature = max(0.05, consistency_threshold)

        # Starts from the top-k candidates only.
        candidates = move_values[:self.top_k]
        candidate_count = len(candidates)

        # Removes moves with severe immediate material risk when possible.
        safe_candidates = [
            candidate
            for candidate in candidates
            if self.base_mcts._bad_loss_penalty(board, candidate[0])
            < self.severe_material_risk_threshold
        ]
        if safe_candidates:
            candidates = safe_candidates

        # Keeps candidate quality within the current adaptive error cap.
        dynamic_error_cap = self._dynamic_error_cap(board)
        quality_candidates = [
            candidate
            for candidate in candidates
            if best_value - candidate[1] <= dynamic_error_cap
        ]
        if quality_candidates:
            candidates = quality_candidates
        else:
            # Falls back to the best move if all candidates exceed the cap.
            candidates = candidates[:1]
        candidate_count_after_cap = len(candidates)

        scored_moves = []
        # Scores candidates by closeness to the player's target error.
        for move, value, visits in candidates:
            move_error = best_value - value
            score = math.exp(-abs(move_error - target_error) / temperature)
            scored_moves.append((move, score, move_error, value, visits))

        total_score = sum(score for _, score, _, _, _ in scored_moves)

        if total_score == 0:
            # Falls back to strongest play if sampling weights collapse.
            selected_move = best_move
        else:
            r = random.random() * total_score
            cumulative = 0

            # Samples one move according to adaptive scores.
            selected_move = best_move
            for move, score, move_error, value, visits in scored_moves:
                cumulative += score
                if r <= cumulative:
                    selected_move = move
                    break

        selected_move_rank, selected_move_value = self._selected_move_details(
            selected_move,
            move_values,
        )
        selected_move_error = best_value - selected_move_value
        self.last_decision_info = {
            # Stores decision details for JSON logging and analysis.
            "selected_move_rank": selected_move_rank,
            "selected_move_value": selected_move_value,
            "best_move_value": best_value,
            "selected_move_error": selected_move_error,
            "target_error": target_error,
            "temperature": temperature,
            "dynamic_error_cap": dynamic_error_cap,
            "candidate_count": candidate_count,
            "candidate_count_after_cap": candidate_count_after_cap,
            "chosen_move_passed_cap": selected_move_error <= dynamic_error_cap,
            "player_avg_error": self.player_model.average_error(),
            "player_recent_error": (
                self.player_model.errors[-1]
                if self.player_model.errors
                else None
            ),
            "player_consistency": consistency_threshold,
        }

        self._print_adaptive_debug(
            best_move=best_move,
            target_error=target_error,
            consistency=consistency_threshold,
            temperature=temperature,
            scored_moves=scored_moves,
            total_score=total_score,
            selected_move=selected_move,
        )

        return selected_move, move_values

    def _selected_move_details(self, selected_move, move_values):
        # Finds the selected move's rank and value in the full candidate list.
        for rank, (move, value, visits) in enumerate(move_values, start=1):
            if move == selected_move:
                return rank, value

        return None, None

    def _dynamic_error_cap(self, board=None):
        # Limits how far below the best move adaptive selection may go.
        if board is not None and board.fullmove_number <= self.base_mcts.opening_max_fullmove:
            # Keeps opening adaptation strict while early errors are noisy.
            return self.min_error_cap

        errors = self.player_model.errors
        if len(errors) < self.minimum_model_observations:
            # Requires enough observations before loosening the cap.
            return self.min_error_cap

        # Uses recent errors so old games do not dominate adaptation.
        recent_errors = errors[-self.model_error_window:]
        smoothed_average_error = sum(recent_errors) / len(recent_errors)

        # Uses recent consistency to allow slightly wider matching.
        if len(recent_errors) < 2:
            consistency = 0
        else:
            squared_differences = [
                (error - smoothed_average_error) ** 2
                for error in recent_errors
            ]
            consistency = math.sqrt(sum(squared_differences) / len(squared_differences))

        consistency_margin = min(
            self.max_consistency_margin,
            self.consistency_margin_weight * consistency,
        )

        # Clamps the cap between strict and maximum allowed adaptation.
        return min(
            self.max_error_cap,
            max(
                self.min_error_cap,
                smoothed_average_error + consistency_margin,
            ),
        )

    def _print_adaptive_debug(
        self,
        best_move,
        target_error,
        consistency,
        temperature,
        scored_moves,
        total_score,
        selected_move,
    ):
        # Prints adaptive selection diagnostics for thesis playtests.
        candidate_errors = [move_error for _, _, move_error, _, _ in scored_moves]
        minimum_candidate_error = min(candidate_errors)
        maximum_candidate_error = max(candidate_errors)
        closest_candidate = min(
            scored_moves,
            key=lambda item: abs(item[2] - target_error),
        )

        # Checks whether the target error is reachable by current candidates.
        target_inside_range = minimum_candidate_error <= target_error <= maximum_candidate_error
        selected_rank = next(
            rank
            for rank, (move, _, _, _, _) in enumerate(scored_moves, start=1)
            if move == selected_move
        )

        print("\nAdaptive MCTS decision:")
        print(f"top_k={self.top_k}")
        print(f"best_move={best_move}")
        print(f"target_error={target_error:.3f}")
        print(f"consistency={consistency:.3f}")
        print(f"temperature={temperature:.3f}")
        print(f"minimum_candidate_error={minimum_candidate_error:.3f}")
        print(f"maximum_candidate_error={maximum_candidate_error:.3f}")
        print(f"closest_candidate_to_target={closest_candidate[0]}")
        print(f"target_error_inside_candidate_range={target_inside_range}")
        if not target_inside_range:
            print("target_error outside candidate range")

        print("candidates:")
        for rank, (move, score, move_error, value, visits) in enumerate(scored_moves, start=1):
            probability = score / total_score if total_score > 0 else 0
            print(
                f"rank={rank} move={move} value={value:.3f} visits={visits} "
                f"error_from_best={move_error:.3f} adaptive_score={score:.3f} "
                f"probability={probability:.3f}"
            )

        print(f"selected_move={selected_move}")
        print(f"selected_move_rank={selected_rank}")
