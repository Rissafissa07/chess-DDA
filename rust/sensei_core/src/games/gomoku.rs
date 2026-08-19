use std::fmt;

use crate::game::{Game, Player, Status};

pub const SIZE: usize = 15;
pub const CELLS: usize = SIZE * SIZE;

const DIRECTIONS: [(isize, isize); 4] = [
    (1, 0),  // vertical
    (0, 1),  // horizontal
    (1, 1),  // diag down-right
    (1, -1), // diag down-left
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Gomoku {
    pub board: [Option<Player>; CELLS],
    pub turn: Player,
    pub last_move: Option<usize>,
}

impl Gomoku {
    pub fn new() -> Self {
        Self {
            board: [None; CELLS],
            turn: Player::Player1,
            last_move: None,
        }
    }

    pub fn check_win_from(&self, last_idx: usize, player: Player) -> bool {
        let row = (last_idx / SIZE) as isize;
        let col = (last_idx % SIZE) as isize;

        for &(dr, dc) in &DIRECTIONS {
            let mut count = 1;

            // positive direction
            for step in 1..5 {
                let r = row + dr * step;
                let c = col + dc * step;

                if r >= 0 && r < SIZE as isize && c >= 0 && c < SIZE as isize {
                    if self.board[r as usize * SIZE + c as usize] == Some(player) {
                        count += 1;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }

            // negative direction
            for step in 1..5 {
                let r = row - dr * step;
                let c = col - dc * step;

                if r >= 0 && r < SIZE as isize && c >= 0 && c < SIZE as isize {
                    if self.board[r as usize * SIZE + c as usize] == Some(player) {
                        count += 1;
                    } else {
                        break;
                    }
                } else {
                    break;
                }
            }

            if count >= 5 {
                return true;
            }
        }

        false
    }

    pub fn is_full(&self) -> bool {
        self.board.iter().all(|sq| sq.is_some())
    }
}

impl Default for Gomoku {
    fn default() -> Self {
        Self::new()
    }
}

impl Game for Gomoku {
    type Move = usize;

    fn fill_legal_moves(&self, moves: &mut Vec<Self::Move>) {
        if self.status().is_terminal() {
            return;
        }

        for (idx, square) in self.board.iter().enumerate() {
            if square.is_none() {
                moves.push(idx);
            }
        }
    }

    fn make_move(&mut self, mv: Self::Move) {
        self.board[mv] = Some(self.turn);
        self.last_move = Some(mv);
        self.turn = self.turn.opponent();
    }

    fn current_player(&self) -> Player {
        self.turn
    }

    fn status(&self) -> Status {
        if let Some(last_idx) = self.last_move {
            let prev_player = self.turn.opponent();

            if self.check_win_from(last_idx, prev_player) {
                return Status::Win(prev_player);
            }
        }

        if self.is_full() {
            Status::Draw
        } else {
            Status::Ongoing
        }
    }

    fn parse_move(&self, input: &str) -> Option<Self::Move> {
        let trimmed = input.trim();
        if trimmed.is_empty() {
            return None;
        }

        // 1. parse coordinates (eg H8)
        let first_char = trimmed.chars().next()?.to_ascii_uppercase();
        if first_char.is_ascii_alphabetic() {
            let col = (first_char as u8).checked_sub(b'A')? as usize;
            if col >= SIZE {
                return None;
            }

            let row_str = &trimmed[1..];
            let row_num = row_str.parse::<usize>().ok()?;
            if row_num == 0 || row_num > SIZE {
                return None;
            }

            let row = row_num - 1;
            return Some(row * SIZE + col);
        }

        // 2. direct numeric index fallback (eg `112``)
        trimmed.parse::<usize>().ok().filter(|&idx| idx < CELLS)
    }

    fn format_move(&self, mv: Self::Move) -> String {
        let col = (b'A' + (mv % SIZE) as u8) as char;
        let row = mv / SIZE + 1;
        format!("{}{}", col, row)
    }
}

impl fmt::Display for Gomoku {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        writeln!(f)?;
        write!(f, "    ")?;
        for col in 0..SIZE {
            write!(f, " {:2}", (b'A' + col as u8) as char)?;
        }
        writeln!(f)?;
        for row in 0..SIZE {
            write!(f, "{:2} |", row + 1)?;
            for col in 0..SIZE {
                let idx = row * SIZE + col;
                let symbol = match self.board[idx] {
                    Some(Player::Player1) => " X ",
                    Some(Player::Player2) => " O ",
                    None => " . ",
                };
                write!(f, "{}", symbol)?;
            }
            writeln!(f, "|")?;
        }
        writeln!(f)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn horizontal_win() {
        let mut game = Gomoku::new();

        for col in 0..4 {
            game.make_move(col);
            game.make_move(SIZE + col);
        }

        game.make_move(4);

        assert_eq!(game.status(), Status::Win(Player::Player1));
    }

    #[test]
    fn diagonal_win() {
        let mut game = Gomoku::new();

        for step in 0..4 {
            game.make_move(step * SIZE + step);
            game.make_move(step * SIZE + 14);
        }

        game.make_move(4 * SIZE + 4);

        assert_eq!(game.status(), Status::Win(Player::Player1));
    }

    #[test]
    fn coordinate_parsing() {
        let game = Gomoku::new();

        // A1 -> 0
        assert_eq!(game.parse_move("A1"), Some(0));
        assert_eq!(game.parse_move("a1"), Some(0));

        // H8 -> 112
        assert_eq!(game.parse_move("H8"), Some(112));
        assert_eq!(game.parse_move("h8"), Some(112));

        // Format test
        assert_eq!(game.format_move(112), "H8");
        assert_eq!(game.format_move(0), "A1");
    }
}
