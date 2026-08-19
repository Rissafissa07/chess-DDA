use crate::game::player::agent::Agent;
use crate::game::Game;

use rand::seq::SliceRandom;

pub struct RandomAgent {
    pub rng: rand::rngs::ThreadRng,
}

impl RandomAgent {
    pub fn new() -> Self {
        Self {
            rng: rand::thread_rng(),
        }
    }
}

impl Default for RandomAgent {
    fn default() -> Self {
        Self::new()
    }
}

impl<G: Game> Agent<G> for RandomAgent {
    fn select_move(&mut self, game: &G) -> Option<G::Move> {
        let moves = game.legal_moves();
        moves.choose(&mut self.rng).copied()
    }

    fn name(&self) -> &str {
        "Random"
    }
}
