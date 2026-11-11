"""
Card Removal and Blocker Analysis Engine.
Computes blocker metrics to optimize bluffing, value-betting, and bluff-catching:
- Nut flush blockers (e.g. holding the Ace of the flush suit)
- Straight connectivity blockers (blocking open-ended straight draws)
- Board pair blockers (reducing villain's sets and top pair combinations)
"""

from dataclasses import dataclass
from core.card import Card

@dataclass
class BlockerReport:
    nut_flush_blocker: bool = False
    second_nut_flush_blocker: bool = False
    flush_suit: int | None = None
    straight_blocker_score: float = 0.0
    top_pair_blocker: bool = False
    bluff_equity_boost: float = 0.0
    bluff_catch_boost: float = 0.0

def analyze_blockers(my_cards: list[int], community_cards: list[int]) -> BlockerReport:
    """
    Analyzes card removal effects of my_cards given the community_cards.
    """
    report = BlockerReport()
    if not community_cards or len(my_cards) < 2:
        return report

    my_ranks = [Card.rank(c) for c in my_cards]
    my_suits = [Card.suit(c) for c in my_cards]
    comm_ranks = [Card.rank(c) for c in community_cards]
    comm_suits = [Card.suit(c) for c in community_cards]

    # --- 1. FLUSH BLOCKERS ---
    # Check if there is a flush draw or completed flush on board (>= 2 cards of same suit)
    suit_counts = [0, 0, 0, 0]
    for s in comm_suits:
        suit_counts[s] += 1

    for s, cnt in enumerate(suit_counts):
        if cnt >= 3:
            # 3 or 4 cards to a flush on board! Nut flush blocker is massive!
            report.flush_suit = s
            # Check if we hold the Ace (rank 12) or King (rank 11) of suit s
            for c in my_cards:
                if Card.suit(c) == s:
                    if Card.rank(c) == 12: # Ace of flush suit
                        report.nut_flush_blocker = True
                        report.bluff_equity_boost += 0.08
                    elif Card.rank(c) == 11: # King of flush suit
                        report.second_nut_flush_blocker = True
                        report.bluff_equity_boost += 0.04
        elif cnt == 2 and len(community_cards) <= 4:
            # Flop/turn 2-card flush draw
            for c in my_cards:
                if Card.suit(c) == s and Card.rank(c) == 12:
                    report.nut_flush_blocker = True
                    report.bluff_equity_boost += 0.03

    # --- 2. STRAIGHT BLOCKERS ---
    # Look for boards with connected ranks (e.g., T-9-8 or 8-7-6)
    unique_comm_ranks = sorted(set(comm_ranks))
    if len(unique_comm_ranks) >= 3:
        # Check gaps between consecutive cards
        for i in range(len(unique_comm_ranks) - 2):
            span = unique_comm_ranks[i+2] - unique_comm_ranks[i]
            if span <= 4: # Connected 3-card straight texture
                # Holding cards that bridge or cap this straight blocks villain's straights
                for mr in my_ranks:
                    if unique_comm_ranks[i] - 2 <= mr <= unique_comm_ranks[i+2] + 2:
                        report.straight_blocker_score += 0.04
                        report.bluff_equity_boost += 0.02

    # --- 3. TOP PAIR / SET BLOCKERS ---
    max_board_rank = max(comm_ranks)
    if max_board_rank in my_ranks:
        # We hold one card matching top card of the board!
        # This cuts the opponent's combos of top pair from 12 down to 6, and sets from 3 down to 1!
        report.top_pair_blocker = True
        # If we are bluff-catching or evaluating villain's aggression:
        report.bluff_catch_boost += 0.04

    # Cap boosts safely
    report.bluff_equity_boost = min(0.12, report.bluff_equity_boost)
    report.bluff_catch_boost = min(0.08, report.bluff_catch_boost)

    return report
