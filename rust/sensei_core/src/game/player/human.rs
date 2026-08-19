use crate::game::player::agent::Agent;
use crate::game::Game;
use std::io::{self, Write};

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

impl<G: Game> Agent<G> for HumanAgent {
    fn select_move(&mut self, game: &G) -> Option<G::Move> {
        let legal_moves = game.legal_moves();
        if legal_moves.is_empty() {
            return None;
        }

        // render the board visually for the human player
        println!("{}", game);

        loop {
            print!("{}: enter your move: ", self.name);
            io::stdout().flush().unwrap();

            let mut input = String::new();
            if io::stdin().read_line(&mut input).is_err() {
                continue;
            }

            if let Some(mv) = game.parse_move(input.trim()) {
                if legal_moves.contains(&mv) {
                    return Some(mv);
                } else {
                    println!(
                        "Invalid: square {} is already occupied",
                        game.format_move(mv)
                    );
                    continue;
                }
            }

            println!("Invalid: not a coordinate, enter a valid square (eg H8)");
        }
    }

    fn name(&self) -> &str {
        &self.name
    }
}
