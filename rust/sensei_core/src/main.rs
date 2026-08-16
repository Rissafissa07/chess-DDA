use std::io::{self, Write};
use sensei_core::core::game::Game;
use sensei_core::core::player::Player;
use sensei_core::games::tictactoe::TicTacToe;

fn main() {
    println!("==============================");
    println!("           TIC-TAC-TOE        ");
    println!("==============================");

    let mut game = TicTacToe::new();

    while !game.is_terminal() {
        game.display_board();

        let current = game.current_player();
        let symbol = if current == Player::Player1 { "X" } else { "O" };

        print!("Player {:?} ({}), enter move (0-8): ", current, symbol);
        io::stdout().flush().unwrap();

        let mut input = String::new();
        io::stdin().read_line(&mut input).expect("Failed to read input");

        match input.trim().parse::<usize>() {
            Ok(mv) if game.legal_moves().contains(&mv) => {
                game.make_move(mv);
            }
            _ => {
                println!("Invalid move! Legal moves are: {:?}", game.legal_moves());
            }
        }
    }

    game.display_board();
    let winner =
        if game.reward(Player::Player1) == 1.0 { "Player 1 (X)" }
        else if game.reward(Player::Player2) == 1.0 { "Player 2 (O)" }
        else { "DRAW!" };

    println!("Winner: {}", winner);
}
