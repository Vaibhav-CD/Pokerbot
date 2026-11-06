"""
Post-Flop Strategy Engine (Flop, Turn, River).
Combines:
- Exact/Monte-Carlo conditioned equity on Sneak Peek revealed card.
- Pot Odds and Expected Value (EV).
- Exploitation of opponent tendencies (Calling Station vs Nit).
- Precise legal bet sizing using competition rules.
"""

from core.game_state import RoundState, BIG_BLIND
from core.equity import calculate_equity
from core.card import Card
from .opponent_model import OpponentModel

class PostflopEngine:
    @staticmethod
    def get_action(state: RoundState, opp_model: OpponentModel) -> tuple[str, int]:
        """
        Returns (action_type, amount)
        action_type in {'FOLD', 'CHECK', 'CALL', 'RAISE'}
        amount: raise TO amount if RAISE, else 0
        """
        cost = state.cost_to_call
        pot = state.pot
        can_raise = state.can_raise()
        min_r, max_r = state.legal_raise_bounds()

        # 1. Compute Equity conditioned on Sneak Peek information
        # 60 simulations is ultra-fast (< 1ms) and accurate
        equity = calculate_equity(
            state.my_cards,
            state.community_cards,
            opp_revealed_card=state.opp_revealed_card,
            num_simulations=60
        )

        # 2. Adjust for revealed card synergy if we won auction
        if state.opp_revealed_card is not None:
            opp_r = Card.rank(state.opp_revealed_card)
            board_ranks = [Card.rank(c) for c in state.community_cards]
            
            # If opponent's revealed card matches top card on board, give them credit for top pair
            if opp_r in board_ranks:
                # Their range is weighted towards strong hands
                equity = max(0.05, equity - 0.05)
            elif opp_r < min(board_ranks):
                # Opponent holds an undercard to board, range is weakened
                equity = min(0.95, equity + 0.05)

        # 3. Pot Odds threshold
        if cost > 0:
            pot_odds = cost / (pot + cost)
        else:
            pot_odds = 0.0

        # Adjust calling threshold based on opponent profile
        call_discount = 0.0
        if opp_model.is_tight_passive:
            # When a tight player bets, they have it! Be more conservative
            call_discount = -0.06
        elif opp_model.is_calling_station:
            # Calling stations don't fold, so don't bluff them
            call_discount = 0.02

        effective_equity = equity + call_discount

        # === 4. DECISION TREE ===

        # Scenario A: Facing a Bet or Raise (cost > 0)
        if cost > 0:
            # Monster Hand (Equity >= 0.82): Raise for value
            if effective_equity >= 0.82 and can_raise:
                target_raise = state.my_wager + cost + max(int(0.66 * pot), BIG_BLIND)
                clamped = state.clamp_raise(target_raise)
                if clamped >= min_r:
                    return ("RAISE", clamped)
                return ("CALL", 0)

            # Very Strong Hand (Equity >= 0.65): Call or Raise
            if effective_equity >= 0.65:
                if can_raise and effective_equity >= 0.75:
                    target_raise = state.my_wager + cost + max(int(0.50 * pot), BIG_BLIND)
                    clamped = state.clamp_raise(target_raise)
                    if clamped >= min_r:
                        return ("RAISE", clamped)
                return ("CALL", 0)

            # Profitable Call (Pot Odds satisfied)
            if effective_equity >= pot_odds:
                return ("CALL", 0)

            # Speculative Draw (Flop/Turn only, small bet to call)
            if state.street in ("FLOP", "TURN") and cost <= int(0.25 * pot) and effective_equity >= pot_odds - 0.08:
                return ("CALL", 0)

            # Unprofitable: Fold
            return ("FOLD", 0)

        # Scenario B: Unopened pot (cost == 0, Check is legal)
        else:
            # Monster Value (Equity >= 0.75): Bet for value
            if effective_equity >= 0.75 and can_raise:
                # Bet 60% of pot
                target_bet = state.my_wager + max(int(0.60 * pot), BIG_BLIND)
                clamped = state.clamp_raise(target_bet)
                if clamped >= min_r:
                    return ("RAISE", clamped)
                return ("CHECK", 0)

            # Medium Value (Equity 0.55 - 0.75): Bet 35%-45% of pot
            if effective_equity >= 0.58 and can_raise:
                target_bet = state.my_wager + max(int(0.40 * pot), BIG_BLIND)
                clamped = state.clamp_raise(target_bet)
                if clamped >= min_r:
                    return ("RAISE", clamped)
                return ("CHECK", 0)

            # Semi-bluff / C-Bet:
            # If opponent folds to c-bets easily and we have position or some equity
            if (
                opp_model.fold_to_cbet > 0.45
                and effective_equity >= 0.35
                and can_raise
                and state.street in ("FLOP", "TURN")
            ):
                target_bet = state.my_wager + max(int(0.33 * pot), BIG_BLIND)
                clamped = state.clamp_raise(target_bet)
                if clamped >= min_r:
                    return ("RAISE", clamped)

            # Default: Take free card with check
            return ("CHECK", 0)
