"""Focused regression tests for Sneak Peek Hold'em bot (stdlib unittest)."""
import random
import unittest

from core.card import Card
from core.evaluator import evaluate_hand
from core.equity import calculate_equity, get_preflop_equity
from core.game_state import RoundState, BIG_BLIND
from strategy.opponent_model import OpponentModel
from strategy.preflop import PreflopEngine
from strategy.auction import AuctionEngine


def C(*names):
    return [Card.from_str(n) for n in names]


class TestEvaluator(unittest.TestCase):
    def test_wheel_straight_flush(self):
        self.assertEqual(evaluate_hand(C('Ah', '2h', '3h', '4h', '5h', 'Ks', 'Qd')), (8, 3))

    def test_straight_beats_trips(self):
        # 5-6-7-8-9 straight beats trip 5s
        self.assertEqual(evaluate_hand(C('5s', '5h', '5d', '6c', '7h', '8s', '9c'))[0], 4)

    def test_two_trips_make_full_house(self):
        self.assertEqual(evaluate_hand(C('As', 'Ah', 'Ad', 'Ks', 'Kh', 'Kd', '2c')), (6, 12, 11))

    def test_quads_kicker(self):
        self.assertEqual(evaluate_hand(C('As', 'Ah', 'Ad', 'Ac', 'Kh', '2d', '3c')), (7, 12, 11))

    def test_flush_top_five(self):
        self.assertEqual(
            evaluate_hand(C('Ah', 'Kh', 'Qh', 'Jh', '9h', '2c', '3d')),
            (5, (12, 11, 10, 9, 7)),
        )

    def test_royal_beats_wheel(self):
        wheel = evaluate_hand(C('Ah', '2h', '3h', '4h', '5h', 'Ks', 'Qd'))
        royal = evaluate_hand(C('Th', 'Jh', 'Qh', 'Kh', 'Ah', '2c', '3d'))
        self.assertGreater(royal, wheel)


class TestGameState(unittest.TestCase):
    def test_max_raise_includes_wagers(self):
        # SB: wager 10, chips 4990; BB: wager 20, chips 4980.
        # True all-in TO amount is min(10+4990, 20+4980) = 5000.
        s = RoundState(my_chips=4990, opp_chips=4980, my_wager=10, opp_wager=20)
        _, max_r = s.legal_raise_bounds()
        self.assertEqual(max_r, 5000)

    def test_max_raise_postflop(self):
        s = RoundState(my_chips=4800, opp_chips=4800, my_wager=100, opp_wager=100)
        _, max_r = s.legal_raise_bounds()
        self.assertEqual(max_r, 4900)

    def test_min_raise_open(self):
        s = RoundState(my_chips=4990, opp_chips=4980, my_wager=0, opp_wager=0)
        min_r, _ = s.legal_raise_bounds()
        self.assertEqual(min_r, BIG_BLIND)


class TestOpponentModel(unittest.TestCase):
    def test_zero_bidder_counts_ones(self):
        m = OpponentModel()
        for b in [0, 1, 0, 1]:
            m.record_auction_bid(b)
        self.assertTrue(m.is_zero_bidder)

    def test_median_bid(self):
        m = OpponentModel()
        for b in [5, 25, 15]:
            m.record_auction_bid(b)
        self.assertEqual(m.median_opp_bid, 15)


class TestEngine(unittest.TestCase):
    def test_sb_limp_bb_check_closes_preflop(self):
        from engine.game_engine import SneakPeekEngine
        from bots.base_bot import BaseBot

        class LimpSB(BaseBot):
            def __init__(self):
                super().__init__('LimpSB')
                self.extra_actions = 0

            def handle_new_round(self, round_num, is_sb, my_cards):
                pass

            def handle_auction_query(self, s):
                return 0

            def handle_action_query(self, s):
                if s.street == 'PREFLOP' and s.cost_to_call == 0:
                    self.extra_actions += 1
                    return ('CHECK', 0)
                return ('CALL', 0)

            def handle_auction_result(self, *a):
                pass

            def handle_round_over(self, *a, **k):
                pass

        class CheckBB(BaseBot):
            def __init__(self):
                super().__init__('CheckBB')

            def handle_new_round(self, round_num, is_sb, my_cards):
                pass

            def handle_auction_query(self, s):
                return 0

            def handle_action_query(self, s):
                return ('CHECK', 0) if s.cost_to_call == 0 else ('CALL', 0)

            def handle_auction_result(self, *a):
                pass

            def handle_round_over(self, *a, **k):
                pass

        random.seed(1)
        sb, bb = LimpSB(), CheckBB()
        e = SneakPeekEngine(sb, bb, num_rounds=1, record_history=True)
        res = e.play_match()
        preflop = [a for a in res['history'][0]['actions'] if a['street'] == 'PREFLOP']
        # Limp + BB check only: no third preflop action.
        self.assertEqual(len(preflop), 2)
        self.assertEqual(sb.extra_actions, 0)

    def test_tie_pot_is_zero_sum(self):
        from engine.game_engine import SneakPeekEngine
        from bots.base_bot import BaseBot

        class CheckCall(BaseBot):
            def __init__(self, n):
                super().__init__(n)

            def handle_new_round(self, round_num, is_sb, my_cards):
                pass

            def handle_auction_query(self, s):
                return 1

            def handle_action_query(self, s):
                return ('CHECK', 0) if s.cost_to_call == 0 else ('CALL', 0)

            def handle_auction_result(self, *a):
                pass

            def handle_round_over(self, *a, **k):
                pass

        for seed in range(20):
            random.seed(seed)
            e = SneakPeekEngine(CheckCall('A'), CheckCall('B'), num_rounds=5)
            res = e.play_match()
            self.assertEqual(res['bankroll1'] + res['bankroll2'], 0)

    def test_auction_second_price(self):
        from engine.game_engine import SneakPeekEngine
        from bots.base_bot import BaseBot

        class FixedBid(BaseBot):
            def __init__(self, n, bid):
                super().__init__(n)
                self.bid = bid

            def handle_new_round(self, round_num, is_sb, my_cards):
                pass

            def handle_auction_query(self, s):
                return self.bid

            def handle_action_query(self, s):
                return ('CHECK', 0) if s.cost_to_call == 0 else ('CALL', 0)

            def handle_auction_result(self, *a):
                pass

            def handle_round_over(self, *a, **k):
                pass

        random.seed(0)
        e = SneakPeekEngine(FixedBid('Hi', 50), FixedBid('Lo', 20), num_rounds=1,
                            record_history=True)
        res = e.play_match()
        auc = res['history'][0]['auction']
        # Winner pays the lower bid.
        self.assertEqual(auc['payment'], 20)


class TestEquity(unittest.TestCase):
    def test_river_exact_deterministic(self):
        my = C('As', 'Ks')
        board = C('Ah', 'Kd', '2c', '5h', '9s')
        e1 = calculate_equity(my, board, opp_revealed_card=Card.from_str('Qh'))
        e2 = calculate_equity(my, board, opp_revealed_card=Card.from_str('Qh'))
        self.assertEqual(e1, e2)
        self.assertGreaterEqual(e1, 0.0)
        self.assertLessEqual(e1, 1.0)

    def test_preflop_aa_strong(self):
        self.assertGreater(get_preflop_equity(*C('As', 'Ah')), 0.80)


class TestPreflop(unittest.TestCase):
    def test_sb_completes_trash_on_pot_odds(self):
        # SB facing 10 to win 30: worst hand still has ~32% equity > 25% pot odds.
        st = RoundState(is_sb=True, my_chips=4990, opp_chips=4980, pot=30,
                        street='PREFLOP', my_cards=C('7d', '2c'),
                        my_wager=10, opp_wager=20)
        action, _ = PreflopEngine.get_action(st, OpponentModel())
        self.assertIn(action, ('CALL', 'RAISE'))

    def test_bb_folds_trash_to_big_raise(self):
        st = RoundState(is_sb=False, my_chips=4800, opp_chips=4800, pot=200,
                        street='PREFLOP', my_cards=C('7d', '2c'),
                        my_wager=20, opp_wager=200)
        action, _ = PreflopEngine.get_action(st, OpponentModel())
        self.assertEqual(action, 'FOLD')


class TestAuction(unittest.TestCase):
    def test_exploits_zero_bidder(self):
        m = OpponentModel()
        for _ in range(5):
            m.record_auction_bid(0)
        st = RoundState(my_chips=4000, opp_chips=4000, pot=100, street='FLOP',
                        my_cards=C('As', 'Ks'), community_cards=C('Ah', '7d', '2c'))
        self.assertEqual(AuctionEngine.calculate_bid(st, m), 1)

    def test_trash_bid_taxes_opponent(self):
        # Bidding 0 lets the opponent win for free; trash should still bid >= 1.
        random.seed(0)
        m = OpponentModel()
        for b in [20, 25, 30]:
            m.record_auction_bid(b)
        st = RoundState(my_chips=4000, opp_chips=4000, pot=100, street='FLOP',
                        my_cards=C('7d', '2c'), community_cards=C('Ah', 'Kd', 'Qh'))
        self.assertGreaterEqual(AuctionEngine.calculate_bid(st, m), 1)


class TestBotLearning(unittest.TestCase):
    def test_bot_observes_opponent_actions(self):
        from bots.sneak_peek_bot import SneakPeekBot
        bot = SneakPeekBot()
        self.assertTrue(hasattr(bot, 'observe_opp_action'))
        bot.observe_opp_action('PREFLOP', 'RAISE', faced_raise=False)
        bot.observe_opp_action('FLOP', 'FOLD', faced_raise=True)
        self.assertGreater(bot.opp_model.opp_pfr_count, 0)
        self.assertGreater(bot.opp_model.opp_faced_postflop_bets, 0)

    def test_per_hand_flags_reset(self):
        from bots.sneak_peek_bot import SneakPeekBot
        from core.card import Card
        bot = SneakPeekBot()
        bot.handle_new_round(1, True, [Card.from_str('As'), Card.from_str('Ks')])
        self.assertFalse(bot.opp_model.pf_raise_this_hand)
        bot.observe_opp_action('PREFLOP', 'RAISE', faced_bet=False)
        self.assertTrue(bot.opp_model.pf_raise_this_hand)
        bot.handle_new_round(2, False, [Card.from_str('As'), Card.from_str('Ks')])
        self.assertFalse(bot.opp_model.pf_raise_this_hand)


def _tight_raising_model():
    m = OpponentModel()
    m.total_hands = 100
    m.opp_vpip_count = 20
    m.opp_pfr_count = 15
    return m


def _loose_passive_model():
    m = OpponentModel()
    m.total_hands = 100
    m.opp_vpip_count = 85
    m.opp_pfr_count = 5
    m.opp_calls = 60
    m.opp_bets_raises = 10
    m.opp_folds_postflop = 10
    return m


class TestRangeEquity(unittest.TestCase):
    def test_tight_range_lowers_medium_hand(self):
        from core.equity import calculate_equity, calculate_range_equity
        my = C('9s', '9c')
        board = C('Ah', 'Kd', '2c')
        random.seed(7)
        uniform = calculate_equity(my, board, None, 600)
        random.seed(7)
        tight = calculate_range_equity(
            my, board, _tight_raising_model(),
            villain_raised_preflop=True, facing_bet=True, num_simulations=600)
        self.assertLess(tight, uniform - 0.03)

    def test_loose_range_close_to_uniform(self):
        from core.equity import calculate_equity, calculate_range_equity
        my = C('9s', '9c')
        board = C('Ah', 'Kd', '2c')
        random.seed(11)
        uniform = calculate_equity(my, board, None, 600)
        random.seed(11)
        loose = calculate_range_equity(
            my, board, _loose_passive_model(),
            villain_raised_preflop=False, facing_bet=False, num_simulations=600)
        self.assertAlmostEqual(loose, uniform, delta=0.08)

    def test_nuts_stay_high_vs_tight(self):
        from core.equity import calculate_range_equity
        random.seed(3)
        eq = calculate_range_equity(
            C('As', 'Ah'), C('Ad', '7d', '2c'), _tight_raising_model(),
            villain_raised_preflop=True, facing_bet=True, num_simulations=300)
        self.assertGreater(eq, 0.90)

    def test_river_weighted_exact_deterministic(self):
        from core.equity import calculate_range_equity
        my = C('As', 'Ks')
        board = C('Ah', 'Kd', '2c', '5h', '9s')
        e1 = calculate_range_equity(my, board, _tight_raising_model(),
                                    opp_revealed_card=Card.from_str('Qh'),
                                    villain_raised_preflop=True)
        e2 = calculate_range_equity(my, board, _tight_raising_model(),
                                    opp_revealed_card=Card.from_str('Qh'),
                                    villain_raised_preflop=True)
        self.assertEqual(e1, e2)
        self.assertGreaterEqual(e1, 0.0)
        self.assertLessEqual(e1, 1.0)

    def test_weight_prefers_strong_hands(self):
        from core.equity import range_cutoff, range_hand_weight
        cutoff = range_cutoff(0.20)
        w_aa = range_hand_weight(*C('As', 'Ah'), cutoff, strength_slope=1.2)
        w_72 = range_hand_weight(*C('7d', '2c'), cutoff, strength_slope=1.2)
        self.assertGreater(w_aa, w_72 * 3)

    def test_range_width_estimates(self):
        self.assertLess(_tight_raising_model().estimated_range_width(True), 0.25)
        self.assertGreater(_loose_passive_model().estimated_range_width(False), 0.60)

    def test_blocker_nut_flush_detection(self):
        from core.blockers import analyze_blockers
        # Board has 3 hearts: Kh, 8h, 2h. We hold Ah (nut flush blocker) and 9s
        my = C('Ah', '9s')
        board = C('Kh', '8h', '2h')
        rep = analyze_blockers(my, board)
        self.assertTrue(rep.nut_flush_blocker)
        self.assertGreater(rep.bluff_equity_boost, 0.05)

    def test_pot_geometry_sizing(self):
        from strategy.pot_geometry import geometric_bet_fraction, get_optimal_bet_size
        # SPR = 10, 3 streets -> geometric fraction should be around 0.85
        f = geometric_bet_fraction(10.0, 3)
        self.assertGreater(f, 0.50)
        self.assertLess(f, 1.20)
        # Sizing with monster equity (0.90) in 200 pot
        amt = get_optimal_bet_size("FLOP", 4000, 4000, 200, 0.90)
        self.assertGreater(amt, 100)


if __name__ == '__main__':
    unittest.main()
