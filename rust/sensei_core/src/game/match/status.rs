use crate::game::player::Player;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {
    Ongoing,
    Win(Player),
    Draw,
}

impl Status {
    pub fn is_terminal(&self) -> bool {
        matches!(self, Status::Win(_) | Status::Draw)
    }

    pub fn is_ongoing(&self) -> bool {
        matches!(self, Status::Ongoing)
    }

    pub fn reward_for(&self, player: Player) -> f32 {
        match self {
            Status::Win(winner) if *winner == player => 1.0,
            Status::Win(_) => 0.0,
            Status::Draw => 0.5,
            Status::Ongoing => panic!("Cannot get reward for ongoing game"),
        }
    }
}
