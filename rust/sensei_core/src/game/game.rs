use std::fmt::Debug;

use crate::game::player::Player;
use crate::game::Status;

pub trait Game: Clone + Send + Sync {
    type Move: Copy + PartialEq + Debug;

    fn legal_moves(&self) -> Vec<Self::Move>;
    fn make_move(&mut self, mv: Self::Move);
    fn current_player(&self) -> Player; // dit is sus als we het met street fighter willen laten wekren bijvoorbeeld
    fn status(&self) -> Status;
}
