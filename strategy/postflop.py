"""
Optimized Post-Flop Strategy Engine (Flop, Turn, River).
Combines:
- Conditioned Range-vs-Range Monte Carlo Equity (Sneak Peek revealed card integration).
- Card Removal & Blocker Analysis (Nut flush blockers, straight blockers, board blockers).
- Stack-to-Pot Ratio (SPR) & Multi-Street Geometric Bet Sizing.
- Opponent Profiling (Calling station exploitation vs nit exploitation).
- Strict competition raise legality bounds.
"""

from core.game_state import RoundState, BIG_BLIND
from core.equity import calculate_range_equity
from core.blockers import analyze_blockers
from strategy.pot_geometry import get_optimal_bet_size, calculate_spr
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

        # 1. Range-vs-range equity conditioned on villain's range & revealed card
        num_sims = 40 if state.street == "RIVER" else 48
        equity = calculate_range_equity(
            state.my_cards,
            state.community_cards,
            opp_model,
            opp_revealed_card=state.opp_revealed_card,
            villain_raised_preflop=opp_model.pf_raise_this_hand,
            facing_bet=cost > 0,
            num_simulations=num_sims
        )

        # 2. Card Removal & Blocker Analysis
        blockers = analyze_blockers(state.my_cards, state.community_cards)

        # 3. Pot Odds threshold
        pot_odds = (cost / (pot + cost)) if cost > 0 else 0.0

        # 4. Opponent Profiler & Blocker EV adjustments
        call_discount = 0.0
        if opp_model.is_tight_passive:
            # Tight passive players rarely bet without monster holdings
            call_discount -= 0.06
        elif opp_model.is_calling_station:
            # Calling stations call down light, so we call lighter and bet bigger
            call_discount += 0.02

        # Blocker boost for bluff-catching (e.g. we hold the Ace of the flush suit)
        if cost > 0 and blockers.nut_flush_blocker:
            call_discount += 0.04
        if cost > 0 and blockers.top_pair_blocker:
            call_discount += 0.03

        effective_equity = equity + call_discount

        # === 5. DECISION TREE ===

        # --- SCENARIO A: FACING A BET OR RAISE (cost > 0) ---
        if cost > 0:
            # Monster Holding (Effective Equity >= 0.82): Raise for geometric value
            if effective_equity >= 0.82 and can_raise:
                opt_bet = get_optimal_bet_size(
                    state.street, state.my_chips, state.opp_chips, pot, effective_equity,
                    is_calling_station=opp_model.is_calling_station
                )
                target_raise = state.my_wager + cost + max(opt_bet, BIG_BLIND)
                clamped = state.clamp_raise(target_raise)
                if clamped >= min_r:
                    return ("RAISE", clamped)
                return ("CALL", 0)

            # Very Strong Holding (Effective Equity 0.66 - 0.82)
            if effective_equity >= 0.66:
                if can_raise and effective_equity >= 0.74 and not opp_model.is_tight_passive:
                    opt_bet = get_optimal_bet_size(
                        state.street, state.my_chips, state.opp_chips, pot, effective_equity,
                        is_calling_station=opp_model.is_calling_station
                    )
                    target_raise = state.my_wager + cost + max(opt_bet, BIG_BLIND)
                    clamped = state.clamp_raise(target_raise)
                    if clamped >= min_r:
                        return ("RAISE", clamped)
                return ("CALL", 0)

            # Profitable Call (Pot Odds satisfied)
            if effective_equity >= pot_odds:
                return ("CALL", 0)

            # Speculative Draw (Flop/Turn only with strong drawing potential or cheap odds)
            if state.street in ("FLOP", "TURN"):
                if cost <= int(0.28 * pot) and (effective_equity >= pot_odds - 0.08 or blockers.nut_flush_blocker):
                    return ("CALL", 0)

            # Negative EV: Fold
            return ("FOLD", 0)

        # --- SCENARIO B: UNOPENED POT (cost == 0, Check is legal) ---
        else:
            # Monster Value (Effective Equity >= 0.78): Geometric sizing to build pot
            if effective_equity >= 0.78 and can_raise:
                opt_bet = get_optimal_bet_size(
                    state.street, state.my_chips, state.opp_chips, pot, effective_equity,
                    is_calling_station=opp_model.is_calling_station
                )
                target = state.my_wager + max(opt_bet, BIG_BLIND)
                clamped = state.clamp_raise(target)
                if clamped >= min_r:
                    return ("RAISE", clamped)
                return ("CHECK", 0)

            # Solid Value (Effective Equity 0.58 - 0.78)
            if effective_equity >= 0.58 and can_raise:
                opt_bet = get_optimal_bet_size(
                    state.street, state.my_chips, state.opp_chips, pot, effective_equity,
                    is_calling_station=opp_model.is_calling_station
                )
                target = state.my_wager + max(opt_bet, BIG_BLIND)
                clamped = state.clamp_raise(target)
                if clamped >= min_r:
                    return ("RAISE", clamped)
                return ("CHECK", 0)

            # Blocker-Assisted Semi-Bluff / C-Bet:
            # When opponent folds to c-bets easily (> 42%) and we have blocker leverage or equity:
            bluff_equity = equity + blockers.bluff_equity_boost
            if (
                opp_model.fold_to_cbet > 0.42
                and bluff_equity >= 0.38
                and can_raise
                and state.street in ("FLOP", "TURN")
            ):
                # 33% pot small c-bet (high risk/reward ratio)
                target_bet = state.my_wager + max(int(0.33 * pot), BIG_BLIND)
                clamped = state.clamp_raise(target_bet)
                if clamped >= min_r:
                    return ("RAISE", clamped)

            # Default: Pot control with Check
            return ("CHECK", 0)
