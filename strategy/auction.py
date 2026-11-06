"""
Auction Engine for Sneak Peek Hold'em.
Implements game-theoretic second-price bidding strategy with Value of Information (VoI).
"""

from .opponent_model import OpponentModel
from core.game_state import RoundState
from core.equity import calculate_equity

class AuctionEngine:
    @staticmethod
    def calculate_bid(
        state: RoundState,
        opp_model: OpponentModel
    ) -> int:
        """
        Calculates optimal sealed bid for the Sneak Peek auction.
        """
        # 1. Penny Auction Exploit: If opponent consistently bids 0 or 1
        if opp_model.is_zero_bidder:
            return 1  # Wins their card for 0 chips!

        # 2. Hand strength and vulnerability analysis
        flop_equity = calculate_equity(state.my_cards, state.community_cards, num_simulations=40)
        pot = state.pot
        max_possible_bid = min(state.my_chips, state.opp_chips)

        # 3. VoI assessment:
        # If we have complete trash (equity < 0.20), don't spend chips on info
        if flop_equity < 0.20:
            return 1 if opp_model.median_opp_bid <= 1 else 0

        # If we have monster nuts (equity > 0.90), our play is already clear
        if flop_equity > 0.90:
            # Bid modestly to keep pot manageable or slightly undercut
            base_bid = int(0.08 * pot)
            return max(1, min(base_bid, max_possible_bid))

        # Close, contested, or drawing hands (equity 0.35 - 0.75):
        # Information is maximally valuable here to avoid expensive post-flop mistakes!
        # The value of info is proportional to pot size and variance
        ambiguity_factor = 1.0 - abs(flop_equity - 0.55) * 1.8
        ambiguity_factor = max(0.2, min(1.0, ambiguity_factor))

        # Target bid scaled with pot and opponent's median bid
        historical_median = opp_model.median_opp_bid
        if historical_median > 0:
            # Overbid opponent's median slightly to win Vickrey auction
            suggested_bid = int(historical_median + 2 + ambiguity_factor * 8)
        else:
            suggested_bid = int((0.15 + 0.15 * ambiguity_factor) * pot)

        # Cap bid conservatively relative to pot and stack
        # Bidding more than 40% of the pot on the flop is negative EV
        max_bid_cap = max(5, int(0.35 * pot))
        final_bid = max(1, min(suggested_bid, max_bid_cap, max_possible_bid))

        return int(final_bid)
