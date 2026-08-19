#[derive(Debug, Clone)]
pub struct StudentProfile {
    pub errors: Vec<f32>,
}

impl StudentProfile {
    pub fn new() -> Self {
        Self { errors: Vec::new() }
    }

    pub fn update(&mut self, error: f32) {
        self.errors.push(error);
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

    #[test]
    fn correct_average_error() {
        let mut student = StudentProfile::new();

        student.update(0.8);
        student.update(0.1);

        let diff = (student.average_error() - 0.45).abs();
        assert!(diff < 1e-5); // put into error reate variable
    }
}
