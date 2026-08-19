use std::fmt::{Debug, Display};

use crate::game::player::Player;
use crate::game::Status;

pub trait Game: Clone + Send + Sync + Display + PartialEq {
    type Move: Copy + PartialEq + Debug;

    fn legal_moves(&self) -> Vec<Self::Move>;
    fn make_move(&mut self, mv: Self::Move);
    fn current_player(&self) -> Player;
    fn status(&self) -> Status;
}
