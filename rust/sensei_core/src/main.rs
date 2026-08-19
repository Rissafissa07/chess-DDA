use sensei_core::game::player::ai::adaptive::AdaptiveSensei;
use sensei_core::game::player::Player;
use sensei_core::game::Game;
use sensei_core::game::Status;
use sensei_core::games::tictactoe::TicTacToe;

use std::io::{self, Write};

fn main() {
    println!("=============================");
    println!("          TIC-TAC-TOE        ");
    println!("=============================");

    let mut game = TicTacToe::new();
    let mut ai = AdaptiveSensei::new(1000, std::f32::consts::SQRT_2);

    while game.status().is_ongoing() {
        game.display_board();

        if game.current_player() == Player::Player1 {
            print!("Your turn (X), enter move (0-8): ");
            io::stdout().flush().unwrap();

            let mut input = String::new();

            io::stdin()
                .read_line(&mut input)
                .expect("Failed to read input");

            match input.trim().parse::<usize>() {
                Ok(mv) if game.legal_moves().contains(&mv) => {
                    ai.observe_student_move(&game, mv);
                    game.make_move(mv);
                }
                _ => {
                    println!("Invalid move! Legal moves are: {:?}", game.legal_moves());
                }
            }
        } else {
            println!("Sensei (O) is thinking...");

            println!(
                "Student stats: Avg error (μ) = {:.3}, Consistency (σ) = {:.3}",
                ai.student.average_error(),
                ai.student.consistency()
            );

            if let Some(ai_move) = ai.adaptive_move(&game) {
                println!("AI chose square: {}", ai_move);
                game.make_move(ai_move);
            }
        }
    }

    game.display_board();
    let winner = match game.status() {
        Status::Win(Player::Player1) => "You (X)",
        Status::Win(Player::Player2) => "Sensei (O)",
        Status::Draw => "DRAW!",
        Status::Ongoing => "Ongoing",
    };

    println!(
        "Final student profile: μ = {:.3}, σ = {:.3}",
        ai.student.average_error(),
        ai.student.consistency()
    );

    println!("Winner: {}", winner);
}
