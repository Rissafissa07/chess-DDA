use std::io::{self, Write};
use crate::game::player::agent::Agent;
use crate::game::Game;

pub struct HumanAgent {
    pub name: String,
}

impl HumanAgent {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
        }
    }
}

impl<G: Game<Move = usize>> Agent<G> for HumanAgent {
    fn select_move(&mut self, game: &G) -> Option<G::Move> {
        let legal_moves = game.legal_moves();
        if legal_moves.is_empty() {
            return None;
        }

        loop {
            print!("{}: enter your move {:?}: ", self.name, legal_moves);
            io::stdout().flush().unwrap();

            let mut input = String::new();
            if io::stdin().read_line(&mut input).is_err() {
                continue;
            }

            if let Ok(mv) = input.trim().parse::<usize>() {
                if legal_moves.contains(&mv) {
                    return Some(mv);
                }
            }

            println!("Invalid move! Please select from {:?}", legal_moves);
        }
    }

    fn name(&self) -> &str {
        &self.name
    }
}
