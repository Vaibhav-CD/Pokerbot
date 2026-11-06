"""
Baseline bots for benchmarking and regression testing.
"""

import random
from .base_bot import BaseBot
from core.game_state import RoundState, BIG_BLIND

class CallStationBot(BaseBot):
    """Calling station that always checks or calls and bids 0 in auction."""
    def __init__(self, name: str = "CallStation"):
        super().__init__(name)

    def handle_new_round(self, round_num: int, is_sb: bool, my_cards: list[int]):
        pass

    def handle_auction_query(self, state: RoundState) -> int:
        return 0  # Typical flawed bot bidding 0

    def handle_action_query(self, state: RoundState) -> tuple[str, int]:
        if state.cost_to_call == 0:
            return ("CHECK", 0)
        return ("CALL", 0)

    def handle_auction_result(self, won_auction, my_bid, opp_bid, opp_revealed_card, my_revealed_card):
        pass

    def handle_round_over(self, state: RoundState, chip_delta: int, opp_cards: list[int] | None = None):
        pass


class HonestBidderBot(BaseBot):
    """Plays tight-aggressive ABC poker and bids a fixed modest amount."""
    def __init__(self, name: str = "HonestBidder"):
        super().__init__(name)

    def handle_new_round(self, round_num: int, is_sb: bool, my_cards: list[int]):
        pass

    def handle_auction_query(self, state: RoundState) -> int:
        return min(25, int(0.20 * state.pot))

    def handle_action_query(self, state: RoundState) -> tuple[str, int]:
        cost = state.cost_to_call
        min_r, max_r = state.legal_raise_bounds()
        
        # Simple rule: if cost == 0, 50% bet, 50% check
        if cost == 0:
            if max_r >= min_r and random.random() < 0.4:
                return ("RAISE", min_r)
            return ("CHECK", 0)
        else:
            if cost > 150:
                return ("FOLD", 0)
            return ("CALL", 0)

    def handle_auction_result(self, won_auction, my_bid, opp_bid, opp_revealed_card, my_revealed_card):
        pass

    def handle_round_over(self, state: RoundState, chip_delta: int, opp_cards: list[int] | None = None):
        pass


class AggressiveBot(BaseBot):
    """Bluffs frequently and bids aggressively in auction."""
    def __init__(self, name: str = "AggressiveBot"):
        super().__init__(name)

    def handle_new_round(self, round_num: int, is_sb: bool, my_cards: list[int]):
        pass

    def handle_auction_query(self, state: RoundState) -> int:
        return min(state.my_chips, max(10, int(0.35 * state.pot)))

    def handle_action_query(self, state: RoundState) -> tuple[str, int]:
        cost = state.cost_to_call
        min_r, max_r = state.legal_raise_bounds()
        
        if max_r >= min_r and random.random() < 0.65:
            # Raise
            target = min(max_r, min_r + BIG_BLIND * 2)
            return ("RAISE", target)
            
        if cost == 0:
            return ("CHECK", 0)
        if cost > 300 and random.random() < 0.5:
            return ("FOLD", 0)
        return ("CALL", 0)

    def handle_auction_result(self, won_auction, my_bid, opp_bid, opp_revealed_card, my_revealed_card):
        pass

    def handle_round_over(self, state: RoundState, chip_delta: int, opp_cards: list[int] | None = None):
        pass
