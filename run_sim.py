"""
Benchmark Simulation Suite for IIT Pokerbots 2026.
Runs 1,000 rounds against multiple opponent profiles,
measuring win rates, profit margins, and strict execution latency.
"""

from engine.game_engine import SneakPeekEngine
from bots.sneak_peek_bot import SneakPeekBot
from bots.baseline_bots import CallStationBot, HonestBidderBot, AggressiveBot

def run_benchmarks():
    print("=" * 65)
    print("IIT POKERBOTS 2026 - SNEAK PEEK HOLD'EM BENCHMARK SUITE")
    print("Rules: 1000 rounds, 5000 chips/round, 20s total time budget")
    print("=" * 65)

    opponents = [
        ("Calling Station (0-bid leak)", CallStationBot()),
        ("Honest Bidder (Tight ABC)", HonestBidderBot()),
        ("Aggressive Bot (Loose Aggressive)", AggressiveBot())
    ]

    for opp_name, opp_bot in opponents:
        print(f"\n---> Playing 1,000 rounds vs {opp_name}...")
        our_bot = SneakPeekBot(name="SneakPeekAI")
        engine = SneakPeekEngine(our_bot, opp_bot, num_rounds=1000)
        
        result = engine.play_match()

        print(f"Results vs {opp_name}:")
        print(f"  * Winner:              {result['winner']}")
        print(f"  * SneakPeekAI Bankroll: {result['bankroll1']:+d} chips")
        print(f"  * Opponent Bankroll:    {result['bankroll2']:+d} chips")
        print(f"  * SneakPeekAI Time:     {result['time1_seconds']:.3f} s / 20.0 s budget")
        print(f"  * Opponent Time:        {result['time2_seconds']:.3f} s")
        
        # Validation checks
        assert result['time1_seconds'] < 20.0, f"FAILED TIME LIMIT: {result['time1_seconds']}s exceeds 20s"
        assert result['bankroll1'] > 0, f"SneakPeekAI was expected to be profitable vs {opp_name}"
        print(f"  [PASS] Completed well within time limit and won profitably!")

    print("\n" + "=" * 65)
    print("ALL BENCHMARK MATCHES COMPLETED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_benchmarks()
