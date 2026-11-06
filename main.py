"""
Main Entry Point for IIT Pokerbots 2026 - Sneak Peek Hold'em.
Usage:
    python main.py --sim             Run local benchmark simulations (1000 rounds)
    python main.py --demo            Play a short interactive 5-round demo match
"""

import sys
import argparse
from bots.sneak_peek_bot import SneakPeekBot
from bots.baseline_bots import CallStationBot, HonestBidderBot, AggressiveBot
from engine.game_engine import SneakPeekEngine

def run_demo(num_rounds: int = 5):
    print("=" * 60)
    print(f"RUNNING DEMO MATCH ({num_rounds} ROUNDS)")
    print("=" * 60)
    bot = SneakPeekBot("SneakPeekAI")
    opp = HonestBidderBot("HonestBidder")
    engine = SneakPeekEngine(bot, opp, num_rounds=num_rounds)
    res = engine.play_match()
    print(f"Match Finished!")
    print(f"SneakPeekAI Bankroll: {res['bankroll1']:+d}")
    print(f"Opponent Bankroll:    {res['bankroll2']:+d}")
    print(f"Total time used:      {res['time1_seconds']:.4f} s")

def main():
    parser = argparse.ArgumentParser(description="IIT Pokerbots 2026 - Sneak Peek Hold'em AI")
    parser.add_argument("--sim", action="store_true", help="Run full 1,000-round benchmark against baselines")
    parser.add_argument("--demo", action="store_true", help="Run short 5-round demo")
    parser.add_argument("--rounds", type=int, default=1000, help="Number of rounds for simulation")
    
    args = parser.parse_args()

    if args.demo:
        run_demo(args.rounds if args.rounds != 1000 else 5)
    elif args.sim or len(sys.argv) == 1:
        from run_sim import run_benchmarks
        run_benchmarks()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
