#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Player {
    Player1,
    Player2,
}

impl Player {
    pub fn opponent(&self) -> Player {
        match self {
            Player::Player1 => Player::Player2,
            Player::Player2 => Player::Player1,
        }
    }
}