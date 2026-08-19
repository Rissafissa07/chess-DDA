use crate::game::player::agent::Agent;
use crate::game::player::Player;
use super::status::Status;
use crate::game::Game;

#[derive(Debug, Clone)]
pub struct Result<M> {
    pub player: Player,
    pub mv: M,
    pub status: Status,
}

#[derive(Debug, Clone)]
pub struct Summary<M> {
    pub status: Status,
    pub history: Vec<M>,
    pub total_moves: usize,
}

pub struct Match<G: Game, P1: Agent<G>, P2: Agent<G>> {
    pub game: G,
    pub agent1: P1,
    pub agent2: P2,
    pub history: Vec<G::Move>,
}

impl<G: Game, P1: Agent<G>, P2: Agent<G>> Match<G, P1, P2> {
    pub fn new(game: G, agent1: P1, agent2: P2) -> Self {
        Self {
            game,
            agent1,
            agent2,
            history: Vec::new(),
        }
    }

    pub fn play_step(&mut self) -> Option<Result<G::Move>> {
        if self.game.status().is_terminal() {
            return None;
        }

        let current = self.game.current_player();

        let chosen_move = match current {
            Player::Player1 => self.agent1.select_move(&self.game)?,
            Player::Player2 => self.agent2.select_move(&self.game)?,
        };

        self.game.make_move(chosen_move);
        self.history.push(chosen_move);

        Some(Result {
            player: current,
            mv: chosen_move,
            status: self.game.status(),
        })
    }

    pub fn play_to_completion(&mut self) -> Summary<G::Move> {
        while self.game.status().is_ongoing() {
            if self.play_step().is_none() {
                break;
            }
        }

        Summary {
            status: self.game.status(),
            history: self.history.clone(),
            total_moves: self.history.len(),
        }
    }
}
