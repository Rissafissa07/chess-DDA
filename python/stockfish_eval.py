import math
import shutil

import chess.engine


class StockfishEvaluator:
    # Wraps Stockfish and returns bounded scores from one player's perspective.
    def __init__(
        self,
        path=None,
        depth=8,
        score_scale=600,
        mate_score=10000,
    ):
        self.path = path or shutil.which("stockfish") or "/opt/homebrew/bin/stockfish"
        self.depth = depth
        self.score_scale = score_scale
        self.mate_score = mate_score
        self.engine = chess.engine.SimpleEngine.popen_uci(self.path)
        self.cache = {}

    def evaluate(self, board, root_player):
        cache_key = (board.transposition_key() if hasattr(board, "transposition_key") else board.fen(), root_player)
        if cache_key in self.cache:
            return self.cache[cache_key]

        info = self.engine.analyse(
            board,
            chess.engine.Limit(depth=self.depth),
        )
        score = info["score"].pov(root_player)
        centipawns = score.score(mate_score=self.mate_score)
        if centipawns is None:
            value = 0
        else:
            value = math.tanh(centipawns / self.score_scale)

        self.cache[cache_key] = value
        return value

    def close(self):
        self.engine.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
