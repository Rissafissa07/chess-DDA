use sensei_core::game::player::ai::adaptive::AdaptiveSensei;
use sensei_core::game::{HumanAgent, Match};
use sensei_core::games::gomoku::Gomoku;

fn main() {
    let game = Gomoku::new();
    let human = HumanAgent::new("You");
    let ai = AdaptiveSensei::new(20000, std::f32::consts::SQRT_2);

    let mut m = Match::new(game, human, ai);
    let summary = m.play_to_completion();

    println!("{}", m.game);

    println!("Match Complete!");
    println!("Result: {:?}", summary.status);
    println!("Total moves: {}", summary.total_moves);

    println!(
        "Student profile: Avg error (μ) = {:.3}, Consistency (σ) = {:.3}",
        m.agent2.student.average_error(),
        m.agent2.student.consistency()
    );
}
