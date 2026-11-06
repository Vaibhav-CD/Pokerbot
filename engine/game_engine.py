"""
Full simulation engine for IIT Pokerbots 2026 Sneak Peek Hold'em.
Executes rounds with exact second-price auction mechanics,
betting rounds, showdown evaluation, and cumulative bankroll tracking.
Optionally records detailed round histories for interactive visualization.
"""

import random
import time
from core.card import Card
from core.evaluator import evaluate_hand
from core.game_state import RoundState, STARTING_STACK, SMALL_BLIND, BIG_BLIND
from bots.base_bot import BaseBot

class SneakPeekEngine:
    def __init__(self, bot1: BaseBot, bot2: BaseBot, num_rounds: int = 1000, record_history: bool = False):
        self.bot1 = bot1
        self.bot2 = bot2
        self.num_rounds = num_rounds
        self.record_history = record_history
        self.bankroll1 = 0
        self.bankroll2 = 0
        self.time1 = 0.0
        self.time2 = 0.0
        self.round_history = []

    def play_match(self, verbose: bool = False) -> dict:
        self.bankroll1 = 0
        self.bankroll2 = 0
        self.time1 = 0.0
        self.time2 = 0.0
        self.round_history = []

        bankroll_progression = [(0, 0)]

        for r in range(1, self.num_rounds + 1):
            bot1_is_sb = (r % 2 == 1)
            delta1, delta2, round_log = self.play_round(r, bot1_is_sb, verbose=verbose)
            self.bankroll1 += delta1
            self.bankroll2 += delta2
            bankroll_progression.append((self.bankroll1, self.bankroll2))

            if self.record_history and round_log is not None:
                round_log["bankroll1_after"] = self.bankroll1
                round_log["bankroll2_after"] = self.bankroll2
                self.round_history.append(round_log)

        return {
            "rounds": self.num_rounds,
            "bot1_name": self.bot1.name,
            "bot2_name": self.bot2.name,
            "bankroll1": self.bankroll1,
            "bankroll2": self.bankroll2,
            "bankroll_progression": bankroll_progression,
            "time1_seconds": self.time1,
            "time2_seconds": self.time2,
            "history": self.round_history,
            "winner": self.bot1.name if self.bankroll1 > self.bankroll2 else (
                self.bot2.name if self.bankroll2 > self.bankroll1 else "TIE"
            )
        }

    def play_round(self, round_num: int, bot1_is_sb: bool, verbose: bool = False) -> tuple[int, int, dict | None]:
        deck = Card.full_deck()
        random.shuffle(deck)

        sb_bot = self.bot1 if bot1_is_sb else self.bot2
        bb_bot = self.bot2 if bot1_is_sb else self.bot1

        sb_cards = [deck.pop(), deck.pop()]
        bb_cards = [deck.pop(), deck.pop()]

        t0 = time.perf_counter()
        sb_bot.handle_new_round(round_num, is_sb=True, my_cards=sb_cards)
        t_sb = time.perf_counter() - t0

        t0 = time.perf_counter()
        bb_bot.handle_new_round(round_num, is_sb=False, my_cards=bb_cards)
        t_bb = time.perf_counter() - t0

        if bot1_is_sb:
            self.time1 += t_sb
            self.time2 += t_bb
        else:
            self.time1 += t_bb
            self.time2 += t_sb

        sb_chips = STARTING_STACK - SMALL_BLIND
        bb_chips = STARTING_STACK - BIG_BLIND
        pot = SMALL_BLIND + BIG_BLIND

        sb_state = RoundState(
            round_num=round_num, is_sb=True, my_chips=sb_chips, opp_chips=bb_chips,
            pot=pot, street="PREFLOP", my_cards=sb_cards, my_wager=SMALL_BLIND, opp_wager=BIG_BLIND
        )
        bb_state = RoundState(
            round_num=round_num, is_sb=False, my_chips=bb_chips, opp_chips=sb_chips,
            pot=pot, street="PREFLOP", my_cards=bb_cards, my_wager=BIG_BLIND, opp_wager=SMALL_BLIND
        )

        community_cards = []
        action_log = []
        auction_log = {}

        # Log initial blinds
        if self.record_history:
            action_log.append({"street": "BLINDS", "player": sb_bot.name, "action": "POST_SB", "amount": SMALL_BLIND, "pot": SMALL_BLIND})
            action_log.append({"street": "BLINDS", "player": bb_bot.name, "action": "POST_BB", "amount": BIG_BLIND, "pot": pot})

        # --- PREFLOP ---
        folded, winner_is_sb = self._run_betting_round(
            sb_bot, bb_bot, sb_state, bb_state, is_preflop=True, action_log=action_log
        )
        if folded:
            d1, d2 = self._calculate_round_result(winner_is_sb, sb_state, bb_state, bot1_is_sb)
            log = self._build_round_log(round_num, bot1_is_sb, sb_cards, bb_cards, community_cards, action_log, auction_log, d1, d2, "FOLD")
            return d1, d2, log

        # --- FLOP ---
        community_cards = [deck.pop(), deck.pop(), deck.pop()]
        sb_state.street = bb_state.street = "FLOP"
        sb_state.community_cards = list(community_cards)
        bb_state.community_cards = list(community_cards)
        sb_state.my_wager = bb_state.my_wager = 0
        sb_state.opp_wager = bb_state.opp_wager = 0

        # --- AUCTION ---
        auction_log = self._run_auction(sb_bot, bb_bot, sb_state, bb_state, sb_cards, bb_cards, bot1_is_sb)

        # --- FLOP BETTING ---
        folded, winner_is_sb = self._run_betting_round(
            sb_bot, bb_bot, sb_state, bb_state, is_preflop=False, action_log=action_log
        )
        if folded:
            d1, d2 = self._calculate_round_result(winner_is_sb, sb_state, bb_state, bot1_is_sb)
            log = self._build_round_log(round_num, bot1_is_sb, sb_cards, bb_cards, community_cards, action_log, auction_log, d1, d2, "FOLD")
            return d1, d2, log

        # --- TURN ---
        community_cards.append(deck.pop())
        sb_state.street = bb_state.street = "TURN"
        sb_state.community_cards = list(community_cards)
        bb_state.community_cards = list(community_cards)
        sb_state.my_wager = bb_state.my_wager = 0
        sb_state.opp_wager = bb_state.opp_wager = 0

        folded, winner_is_sb = self._run_betting_round(
            sb_bot, bb_bot, sb_state, bb_state, is_preflop=False, action_log=action_log
        )
        if folded:
            d1, d2 = self._calculate_round_result(winner_is_sb, sb_state, bb_state, bot1_is_sb)
            log = self._build_round_log(round_num, bot1_is_sb, sb_cards, bb_cards, community_cards, action_log, auction_log, d1, d2, "FOLD")
            return d1, d2, log

        # --- RIVER ---
        community_cards.append(deck.pop())
        sb_state.street = bb_state.street = "RIVER"
        sb_state.community_cards = list(community_cards)
        bb_state.community_cards = list(community_cards)
        sb_state.my_wager = bb_state.my_wager = 0
        sb_state.opp_wager = bb_state.opp_wager = 0

        folded, winner_is_sb = self._run_betting_round(
            sb_bot, bb_bot, sb_state, bb_state, is_preflop=False, action_log=action_log
        )
        if folded:
            d1, d2 = self._calculate_round_result(winner_is_sb, sb_state, bb_state, bot1_is_sb)
            log = self._build_round_log(round_num, bot1_is_sb, sb_cards, bb_cards, community_cards, action_log, auction_log, d1, d2, "FOLD")
            return d1, d2, log

        # --- SHOWDOWN ---
        sb_eval = evaluate_hand(sb_cards + community_cards)
        bb_eval = evaluate_hand(bb_cards + community_cards)

        if sb_eval > bb_eval:
            winner = "SB"
        elif bb_eval > sb_eval:
            winner = "BB"
        else:
            winner = "TIE"

        total_pot = sb_state.pot
        if winner == "SB":
            delta_sb = total_pot - (STARTING_STACK - sb_state.my_chips)
            delta_bb = -(STARTING_STACK - bb_state.my_chips)
        elif winner == "BB":
            delta_bb = total_pot - (STARTING_STACK - bb_state.my_chips)
            delta_sb = -(STARTING_STACK - sb_state.my_chips)
        else:
            half_pot = total_pot // 2
            delta_sb = half_pot - (STARTING_STACK - sb_state.my_chips)
            delta_bb = half_pot - (STARTING_STACK - bb_state.my_chips)

        sb_bot.handle_round_over(sb_state, delta_sb, opp_cards=bb_cards)
        bb_bot.handle_round_over(bb_state, delta_bb, opp_cards=sb_cards)

        d1 = delta_sb if bot1_is_sb else delta_bb
        d2 = delta_bb if bot1_is_sb else delta_sb
        log = self._build_round_log(round_num, bot1_is_sb, sb_cards, bb_cards, community_cards, action_log, auction_log, d1, d2, f"SHOWDOWN ({winner})")
        return d1, d2, log

    def _run_auction(self, sb_bot, bb_bot, sb_state, bb_state, sb_cards, bb_cards, bot1_is_sb: bool) -> dict:
        t0 = time.perf_counter()
        sb_bid = sb_bot.handle_auction_query(sb_state)
        t_sb = time.perf_counter() - t0

        t0 = time.perf_counter()
        bb_bid = bb_bot.handle_auction_query(bb_state)
        t_bb = time.perf_counter() - t0

        if bot1_is_sb:
            self.time1 += t_sb
            self.time2 += t_bb
        else:
            self.time1 += t_bb
            self.time2 += t_sb

        max_sb_bid = min(sb_state.my_chips, sb_state.opp_chips)
        max_bb_bid = min(bb_state.my_chips, bb_state.opp_chips)
        sb_bid = max(0, min(int(sb_bid), max_sb_bid))
        bb_bid = max(0, min(int(bb_bid), max_bb_bid))

        auction_info = {
            "sb_bid": sb_bid,
            "bb_bid": bb_bid,
            "bot1_bid": sb_bid if bot1_is_sb else bb_bid,
            "bot2_bid": bb_bid if bot1_is_sb else sb_bid,
        }

        if sb_bid > bb_bid:
            payment = bb_bid
            sb_state.my_chips -= payment
            bb_state.opp_chips -= payment
            sb_state.pot += payment
            bb_state.pot += payment
            
            revealed = random.choice(bb_cards)
            sb_state.won_auction = True
            sb_state.opp_revealed_card = revealed
            bb_state.my_revealed_card = revealed

            sb_bot.handle_auction_result(True, sb_bid, bb_bid, revealed, None)
            bb_bot.handle_auction_result(False, bb_bid, sb_bid, None, revealed)
            auction_info.update({"winner": sb_bot.name, "payment": payment, "revealed_card": revealed, "revealed_from": bb_bot.name})

        elif bb_bid > sb_bid:
            payment = sb_bid
            bb_state.my_chips -= payment
            sb_state.opp_chips -= payment
            sb_state.pot += payment
            bb_state.pot += payment

            revealed = random.choice(sb_cards)
            bb_state.won_auction = True
            bb_state.opp_revealed_card = revealed
            sb_state.my_revealed_card = revealed

            sb_bot.handle_auction_result(False, sb_bid, bb_bid, None, revealed)
            bb_bot.handle_auction_result(True, bb_bid, sb_bid, revealed, None)
            auction_info.update({"winner": bb_bot.name, "payment": payment, "revealed_card": revealed, "revealed_from": sb_bot.name})

        else:
            payment_sb = sb_bid
            payment_bb = bb_bid
            sb_state.my_chips -= payment_sb
            bb_state.opp_chips -= payment_sb
            bb_state.my_chips -= payment_bb
            sb_state.opp_chips -= payment_bb
            sb_state.pot += (payment_sb + payment_bb)
            bb_state.pot += (payment_sb + payment_bb)

            revealed_to_sb = random.choice(bb_cards)
            revealed_to_bb = random.choice(sb_cards)
            sb_state.won_auction = bb_state.won_auction = True
            sb_state.opp_revealed_card = revealed_to_sb
            sb_state.my_revealed_card = revealed_to_bb
            bb_state.opp_revealed_card = revealed_to_bb
            bb_state.my_revealed_card = revealed_to_sb

            sb_bot.handle_auction_result(True, sb_bid, bb_bid, revealed_to_sb, revealed_to_bb)
            bb_bot.handle_auction_result(True, bb_bid, sb_bid, revealed_to_bb, revealed_to_sb)
            auction_info.update({
                "winner": "TIE (BOTH)", "payment": payment_sb + payment_bb,
                "revealed_to_sb": revealed_to_sb, "revealed_to_bb": revealed_to_bb
            })

        return auction_info

    def _run_betting_round(
        self, sb_bot, bb_bot, sb_state, bb_state, is_preflop: bool, action_log: list | None = None
    ) -> tuple[bool, bool]:
        turn_sb = is_preflop
        last_action = None
        consecutive_checks = 0

        while True:
            active_bot = sb_bot if turn_sb else bb_bot
            active_state = sb_state if turn_sb else bb_state
            passive_state = bb_state if turn_sb else sb_state

            t0 = time.perf_counter()
            action, amount = active_bot.handle_action_query(active_state)
            t_act = time.perf_counter() - t0

            if active_bot == self.bot1:
                self.time1 += t_act
            else:
                self.time2 += t_act

            cost = active_state.cost_to_call
            min_r, max_r = active_state.legal_raise_bounds()

            if action == "FOLD":
                if action_log is not None:
                    action_log.append({"street": active_state.street, "player": active_bot.name, "action": "FOLD", "amount": 0, "pot": active_state.pot})
                return (True, not turn_sb)

            elif action == "CHECK":
                if cost > 0:
                    if action_log is not None:
                        action_log.append({"street": active_state.street, "player": active_bot.name, "action": "ILLEGAL_CHECK_AUTO_FOLD", "amount": 0, "pot": active_state.pot})
                    return (True, not turn_sb)
                consecutive_checks += 1
                last_action = "CHECK"
                if action_log is not None:
                    action_log.append({"street": active_state.street, "player": active_bot.name, "action": "CHECK", "amount": 0, "pot": active_state.pot})
                if consecutive_checks == 2:
                    break

            elif action == "CALL":
                if cost == 0:
                    consecutive_checks += 1
                else:
                    consecutive_checks = 0
                    
                call_amount = min(cost, active_state.my_chips)
                active_state.my_chips -= call_amount
                passive_state.opp_chips -= call_amount
                active_state.my_wager += call_amount
                passive_state.opp_wager = active_state.my_wager
                active_state.pot += call_amount
                passive_state.pot += call_amount

                if action_log is not None:
                    action_log.append({"street": active_state.street, "player": active_bot.name, "action": "CALL", "amount": call_amount, "pot": active_state.pot})
                
                if is_preflop and turn_sb and active_state.my_wager == BIG_BLIND and passive_state.my_wager == BIG_BLIND and last_action is None:
                    last_action = "CALL"
                    turn_sb = not turn_sb
                    continue

                break

            elif action == "RAISE":
                consecutive_checks = 0
                if max_r < min_r or amount < min_r or amount > max_r:
                    if action_log is not None:
                        action_log.append({"street": active_state.street, "player": active_bot.name, "action": f"ILLEGAL_RAISE({amount})_AUTO_FOLD", "amount": 0, "pot": active_state.pot})
                    return (True, not turn_sb)

                additional = amount - active_state.my_wager
                if additional > active_state.my_chips or additional <= 0:
                    if action_log is not None:
                        action_log.append({"street": active_state.street, "player": active_bot.name, "action": f"EXCEEDED_CHIPS_AUTO_FOLD", "amount": 0, "pot": active_state.pot})
                    return (True, not turn_sb)

                active_state.my_chips -= additional
                passive_state.opp_chips -= additional
                active_state.my_wager = amount
                passive_state.opp_wager = amount
                active_state.pot += additional
                passive_state.pot += additional
                last_action = "RAISE"

                if action_log is not None:
                    action_log.append({"street": active_state.street, "player": active_bot.name, "action": "RAISE", "amount": amount, "pot": active_state.pot})

            else:
                if action_log is not None:
                    action_log.append({"street": active_state.street, "player": active_bot.name, "action": f"UNKNOWN_ACTION({action})_AUTO_FOLD", "amount": 0, "pot": active_state.pot})
                return (True, not turn_sb)

            turn_sb = not turn_sb

        return (False, False)

    def _calculate_round_result(
        self, winner_is_sb: bool, sb_state: RoundState, bb_state: RoundState, bot1_is_sb: bool
    ) -> tuple[int, int]:
        total_pot = sb_state.pot
        if winner_is_sb:
            delta_sb = total_pot - (STARTING_STACK - sb_state.my_chips)
            delta_bb = -(STARTING_STACK - bb_state.my_chips)
        else:
            delta_bb = total_pot - (STARTING_STACK - bb_state.my_chips)
            delta_sb = -(STARTING_STACK - sb_state.my_chips)

        sb_bot = self.bot1 if bot1_is_sb else self.bot2
        bb_bot = self.bot2 if bot1_is_sb else self.bot1
        sb_bot.handle_round_over(sb_state, delta_sb, opp_cards=None)
        bb_bot.handle_round_over(bb_state, delta_bb, opp_cards=None)

        return (delta_sb, delta_bb) if bot1_is_sb else (delta_bb, delta_sb)

    def _build_round_log(
        self, round_num: int, bot1_is_sb: bool, sb_cards: list[int], bb_cards: list[int],
        community_cards: list[int], action_log: list, auction_log: dict, delta1: int, delta2: int, outcome: str
    ) -> dict | None:
        if not self.record_history:
            return None
        return {
            "round_num": round_num,
            "bot1_name": self.bot1.name,
            "bot2_name": self.bot2.name,
            "bot1_is_sb": bot1_is_sb,
            "bot1_cards": [Card.to_str(c) for c in (sb_cards if bot1_is_sb else bb_cards)],
            "bot2_cards": [Card.to_str(c) for c in (bb_cards if bot1_is_sb else sb_cards)],
            "community_cards": [Card.to_str(c) for c in community_cards],
            "auction": auction_log,
            "actions": action_log,
            "delta1": delta1,
            "delta2": delta2,
            "outcome": outcome
        }
