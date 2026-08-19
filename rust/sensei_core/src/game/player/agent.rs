use crate::game::Game;

pub trait Agent<G: Game> {
    fn select_move(&mut self, game: &G) -> Option<G::Move>;
    fn name(&self) -> &str;
}
