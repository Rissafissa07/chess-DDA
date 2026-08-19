use std::fmt::Debug;

#[derive(Debug, Clone)]
pub struct Node<M> {
    pub mv: Option<M>,
    pub parent: Option<usize>,
    pub children: Vec<usize>,
    pub visits: usize,
    pub total_reward: f32,
}

impl<M: Copy + PartialEq + Debug> Node<M> {
    pub fn new(mv: Option<M>, parent: Option<usize>) -> Self {
        Self {
            mv,
            parent,
            children: Vec::new(),
            visits: 0,
            total_reward: 0.0,
        }
    }

    /// computes the Upper Confidence Bound (UCT) score.
    /// if `is_root_player` is true, we maximise win rate.
    /// if `is_root_player` is false (opponent's turn), we invert it (1.0 - win_rate).
    pub fn uct_score(&self, parent_visits: usize, c: f32, is_root_player: bool) -> f32 {
        if self.visits == 0 {
            return f32::INFINITY;
        }

        let raw_win_rate = self.total_reward / (self.visits as f32);
        let exploitation = if is_root_player {
            raw_win_rate
        } else {
            1.0 - raw_win_rate
        };

        let exploration = c * ((parent_visits as f32).ln() / (self.visits as f32)).sqrt();
        exploitation + exploration
    }
}
