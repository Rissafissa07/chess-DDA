use crate::game::player::agent::Agent;
use crate::game::player::ai::core::node::Node;
use crate::game::Game;

use rand::seq::SliceRandom;

pub struct MCTS<G: Game> {
    pub simulations: usize,
    pub c: f32, // exploration constant (typically sqrt(2) ≈ 1.414)
    pub nodes: Vec<Node<G::Move>>,
}

impl<G: Game> MCTS<G> {
    pub fn new(simulations: usize, c: f32) -> Self {
        Self {
            simulations,
            c,
            nodes: Vec::new(),
        }
    }

    // TODO: cross compare with typescript gomoku-sensei
    pub fn simulate(&mut self, root_game: &G) {
        let mut curr_idx = 0;
        let mut sim_game = root_game.clone();

        // 1. selection
        while !self.nodes[curr_idx].children.is_empty() && sim_game.status().is_ongoing() {
            let parent_visits = self.nodes[curr_idx].visits;
            let best_child_idx = *self.nodes[curr_idx]
                .children
                .iter()
                .max_by(|&&a, &&b| {
                    let score_a = self.nodes[a].uct_score(parent_visits, self.c);
                    let score_b = self.nodes[b].uct_score(parent_visits, self.c);
                    score_a.partial_cmp(&score_b).unwrap()
                })
                .unwrap();

            curr_idx = best_child_idx;
            sim_game.make_move(self.nodes[curr_idx].mv.unwrap());
        }

        // 2. expansion
        if sim_game.status().is_ongoing() {
            let legal_moves = sim_game.legal_moves();

            for mv in &legal_moves {
                let child_node = Node::new(Some(*mv), Some(curr_idx));
                let child_idx = self.nodes.len();

                self.nodes.push(child_node);
                self.nodes[curr_idx].children.push(child_idx);
            }

            // pick first child for rollout
            if let Some(&first_child) = self.nodes[curr_idx].children.first() {
                curr_idx = first_child;
                sim_game.make_move(self.nodes[curr_idx].mv.unwrap());
            }
        }

        // 3. rollout
        let mut rollout_game = sim_game;
        let mut rng = rand::thread_rng();

        while rollout_game.status().is_ongoing() {
            let moves = rollout_game.legal_moves();

            if let Some(&random_mv) = moves.choose(&mut rng) {
                rollout_game.make_move(random_mv);
            } else {
                break;
            }
        }

        // 4. backpropagation
        let root_player = root_game.current_player();
        let outcome_reward = rollout_game.status().reward_for(root_player);
        let mut backprop_idx = Some(curr_idx);

        while let Some(idx) = backprop_idx {
            self.nodes[idx].visits += 1;
            self.nodes[idx].total_reward += outcome_reward;
            backprop_idx = self.nodes[idx].parent;
        }
    }

    pub fn best_move(&mut self, root_game: &G) -> Option<G::Move> {
        let legal_moves = root_game.legal_moves();

        if legal_moves.is_empty() {
            return None;
        }

        if legal_moves.len() == 1 {
            return Some(legal_moves[0]);
        }

        self.nodes.clear();
        self.nodes.push(Node::new(None, None));

        for _ in 0..self.simulations {
            self.simulate(root_game);
        }

        let root = &self.nodes[0];

        root.children
            .iter()
            .max_by_key(|&&child_idx| self.nodes[child_idx].visits)
            .map(|&best_child_idx| self.nodes[best_child_idx].mv.unwrap())
    }

    pub fn move_evaluations(&mut self, root_game: &G) -> Vec<(G::Move, f32, usize)> {
        let legal_moves = root_game.legal_moves();

        if legal_moves.is_empty() {
            return Vec::new();
        }

        self.nodes.clear();
        self.nodes.push(Node::new(None, None));

        for _ in 0..self.simulations {
            self.simulate(root_game);
        }

        let root = &self.nodes[0];

        root.children
            .iter()
            .map(|&child_idx| {
                let node = &self.nodes[child_idx];
                let mv = node.mv.unwrap();
                let win_rate = if node.visits > 0 {
                    node.total_reward / (node.visits as f32)
                } else {
                    0.0
                };
                (mv, win_rate, node.visits)
            })
            .collect()
    }
}

impl<G: Game> Agent<G> for MCTS<G> {
    fn select_move(&mut self, game: &G) -> Option<G::Move> {
        self.best_move(game)
    }

    fn name(&self) -> &str {
        "MCTS"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::game::player::Player;
    use crate::games::tictactoe::TicTacToe;

    const C: f32 = std::f32::consts::SQRT_2;

    #[test]
    fn basic() {
        let mut mcts = MCTS::new(100, C);
        let game = TicTacToe::new();
        let best_move = mcts.best_move(&game);
        assert!(best_move.is_some());
    }

    #[test]
    fn takes_immediate_win() {
        let mut game = TicTacToe::new();

        game.make_move(0); // p1
        game.make_move(3); // p2
        game.make_move(1); // etc...
        game.make_move(4);

        let mut mcts = MCTS::new(300, C);
        let chosen_move = mcts.best_move(&game);

        assert_eq!(chosen_move, Some(2));
    }

    #[test]
    fn blocks_opponent_win() {
        let mut game = TicTacToe::new();

        game.make_move(0);
        game.make_move(4);
        game.make_move(1);

        let mut mcts = MCTS::new(500, C);
        let chosen_move = mcts.best_move(&game);

        assert_eq!(chosen_move, Some(2));
    }

    #[test]
    fn mcts_crushes_random() {
        use crate::game::player::ai::random::RandomAgent;
        use crate::game::r#match::Match;
        use crate::game::Status;

        let mut mcts_wins = 0;
        let mut draws = 0;

        for _ in 0..20 {
            let game = TicTacToe::new();
            let p1 = MCTS::new(100, C);
            let p2 = RandomAgent::new();

            let mut m = Match::new(game, p1, p2);
            let summary = m.play_to_completion();

            match summary.status {
                Status::Win(Player::Player1) => mcts_wins += 1,
                Status::Draw => draws += 1,
                _ => {}
            }
        }

        // MCTS playing as Player1 against Random should win or draw virtually every game
        assert!(mcts_wins + draws >= 19);
    }
}
