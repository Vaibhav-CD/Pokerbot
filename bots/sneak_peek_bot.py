"""
SneakPeekBot - Championship AI for IIT Pokerbots 2026.
Features:
- Fast bitwise card evaluation and exact post-auction equity conditioning.
- Second-price auction bidding with Value of Information (VoI).
- Deep-stack preflop chart and position exploitation.
- Adaptive opponent profiling (VPIP, PFR, CBet fold, auction bid tracking).
- Strict legality guard preventing any invalid action or timeout.
"""

from .base_bot import BaseBot
from core.game_state import RoundState, BIG_BLIND
from strategy.auction import AuctionEngine
from strategy.preflop import PreflopEngine
from strategy.postflop import PostflopEngine
from strategy.opponent_model import OpponentModel

class SneakPeekBot(BaseBot):
    def __init__(self, name: str = "SneakPeekAI"):
        super().__init__(name)
        self.opp_model = OpponentModel()
        self.current_cards: list[int] = []

    def handle_new_round(self, round_num: int, is_sb: bool, my_cards: list[int]):
        self.current_cards = list(my_cards)
        self.opp_model.total_hands += 1

    def handle_auction_query(self, state: RoundState) -> int:
        try:
            bid = AuctionEngine.calculate_bid(state, self.opp_model)
            # Legality check: non-negative integer <= stack
            max_bid = min(state.my_chips, state.opp_chips)
            clamped = max(0, min(int(bid), max_bid))
            return clamped
        except Exception:
            return 1  # Safe minimum fallback

    def handle_action_query(self, state: RoundState) -> tuple[str, int]:
        try:
            if state.street == "PREFLOP":
                action, amount = PreflopEngine.get_action(state, self.opp_model)
            else:
                action, amount = PostflopEngine.get_action(state, self.opp_model)

            # Bulletproof validation
            cost = state.cost_to_call
            min_r, max_r = state.legal_raise_bounds()

            if action == "RAISE":
                if max_r < min_r or amount < min_r:
                    # Illegal raise: degrade to CALL or CHECK
                    if cost == 0:
                        return ("CHECK", 0)
                    else:
                        return ("CALL", 0)
                amount = max(min_r, min(int(amount), max_r))
                return ("RAISE", amount)

            elif action == "CHECK":
                if cost > 0:
                    # Check is illegal when facing a bet, default to CALL or FOLD
                    return ("CALL", 0) if cost <= BIG_BLIND else ("FOLD", 0)
                return ("CHECK", 0)

            elif action == "CALL":
                if cost == 0:
                    return ("CHECK", 0)
                return ("CALL", 0)

            elif action == "FOLD":
                if cost == 0:
                    return ("CHECK", 0)
                return ("FOLD", 0)

            # Default safe
            return ("CHECK", 0) if cost == 0 else ("CALL", 0)
        except Exception:
            # Absolute safety fallback
            if state.cost_to_call == 0:
                return ("CHECK", 0)
            return ("FOLD", 0)

    def handle_auction_result(
        self,
        won_auction: bool,
        my_bid: int,
        opp_bid: int | None,
        opp_revealed_card: int | None,
        my_revealed_card: int | None
    ):
        if opp_bid is not None:
            self.opp_model.record_auction_bid(opp_bid)

    def handle_round_over(self, state: RoundState, chip_delta: int, opp_cards: list[int] | None = None):
        # We can update opponent profile here if showdown cards are revealed
        pass
