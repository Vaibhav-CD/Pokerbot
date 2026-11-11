"""
Auction Engine for Sneak Peek Hold'em.
Implements game-theoretic second-price bidding strategy with Value of Information (VoI)
and the Pot-Share Rebate Theorem.
"""

from .opponent_model import OpponentModel
from core.game_state import RoundState
from core.equity import calculate_range_equity

class AuctionEngine:
    @staticmethod
    def calculate_bid(
        state: RoundState,
        opp_model: OpponentModel
    ) -> int:
        """
        Calculates optimal sealed bid for the Sneak Peek auction using:
        1. Penny Auction Leak Exploit (bidding 1 against zero-bidders).
        2. Pot-Share Rebate: Net cost = (1 - Equity) * Payment.
        3. Marginal Value of Information (VoI) based on hand ambiguity and pot size.
        """
        # 1. Penny Auction Exploit: If opponent consistently bids 0 or 1
        if opp_model.is_zero_bidder:
            return 1  # Wins opponent's card for 0 chips!

        # 2. Hand strength vs villain's estimated range
        flop_equity = calculate_range_equity(
            state.my_cards, state.community_cards, opp_model,
            villain_raised_preflop=opp_model.pf_raise_this_hand,
            num_simulations=32,
        )
        pot = state.pot
        max_possible_bid = min(state.my_chips, state.opp_chips)
        median_bid = opp_model.median_opp_bid

        # 3. Categorized VoI with Pot-Share Rebate Theorem:
        # Expected Net Cost to Winner = (1 - FlopEquity) * Payment

        # Category A: Hopeless Trash (equity < 0.20)
        # Info is worthless to us, but we bid 1-2 chips to tax the opponent
        # (if opponent bids 2+, we pay 0 and they pay our tax into the pot).
        if flop_equity < 0.20:
            tax = 2 if median_bid > 5 else 1
            return max(1, min(tax, max_possible_bid))

        # Category B: Absolute Monster (equity > 0.88)
        # We already have dominant showdown value.
        # Primary goal is information denial: prevent villain from finding out they are crushed!
        # With high equity (e.g. 90%), our rebate is 90% (net cost is only 10% of bid!).
        if flop_equity > 0.88:
            rebate_discount = 1.0 - flop_equity # ~0.10
            # Target bid to safely beat villain's median bid
            target = max(int(0.12 * pot), median_bid + 3)
            return max(1, min(target, max_possible_bid))

        # Category C: Contested, Drawing, & Volatile Hands (equity 0.20 - 0.88)
        # Value of Information is maximized here!
        # Ambiguity peak is at 50% equity (1.0), tapering down towards edges.
        ambiguity = 1.0 - abs(flop_equity - 0.50) * 1.6
        ambiguity = max(0.25, min(1.0, ambiguity))

        # Gross Value of Information in chips:
        # Seeing 1 card reduces entropy by 95.7%, avoiding costly mistakes on turn/river.
        voi_chips = pot * (0.12 + 0.18 * ambiguity)

        # Apply Pot-Share Rebate:
        # Since net cost is (1 - P_win) * Payment, our willingness to bid increases with equity!
        rebate_multiplier = 1.0 / max(0.30, (1.0 - flop_equity))
        willingness_to_bid = int(voi_chips * min(1.6, rebate_multiplier * 0.75))

        # Strategic positioning relative to opponent's median bid:
        if median_bid > 0:
            # Overbid opponent's median bid by a strategic margin to secure the card
            # at their lower price!
            strategic_bid = max(willingness_to_bid, median_bid + 2 + int(ambiguity * 5))
        else:
            strategic_bid = willingness_to_bid

        # Conservative ceiling: Never risk more than 35% of the pot on flop auction
        max_bid_cap = max(5, int(0.35 * pot))
        final_bid = max(1, min(strategic_bid, max_bid_cap, max_possible_bid))

        return int(final_bid)
