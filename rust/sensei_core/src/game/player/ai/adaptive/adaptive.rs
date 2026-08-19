use crate::game::player::agent::Agent;
use crate::game::player::ai::adaptive::student_profile::StudentProfile;
use crate::game::player::ai::core::mcts::MCTS;
use crate::game::Game;

pub struct AdaptiveSensei<G: Game> {
    pub mcts: MCTS<G>,
    pub student: StudentProfile,
    pub last_board: Option<G>,
}

impl<G: Game> AdaptiveSensei<G> {
    pub fn new(simulations: usize, c: f32) -> Self {
        Self {
            mcts: MCTS::new(simulations, c),
            student: StudentProfile::new(),
            last_board: None,
        }
    }

    pub fn observe_student_move(&mut self, game_before_move: &G, chosen_move: G::Move) {
        let evals = self.mcts.move_evaluations(game_before_move);
        let max_visits = evals
            .iter()
            .map(|(_, _, visits)| *visits)
            .max()
            .unwrap_or(1);

        if let Some((_, _, chosen_visits)) = evals.iter().find(|(mv, _, _)| *mv == chosen_move) {
            let error = Self::error_rate(*chosen_visits, max_visits);
            self.student.update(error);
        }
    }

    pub fn adaptive_move(&mut self, game: &G) -> Option<G::Move> {
        let evals = self.mcts.move_evaluations(game);

        if evals.is_empty() {
            return None;
        }

        let max_visits = evals
            .iter()
            .map(|(_, _, visits)| *visits)
            .max()
            .unwrap_or(1);
        let target_error = self.student.average_error();
        let temperature = self.student.consistency();

        let scored_moves: Vec<(G::Move, f32)> = evals
            .iter()
            .map(|(mv, _, visits)| {
                let error = Self::error_rate(*visits, max_visits);
                let distance = (error - target_error).abs();
                let score = (-distance / temperature).exp();
                (*mv, score)
            })
            .collect();

        let total_score: f32 = scored_moves.iter().map(|(_, s)| s).sum();

        if total_score == 0.0 {
            return Some(evals[0].0);
        }

        let mut sample = rand::random::<f32>() * total_score;

        for (mv, score) in scored_moves {
            sample -= score;

            if sample <= 0.0 {
                return Some(mv);
            }
        }

        Some(evals[0].0)
    }

    fn error_rate(visits: usize, max_visits: usize) -> f32 {
        1.0 - (visits as f32 / max_visits as f32)
    }
}

impl<G: Game> Agent<G> for AdaptiveSensei<G> {
    fn select_move(&mut self, game: &G) -> Option<G::Move> {
        if let Some(prev_game) = self.last_board.take() {
            let student_move = prev_game.legal_moves().into_iter().find(|&mv| {
                let mut test_game = prev_game.clone();
                test_game.make_move(mv);
                test_game == *game
            });

            if let Some(mv) = student_move {
                self.observe_student_move(&prev_game, mv);
            }
        }

        let chosen_move = self.adaptive_move(game)?;

        let mut next_game = game.clone();
        next_game.make_move(chosen_move);
        self.last_board = Some(next_game);

        Some(chosen_move)
    }

    fn name(&self) -> &str {
        "Sensei"
    }
}
