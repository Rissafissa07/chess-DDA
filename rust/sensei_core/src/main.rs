use sensei_core::core::game::Game;
use sensei_core::core::player::Player;
use sensei_core::games::tictactoe::TicTacToe;

use sensei_core::engine::mcts::MCTS;

use std::io::{self, Write};

fn main() {
    println!("==============================");
    println!("           TIC-TAC-TOE        ");
    println!("==============================");

    let mut game = TicTacToe::new();
    let mut ai = MCTS::new(1000, std::f32::consts::SQRT_2);

    while !game.is_terminal() {
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
                    game.make_move(mv);
                }
                _ => {
                    println!("Invalid move! Legal moves are: {:?}", game.legal_moves());
                }
            }
        } else {
            println!("AI (O) is thinking...");

            if let Some(ai_move) = ai.best_move(&game) {
                println!("AI chose square: {}", ai_move);
                game.make_move(ai_move);
            }
        }
    }

    game.display_board();
    let winner = if game.reward(Player::Player1) == 1.0 {
        "You (X)"
    } else if game.reward(Player::Player2) == 1.0 {
        "AI (O)"
    } else {
        "DRAW!"
    };

    println!("Winner: {}", winner);
}
