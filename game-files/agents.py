import chess
import random
import math


class RandomPlayer:
    def choose_move(self, board):
        return random.choice(list(board.legal_moves))


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
            key=lambda c: c.wins / c.visits if c.visits > 0 else -1
        )
        
        move_values = []

        for child in root.children:
            if child.visits > 0:
                value = child.wins / child.visits
            else:
                value = 0

            move_values.append((child.move, value, child.visits))

        # sort best → worst
        move_values.sort(key=lambda x: x[1], reverse=True)

        # DEBUG PRINT (important for now)
        print("\nMove evaluations:")
        for move, value, visits in move_values[:5]:
            print(f"{move} → value={value:.3f}, visits={visits}")

        # return best move (for now)
        best_move = move_values[0][0]  # Return the move with the highest value
        return best_move, move_values
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

        while current is not None:
            # Update visits and wins
            current.visits += 1

            if current.board.turn == root_player:
                current.wins += result
            else:
                current.wins -= result

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