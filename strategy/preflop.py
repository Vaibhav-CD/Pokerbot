"""
Preflop Strategy Engine.
Implements deep-stack (250 BB) heads-up preflop strategy.
Accounts for position: SB is first preflop, but has position (acts 2nd) on all postflop streets.
"""

from core.game_state import RoundState, BIG_BLIND
from core.equity import get_preflop_equity, get_canonical_hand
from .opponent_model import OpponentModel

class PreflopEngine:
    @staticmethod
    def get_action(state: RoundState, opp_model: OpponentModel) -> tuple[str, int]:
        """
        Returns (action_type, amount)
        action_type: 'FOLD', 'CHECK', 'CALL', 'RAISE'
        amount: raise TO amount if RAISE, else 0
        """
        c1, c2 = state.my_cards[0], state.my_cards[1]
        hand_name = get_canonical_hand(c1, c2)
        equity = get_preflop_equity(c1, c2)
        cost = state.cost_to_call
        can_raise = state.can_raise()
        min_r, max_r = state.legal_raise_bounds()

        # Check if opponent is folding to steals frequently
        is_stealer_paradise = opp_model.fold_to_steal > 0.60

        # === 1. SMALL BLIND (Acting 1st preflop, but in-position postflop) ===
        if state.is_sb:
            # First decision: Cost to call is 10 (matching 20 BB)
            if cost == 10:
                # Premium hands: Raise for value
                if equity >= 0.60 or hand_name in ('AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AKo', 'AQs'):
                    if can_raise:
                        target = min(max_r, max(min_r, 3 * BIG_BLIND)) # 60 chips standard raise
                        return ("RAISE", target)
                    return ("CALL", 0)

                # Strong hands or exploitative steal:
                if equity >= 0.50 or is_stealer_paradise:
                    if can_raise and random_or_freq(0.75):
                        target = min(max_r, max(min_r, int(2.5 * BIG_BLIND))) # 50 chips
                        return ("RAISE", target)
                    return ("CALL", 0)

                # Speculative / Drawing hands (playable in-position):
                if equity >= 0.40:
                    return ("CALL", 0)

                # Weak trash
                return ("FOLD", 0)

            # Facing a 3-bet / raise from BB (cost > 10)
            else:
                # Pot odds: cost / (pot + cost)
                pot_odds = cost / (state.pot + cost)
                
                # Premium: 4-bet or call
                if equity >= 0.68 or hand_name in ('AA', 'KK', 'QQ', 'AKs'):
                    if can_raise:
                        target = min(max_r, max(min_r, state.my_wager + cost * 3))
                        return ("RAISE", target)
                    return ("CALL", 0)

                # Solid value / speculative with good implied odds
                if equity >= pot_odds + 0.05 and equity >= 0.48:
                    return ("CALL", 0)

                # Otherwise fold
                return ("FOLD", 0)

        # === 2. BIG BLIND (Posted 20, SB already called or raised) ===
        else:
            # SB just limped (cost == 0, check is legal)
            if state.is_check_legal():
                # Premium / Strong: Raise to punish limper
                if equity >= 0.60 and can_raise:
                    target = min(max_r, max(min_r, int(3.5 * BIG_BLIND))) # 70 chips
                    return ("RAISE", target)
                # Free check with anything else
                return ("CHECK", 0)

            # SB raised (cost > 0)
            else:
                pot_odds = cost / (state.pot + cost)
                
                # 3-bet monsters
                if (equity >= 0.68 or hand_name in ('AA', 'KK', 'QQ', 'AKs')) and can_raise:
                    target = min(max_r, max(min_r, state.my_wager + cost * 3))
                    return ("RAISE", target)

                # Defend calling range
                if equity >= pot_odds:
                    return ("CALL", 0)

                # Fold trash to raise
                return ("FOLD", 0)

def random_or_freq(freq: float) -> bool:
    import random
    return random.random() < freq
