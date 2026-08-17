#[derive(Debug, Clone)]
pub struct Node<M> {
    pub mv: Option<M>,
    pub parent: Option<usize>,
    pub children: Vec<usize>,
    pub visits: usize,
    pub total_reward: f32,
}

impl<M: Copy> Node<M> {
    pub fn new(mv: Option<M>, parent: Option<usize>) -> Self {
        Self {
            mv,
            parent,
            children: Vec::new(),
            visits: 0,
            total_reward: 0.0,
        }
    }

    pub fn uct_score(&self, parent_visits: usize, c:f32) -> f32 {
        if self.visits == 0 {
            return f32::INFINITY;
        }

        let exploration = c * ((parent_visits as f32).ln() / (self.visits as f32)).sqrt();
        let exploitation = self.total_reward / (self.visits as f32);

        exploitation + exploration
    }

    
}
