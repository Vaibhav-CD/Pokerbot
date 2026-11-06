"""
Adaptive Opponent Modeling & Exploitation Engine.
Tracks running statistics across 1,000 hands and identifies leaks:
- Preflop: VPIP, PFR, fold to raise.
- Auction: Bid distribution, zero-bid frequency, median bid.
- Postflop: Aggression factor, fold to bet frequency.
"""

class OpponentModel:
    def __init__(self):
        self.total_hands = 0
        
        # Preflop tracking
        self.opp_vpip_count = 0
        self.opp_pfr_count = 0
        self.opp_faced_raise_count = 0
        self.opp_folded_to_raise_count = 0
        
        # Auction tracking
        self.opp_bids: list[int] = []
        self.opp_zero_bids = 0
        
        # Postflop tracking
        self.opp_bets_raises = 0
        self.opp_calls = 0
        self.opp_folds_postflop = 0
        self.opp_faced_postflop_bets = 0

    def record_auction_bid(self, bid: int):
        self.opp_bids.append(bid)
        if bid == 0:
            self.opp_zero_bids += 1

    def record_preflop_action(self, action_type: str, faced_raise: bool = False):
        if action_type in ("CALL", "RAISE"):
            self.opp_vpip_count += 1
        if action_type == "RAISE":
            self.opp_pfr_count += 1
        if faced_raise:
            self.opp_faced_raise_count += 1
            if action_type == "FOLD":
                self.opp_folded_to_raise_count += 1

    def record_postflop_action(self, action_type: str, faced_bet: bool = False):
        if action_type in ("BET", "RAISE"):
            self.opp_bets_raises += 1
        elif action_type == "CALL":
            self.opp_calls += 1
        elif action_type == "FOLD":
            self.opp_folds_postflop += 1
            
        if faced_bet:
            self.opp_faced_postflop_bets += 1

    # Computed metrics
    @property
    def vpip(self) -> float:
        if self.total_hands == 0:
            return 0.50
        return self.opp_vpip_count / self.total_hands

    @property
    def pfr(self) -> float:
        if self.total_hands == 0:
            return 0.25
        return self.opp_pfr_count / self.total_hands

    @property
    def fold_to_steal(self) -> float:
        if self.opp_faced_raise_count == 0:
            return 0.40
        return self.opp_folded_to_raise_count / self.opp_faced_raise_count

    @property
    def fold_to_cbet(self) -> float:
        if self.opp_faced_postflop_bets == 0:
            return 0.40
        return self.opp_folds_postflop / self.opp_faced_postflop_bets

    @property
    def median_opp_bid(self) -> int:
        if not self.opp_bids:
            return 10  # baseline assumption
        sorted_bids = sorted(self.opp_bids)
        return sorted_bids[len(sorted_bids) // 2]

    @property
    def is_zero_bidder(self) -> bool:
        """Returns True if opponent consistently bids 0 or 1 in auction."""
        if len(self.opp_bids) >= 3:
            return (self.opp_zero_bids / len(self.opp_bids)) > 0.60
        return False

    @property
    def is_calling_station(self) -> bool:
        """High VPIP and rarely folds postflop."""
        return self.vpip > 0.65 and self.fold_to_cbet < 0.25

    @property
    def is_tight_passive(self) -> bool:
        """Low VPIP and folds easily."""
        return self.vpip < 0.35 or self.fold_to_steal > 0.65
