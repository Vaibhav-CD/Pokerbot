"""
Game State tracking & Bet Legality Verification for Sneak Peek Hold'em.
"""

from dataclasses import dataclass, field
from .card import Card

BIG_BLIND = 20
SMALL_BLIND = 10
STARTING_STACK = 5000

@dataclass
class RoundState:
    round_num: int = 1
    is_sb: bool = True  # True if Small Blind (acts 1st preflop, 2nd postflop)
    my_chips: int = STARTING_STACK
    opp_chips: int = STARTING_STACK
    pot: int = 0
    street: str = "PREFLOP"  # PREFLOP, FLOP, TURN, RIVER
    my_cards: list[int] = field(default_factory=list)
    community_cards: list[int] = field(default_factory=list)
    
    # Betting round wagers
    my_wager: int = 0
    opp_wager: int = 0
    
    # Auction information
    auction_complete: bool = False
    my_bid: int = 0
    opp_bid: int | None = None
    won_auction: bool = False
    opp_revealed_card: int | None = None
    my_revealed_card: int | None = None

    @property
    def cost_to_call(self) -> int:
        return max(0, self.opp_wager - self.my_wager)

    def legal_raise_bounds(self) -> tuple[int, int]:
        """
        Calculates exact legal min_raise and max_raise (raise TO amount)
        according to the competition rule:
        Minimum Raise = Current Wager + Cost to Call + max(Big Blind, Cost to Call)
        Maximum Raise = min(Your Chips, Opponent's Chips)
        """
        cost = self.cost_to_call
        min_raise = self.my_wager + cost + max(BIG_BLIND, cost)
        max_raise = min(self.my_chips, self.opp_chips)
        return int(min_raise), int(max_raise)

    def can_raise(self) -> bool:
        min_r, max_r = self.legal_raise_bounds()
        return max_r >= min_r

    def is_check_legal(self) -> bool:
        return self.cost_to_call == 0

    def clamp_raise(self, target_amount: int) -> int:
        """Clamps a target raise TO amount to strictly legal bounds."""
        min_r, max_r = self.legal_raise_bounds()
        if max_r < min_r:
            # Cannot raise, must call or check
            return -1
        return max(min_r, min(int(target_amount), max_r))
