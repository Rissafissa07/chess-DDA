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
    material_risk_weight = 0.1
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
                value = mcts_value - bad_loss_penalty + opening_bonus
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

    def __init__(self, simulations=200, top_k=5):
        self.simulations = simulations
        self.top_k = top_k
        self.base_mcts = MCTSPlayer(simulations=simulations)
        self.player_model = PlayerModel() 

    def choose_move(self, board):
        best_move, move_values = self.base_mcts.choose_move(board)

        if move_values is None or len(move_values) == 0:
            return random.choice(list(board.legal_moves))  # No move values available, return a random move
        
        best_value = move_values[0][1]
        target_error = self.player_model.average_error() # Could be a fixed threshold or based on the player's historical performance
        consistency_threshold = self.player_model.consistency()  # Could be a fixed threshold or based on the player's historical performance

        temperature = max(0.05, consistency_threshold)  # Ensure temperature is not too low, will be adjusted if necessary

        candidates = move_values[:self.top_k]
        safe_candidates = [
            candidate
            for candidate in candidates
            if self.base_mcts._bad_loss_penalty(board, candidate[0])
            < self.severe_material_risk_threshold
        ]
        if safe_candidates:
            candidates = safe_candidates

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
