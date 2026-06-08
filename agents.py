import chess
import random
import math


class RandomPlayer:
    def choose_move(self, board):
        return random.choice(list(board.legal_moves))

class PlayerModel:
    def __init__(self):
        self.errors = []

    def update(self, error):
        if error is not None:
            self.errors.append(error)

    def average_error(self):
        if len(self.errors) == 0:
            return 0

        return sum(self.errors) / len(self.errors)

    def consistency(self):
        if len(self.errors) < 2:
            return 0

        avg = self.average_error()
        squared_differences = [(error - avg) ** 2 for error in self.errors]
        variance = sum(squared_differences) / len(squared_differences)

        return math.sqrt(variance)

    def blunder_rate(self, threshold=0.5):
        if len(self.errors) == 0:
            return 0

        blunders = [error for error in self.errors if error >= threshold]
        return len(blunders) / len(self.errors)

def find_move_error(chosen_move, move_values):
    if move_values is None or len(move_values) == 0:
        return None

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
    # Represents a node in the Monte Carlo Tree Search
    def __init__(self, board, parent=None, move=None):
        self.board = board
        self.parent = parent
        self.move = move
        self.children = []
        self.visits = 0
        self.wins = 0

    def uct_score(self, c=1.4):
        # UCT score for selection
        if self.visits == 0: 
            return float("inf")
        return (self.wins / self.visits) + c * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )


class MCTSPlayer:
    piece_values = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }
    static_piece_values = {
        chess.PAWN: 1.0,
        chess.KNIGHT: 3.2,
        chess.BISHOP: 3.3,
        chess.ROOK: 5.0,
        chess.QUEEN: 9.0,
    }
    material_risk_weight = 0.1
    root_static_eval_weight = 0.35
    static_eval_scale = 6.0
    mobility_weight = 0.03
    centre_control_weight = 0.10
    bishop_pair_bonus = 0.20
    castling_rights_bonus = 0.10
    castled_king_bonus = 0.25
    developed_minor_bonus = 0.10
    doubled_pawn_penalty = 0.12
    isolated_pawn_penalty = 0.10
    passed_pawn_base_bonus = 0.08
    passed_pawn_advance_bonus = 0.04
    blocked_passed_pawn_multiplier = 0.45
    king_pressure_attack_weight = 0.04
    king_pressure_near_king_weight = 0.06
    king_pressure_direct_check_weight = 0.12
    own_king_pressure_penalty = 0.06
    own_king_direct_check_penalty = 0.12
    attacked_piece_weight = 0.04
    undefended_attacked_piece_weight = 0.08
    own_attacked_piece_penalty = 0.04
    own_undefended_attacked_piece_penalty = 0.08
    opening_max_fullmove = 8
    develop_minor_bonus = 0.08
    centre_pawn_bonus = 0.06
    central_minor_bonus = 0.04
    castling_bonus = 0.12
    early_queen_move_penalty = 0.10
    repeated_piece_move_penalty = 0.06

    def __init__(self, simulations=200):
        self.simulations = simulations

    def choose_move(self, board):
        root = MCTSNode(board.copy())
        # Run simulations to build the tree
        for _ in range(self.simulations):
            self.simulate(root)
        # If no children were added (e.g., if the game is already over), return a random move
        if not root.children:
            return random.choice(list(board.legal_moves))

        best_child = max(
            root.children,
            key=lambda c: (c.wins / c.visits) if c.visits > 0 else float("-inf")
        )
        
        move_values = []

        for child in root.children:
            if child.visits > 0:
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

        # sort best -> worst
        move_values.sort(key=lambda x: x[1], reverse=True)

        # DEBUG PRINT (important for now)
        print("\nMove evaluations:")
        for move, value, visits in move_values[:5]:
            print(f"{move} -> value={value:.3f}, visits={visits}")

        # return best move (for now)
        best_move = move_values[0][0]  # Return the move with the highest value
        return best_move, move_values

    def _material_balance(self, board, color):
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
        root_player = board.turn
        starting_balance = self._material_balance(board, root_player)
        candidate_board = board.copy()
        candidate_board.push(candidate_move)

        if candidate_board.is_checkmate():
            return 0

        candidate_gain = max(
            0,
            self._material_balance(candidate_board, root_player) - starting_balance,
        )
        worst_uncompensated_loss = 0

        for reply in candidate_board.legal_moves:
            reply_board = candidate_board.copy()
            reply_board.push(reply)

            immediate_loss = (
                self._material_balance(candidate_board, root_player)
                - self._material_balance(reply_board, root_player)
            )
            if immediate_loss <= 0:
                continue

            compensation = self._best_immediate_compensation(reply_board, root_player)
            uncompensated_loss = max(0, immediate_loss - candidate_gain - compensation)
            worst_uncompensated_loss = max(worst_uncompensated_loss, uncompensated_loss)

        return self.material_risk_weight * worst_uncompensated_loss

    def _opening_bonus(self, board, candidate_move):
        if board.fullmove_number > self.opening_max_fullmove:
            return 0

        piece = board.piece_at(candidate_move.from_square)
        if piece is None:
            return 0

        bonus = 0
        starting_rank = 0 if piece.color == chess.WHITE else 7
        central_pawn_squares = {chess.D4, chess.E4, chess.D5, chess.E5}
        central_knight_squares = {chess.C3, chess.F3, chess.C6, chess.F6}

        if (
            piece.piece_type in (chess.KNIGHT, chess.BISHOP)
            and chess.square_rank(candidate_move.from_square) == starting_rank
        ):
            bonus += self.develop_minor_bonus

        if piece.piece_type == chess.PAWN and candidate_move.to_square in central_pawn_squares:
            bonus += self.centre_pawn_bonus

        if piece.piece_type == chess.KNIGHT and candidate_move.to_square in central_knight_squares:
            bonus += self.central_minor_bonus

        if board.is_castling(candidate_move):
            bonus += self.castling_bonus

        if piece.piece_type == chess.QUEEN:
            bonus -= self.early_queen_move_penalty

        if (
            len(board.move_stack) >= 2
            and candidate_move.from_square == board.move_stack[-2].to_square
        ):
            bonus -= self.repeated_piece_move_penalty

        return bonus

    def _static_eval(self, board, root_player):
        if board.is_checkmate():
            return 1 if board.turn != root_player else -1
        if board.is_game_over(claim_draw=True):
            return 0

        root_score = self._static_score_for_color(board, root_player)
        opponent_score = self._static_score_for_color(board, not root_player)
        return math.tanh((root_score - opponent_score) / self.static_eval_scale)

    def _static_score_for_color(self, board, color):
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
        return sum(
            len(board.pieces(piece_type, color)) * value
            for piece_type, value in self.static_piece_values.items()
        )

    def _mobility(self, board, color):
        mobility_board = board.copy(stack=False)
        mobility_board.turn = color
        return mobility_board.legal_moves.count()

    def _centre_control(self, board, color):
        central_squares = (chess.D4, chess.E4, chess.D5, chess.E5)
        return sum(bool(board.attackers(color, square)) for square in central_squares)

    def _bishop_pair_score(self, board, color):
        if len(board.pieces(chess.BISHOP, color)) >= 2:
            return self.bishop_pair_bonus
        return 0

    def _king_safety_score(self, board, color):
        king_square = board.king(color)
        castled_squares = (
            {chess.G1, chess.C1}
            if color == chess.WHITE
            else {chess.G8, chess.C8}
        )

        score = 0
        if king_square in castled_squares:
            score += self.castled_king_bonus
        if board.has_kingside_castling_rights(color):
            score += self.castling_rights_bonus
        if board.has_queenside_castling_rights(color):
            score += self.castling_rights_bonus
        return score

    def _developed_minor_score(self, board, color):
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
        def passed_pawn_value(square, pawn_color):
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
        file_index = chess.square_file(square)
        rank = chess.square_rank(square)
        adjacent_files = range(max(0, file_index - 1), min(7, file_index + 1) + 1)

        for enemy_square in board.pieces(chess.PAWN, not color):
            enemy_file = chess.square_file(enemy_square)
            if enemy_file not in adjacent_files:
                continue

            enemy_rank = chess.square_rank(enemy_square)
            if color == chess.WHITE and enemy_rank > rank:
                return False
            if color == chess.BLACK and enemy_rank < rank:
                return False

        return True

    def _king_pressure_score(self, board, color):
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
        king_square = board.king(king_color)
        if king_square is None:
            return 0

        pressure_piece_weights = {
            chess.KNIGHT: 1.0,
            chess.BISHOP: 1.0,
            chess.ROOK: 1.2,
            chess.QUEEN: 1.5,
        }
        king_zone = chess.SquareSet(chess.BB_KING_ATTACKS[king_square])
        pressure_score = 0
        unique_attackers = set()

        for target_square in king_zone:
            for attacker_square in board.attackers(attacking_color, target_square):
                piece = board.piece_at(attacker_square)
                if piece is None or piece.piece_type not in pressure_piece_weights:
                    continue

                unique_attackers.add(attacker_square)
                pressure_score += pressure_weight * pressure_piece_weights[piece.piece_type]

        for attacker_square in board.attackers(attacking_color, king_square):
            piece = board.piece_at(attacker_square)
            if piece is None or piece.piece_type not in pressure_piece_weights:
                continue

            unique_attackers.add(attacker_square)
            pressure_score += direct_check_weight * pressure_piece_weights[piece.piece_type]

        if len(unique_attackers) > 1:
            pressure_score += self.king_pressure_near_king_weight * (len(unique_attackers) - 1)

        return pressure_score

    def _piece_pressure_score(self, board, color):
        score = 0
        for square, piece in board.piece_map().items():
            if piece.piece_type == chess.KING:
                continue

            piece_value = self.static_piece_values[piece.piece_type]
            attacked_by_color = bool(board.attackers(color, square))
            attacked_by_opponent = bool(board.attackers(not color, square))
            defended = bool(board.attackers(piece.color, square))

            if piece.color != color and attacked_by_color:
                score += self.attacked_piece_weight * piece_value
                if not defended:
                    score += self.undefended_attacked_piece_weight * piece_value

            if piece.color == color and attacked_by_opponent:
                score -= self.own_attacked_piece_penalty * piece_value
                if not defended:
                    score -= self.own_undefended_attacked_piece_penalty * piece_value

        return score

    def simulate(self, node):
        current = node

        # SELECTION - traverse down the tree using UCT scores
        while current.children:
            current = max(current.children, key=lambda c: c.uct_score())

        # EXPANSION - if the node is not terminal, expand it
        if not current.board.is_game_over():
            for move in current.board.legal_moves:
                new_board = current.board.copy()
                new_board.push(move)
                child = MCTSNode(new_board, parent=current, move=move)
                current.children.append(child)

            current = random.choice(current.children)

        # SIMULATION - perform a random rollout from the current node
        result = self.rollout(current.board.copy())

        # BACKPROP - update the node statistics up the tree
        root_player = node.board.turn
        root_value = result if root_player == chess.WHITE else -result

        while current is not None:
            # Update visits and wins
            current.visits += 1
            current.wins += root_value

            current = current.parent

    def rollout(self, board):
        # Perform a random rollout until the game ends
        while not board.is_game_over():
            move = random.choice(list(board.legal_moves))
            board.push(move)
        # Determine the result of the game
        result = board.result()

        if result == "1-0":
            return 1
        elif result == "0-1":
            return -1
        else:
            return 0

class BestMCTSPlayer(MCTSPlayer):
    def choose_move(self, board):
        result = super().choose_move(board)

        if not isinstance(result, tuple):
            return result

        _, move_values = result
        return move_values[0][0], move_values

class AdaptiveMCTSPlayer:
    severe_material_risk_threshold = 0.5
    min_error_cap = 0.12
    max_error_cap = 0.30
    consistency_margin_weight = 0.5
    max_consistency_margin = 0.12
    minimum_model_observations = 4
    model_error_window = 6

    def __init__(self, simulations=200, top_k=5):
        self.simulations = simulations
        self.top_k = top_k
        self.base_mcts = MCTSPlayer(simulations=simulations)
        self.player_model = PlayerModel() 
        self.last_decision_info = None

    def choose_move(self, board):
        self.last_decision_info = None
        best_move, move_values = self.base_mcts.choose_move(board)

        if move_values is None or len(move_values) == 0:
            return random.choice(list(board.legal_moves))  # No move values available, return a random move
        
        best_value = move_values[0][1]
        target_error = self.player_model.average_error() # Could be a fixed threshold or based on the player's historical performance
        consistency_threshold = self.player_model.consistency()  # Could be a fixed threshold or based on the player's historical performance

        temperature = max(0.05, consistency_threshold)  # Ensure temperature is not too low, will be adjusted if necessary

        candidates = move_values[:self.top_k]
        candidate_count = len(candidates)
        safe_candidates = [
            candidate
            for candidate in candidates
            if self.base_mcts._bad_loss_penalty(board, candidate[0])
            < self.severe_material_risk_threshold
        ]
        if safe_candidates:
            candidates = safe_candidates

        dynamic_error_cap = self._dynamic_error_cap()
        quality_candidates = [
            candidate
            for candidate in candidates
            if best_value - candidate[1] <= dynamic_error_cap
        ]
        if quality_candidates:
            candidates = quality_candidates
        else:
            candidates = candidates[:1]
        candidate_count_after_cap = len(candidates)

        scored_moves = []
        for move, value, visits in candidates:
            move_error = best_value - value
            score = math.exp(-abs(move_error - target_error) / temperature)
            scored_moves.append((move, score, move_error, value, visits))

        total_score = sum(score for _, score, _, _, _ in scored_moves)

        if total_score == 0:
            selected_move = best_move
        else:
            r = random.random() * total_score
            cumulative = 0

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
        for rank, (move, value, visits) in enumerate(move_values, start=1):
            if move == selected_move:
                return rank, value

        return None, None

    def _dynamic_error_cap(self):
        errors = self.player_model.errors
        if len(errors) < self.minimum_model_observations:
            return self.min_error_cap

        recent_errors = errors[-self.model_error_window:]
        smoothed_average_error = sum(recent_errors) / len(recent_errors)

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
        candidate_errors = [move_error for _, _, move_error, _, _ in scored_moves]
        minimum_candidate_error = min(candidate_errors)
        maximum_candidate_error = max(candidate_errors)
        closest_candidate = min(
            scored_moves,
            key=lambda item: abs(item[2] - target_error),
        )
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
