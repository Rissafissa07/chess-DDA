use std::collections::VecDeque;

#[derive(Debug, Clone)]
pub struct StudentProfile {
    pub errors: VecDeque<f32>,
    max_history: usize,
}

impl StudentProfile {
    pub fn new() -> Self {
        Self::with_capacity(20)
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            errors: VecDeque::with_capacity(capacity),
            max_history: capacity,
        }
    }

    pub fn update(&mut self, error: f32) {
        if self.errors.len() >= self.max_history {
            self.errors.pop_front();
        }

        self.errors.push_back(error);
    }

    pub fn average_error(&self) -> f32 {
        if self.errors.is_empty() {
            return 0.0;
        }

        self.errors.iter().sum::<f32>() / (self.errors.len() as f32)
    }

    pub fn consistency(&self) -> f32 {
        if self.errors.len() < 2 {
            return 0.1; // default starting consistency
        }

        let avg = self.average_error();
        let variance =
            self.errors.iter().map(|e| (e - avg).powi(2)).sum::<f32>() / (self.errors.len() as f32);

        variance.sqrt().max(0.05)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MAX_ERROR_DIFF: f32 = 1e-6;

    #[test]
    fn correct_average_error() {
        let mut student = StudentProfile::new();

        student.update(0.8);
        student.update(0.1);

        let diff = (student.average_error() - 0.45).abs();
        assert!(diff < MAX_ERROR_DIFF);
    }

    #[test]
    fn rolling_window_eviction() {
        let mut student = StudentProfile::with_capacity(3);

        student.update(1.0);
        student.update(0.2);
        student.update(0.4);
        student.update(0.6);
        assert_eq!(student.errors.len(), 3);

        let diff = (student.average_error() - 0.4).abs();
        assert!(diff < MAX_ERROR_DIFF);
    }
}
