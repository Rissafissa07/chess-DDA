use std::fmt;

use crate::game::player::Player;
use crate::game::Game;
use crate::game::Status;

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
            // rows
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            // columns
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            // diagonals
            [0, 4, 8],
            [2, 4, 6],
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
}

impl Default for TicTacToe {
    fn default() -> Self {
        Self::new()
    }
}

impl Game for TicTacToe {
    type Move = usize;

    fn fill_legal_moves(&self, buffer: &mut Vec<Self::Move>) {
        if self.status().is_terminal() {
            return;
        }

        for (idx, square) in self.board.iter().enumerate() {
            if square.is_none() {
                buffer.push(idx);
            }
        }
    }

    fn make_move(&mut self, mv: Self::Move) {
        self.board[mv] = Some(self.turn);
        self.turn = self.turn.opponent();
    }

    fn current_player(&self) -> Player {
        self.turn
    }

    fn status(&self) -> Status {
        if self.check_win(Player::Player1) {
            Status::Win(Player::Player1)
        } else if self.check_win(Player::Player2) {
            Status::Win(Player::Player2)
        } else if self.is_full() {
            Status::Draw
        } else {
            Status::Ongoing
        }
    }

    fn parse_move(&self, input: &str) -> Option<Self::Move> {
        input.trim().parse::<usize>().ok().filter(|&idx| idx < 9)
    }
}

impl fmt::Display for TicTacToe {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f)?;
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
            writeln!(f, " {} | {} | {} ", cells[0], cells[1], cells[2])?;
            if row < 2 {
                writeln!(f, "---+---+---")?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn initial_board() {
        let game = TicTacToe::new();

        assert_eq!(game.legal_moves().len(), 9);
        assert_eq!(game.status(), Status::Ongoing);
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

        assert_eq!(game.status(), Status::Win(Player::Player1));
        assert_eq!(game.status().reward_for(Player::Player1), 1.0);
        assert_eq!(game.status().reward_for(Player::Player2), 0.0);
    }
}
