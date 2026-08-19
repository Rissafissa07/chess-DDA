use crate::game::Game;
use crate::game::player::Player;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TicTacToe {
    pub board: [Option<Player>; 9],
    pub turn: Player,
}

impl TicTacToe {
    pub fn new() -> Self {
        Self {
            board: [None; 9],
            turn: Player::Player1,
        }
    }

    pub fn check_win(&self, player: Player) -> bool {
        const WINNING_LINES: [[usize; 3]; 8] = [
            // Rows
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            // Columns
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            // Diagonals
            [0, 4, 8], [2, 4, 6],
        ];

        WINNING_LINES.iter().any(|&[a, b, c]| {
            self.board[a] == Some(player)
                && self.board[b] == Some(player)
                && self.board[c] == Some(player)
        })
    }

    pub fn is_full(&self) -> bool {
        self.board.iter().all(|square| square.is_some())
    }

    pub fn display_board(&self) {
        println!();
        for row in 0..3 {
            let cells: Vec<String> = (0..3)
                .map(|col| {
                    let idx = row * 3 + col;
                    match self.board[idx] {
                        Some(Player::Player1) => "X".to_string(),
                        Some(Player::Player2) => "O".to_string(),
                        None => idx.to_string(),
                    }
                })
                .collect();
            println!(" {} | {} | {} ", cells[0], cells[1], cells[2]);
            if row < 2 {
                println!("---+---+---");
            }
        }
        println!();
    }
}

impl Game for TicTacToe {
    type Move = usize;

    fn legal_moves(&self) -> Vec<Self::Move> {
        if self.is_terminal() {
            return Vec::new();
        }

        let mut moves = Vec::new();

        for (idx, square) in self.board.iter().enumerate() {
            if square.is_none() {
                moves.push(idx)
            }
        }
        moves
    }

    fn make_move(&mut self, mv: Self::Move) {
        self.board[mv] = Some(self.turn);
        self.turn = self.turn.opponent();
    }

    fn is_terminal(&self) -> bool {
        self.check_win(Player::Player1)
            || self.check_win(Player::Player2)
            || self.is_full()
    }

    fn current_player(&self) -> Player {
        self.turn
    }

    fn reward(&self, player: Player) -> f32 {
        if self.check_win(player) {
            1.0
        } else if self.check_win(player.opponent()) {
            -1.0
        } else {
            0.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn initial_board() {
        let game = TicTacToe::new();

        assert_eq!(game.legal_moves().len(), 9);
        assert!(!game.is_terminal());
        assert_eq!(game.current_player(), Player::Player1);
    }

    #[test]
    fn win() {
        let mut game = TicTacToe::new();

        game.make_move(0);
        game.make_move(3);

        game.make_move(1);
        game.make_move(4);

        game.make_move(2);

        assert!(game.is_terminal());
        assert_eq!(game.reward(Player::Player1), 1.0);
        assert_eq!(game.reward(Player::Player2), -1.0)
    }
}
