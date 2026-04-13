from agents import RandomPlayer, MCTSPlayer
from game import simulate_games
from analysis import analyze_phases
from visuals import play_visual_game


if __name__ == "__main__":
    VISUAL = True  # Set to True to see the board after each move
    p1 = MCTSPlayer(simulations=200)
    p2 = RandomPlayer()

    results = simulate_games(p1, p2, n_games=1, verbose=VISUAL)
    print("Finished", len(results), "games")

    avg_moves = sum(r["num_moves"] for r in results) / len(results)
    print("Average game length:", avg_moves)

    print("Example result:", results[0]["result"])
    print("\nPhase breakdown:")
    print(results[0]["phases"])
    print("\nFirst move debug:")
    print(results[0]["moves"][0])

    analysis = analyze_phases(results[0])

    print("\nPHASE ANALYSIS:")
    for phase, stats in analysis.items():
        print(f"\n{phase.upper()}:")
        print(f"  avg_error: {stats['avg_error']:.3f}")
        avg_error = stats['avg_error']
        consistency = stats['consistency']

        if avg_error is None:
            print("  avg_error: None")
            print("  consistency: None")
        else:
            print(f"  avg_error: {avg_error:.3f}")
            print(f"  consistency: {consistency:.3f}")

    