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

        # Per-hand action flags (reset via new_hand each round)
        self.pf_vpip_this_hand = False
        self.pf_raise_this_hand = False

    def new_hand(self):
        self.pf_vpip_this_hand = False
        self.pf_raise_this_hand = False

    def record_auction_bid(self, bid: int):
        self.opp_bids.append(bid)
        if bid <= 1:
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

    def observe(self, street: str, action_type: str, faced_bet: bool = False):
        """Route one observed opponent action into preflop/postflop stats."""
        if street == "PREFLOP":
            self.record_preflop_action(action_type, faced_raise=faced_bet)
            if action_type in ("CALL", "RAISE"):
                self.pf_vpip_this_hand = True
            if action_type == "RAISE":
                self.pf_raise_this_hand = True
        elif street in ("FLOP", "TURN", "RIVER"):
            self.record_postflop_action(action_type, faced_bet=faced_bet)

    @property
    def postflop_aggro_rate(self) -> float:
        """Fraction of postflop actions that are bets/raises."""
        total = self.opp_bets_raises + self.opp_calls + self.opp_folds_postflop
        if total == 0:
            return 0.30
        return self.opp_bets_raises / total

    def estimated_range_width(self, villain_raised: bool) -> float:
        """Estimate villain's range width (fraction of all hands) for this hand."""
        if villain_raised:
            return max(0.08, min(0.60, self.pfr))
        width = self.vpip - 0.5 * self.pfr
        return max(0.10, min(0.95, width))

    @property
    def is_calling_station(self) -> bool:
        """High VPIP and rarely folds postflop."""
        return self.vpip > 0.65 and self.fold_to_cbet < 0.25

    @property
    def is_tight_passive(self) -> bool:
        """Low VPIP and folds easily."""
        return self.vpip < 0.35 or self.fold_to_steal > 0.65
