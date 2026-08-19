use std::fmt::Debug;

use crate::game::player::Player;

pub trait Game: Clone + Send + Sync {
    type Move: Copy + PartialEq + Debug;

    fn legal_moves(&self) -> Vec<Self::Move>;
    fn make_move(&mut self, mv: Self::Move);
    fn is_terminal(&self) -> bool;
    fn current_player(&self) -> Player; // dit is sus als we het met street fighter willen laten wekren bijvoorbeeld
    fn reward(&self, player: Player) -> f32;
}
