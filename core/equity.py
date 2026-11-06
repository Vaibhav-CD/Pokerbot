"""
Equity Calculator & Preflop Hand Strength Lookup.
Provides:
1. Canonical hand representation (e.g., 'AKs', '77', 'T9o').
2. Preflop hand equity vs random range table (169 hands).
3. Ultra-fast Monte Carlo & Exact enumeration post-flop equity calculation,
   incorporating Sneak Peek's revealed card information.
"""

import random
from .card import Card, RANK_CHARS
from .evaluator import evaluate_hand

def get_canonical_hand(c1: int, c2: int) -> str:
    r1, s1 = Card.rank(c1), Card.suit(c1)
    r2, s2 = Card.rank(c2), Card.suit(c2)
    if r1 < r2:
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    char1, char2 = RANK_CHARS[r1], RANK_CHARS[r2]
    if r1 == r2:
        return f"{char1}{char2}"
    elif s1 == s2:
        return f"{char1}{char2}s"
    else:
        return f"{char1}{char2}o"

# High-precision precomputed 169-hand preflop equity against a random holding
# Sourced from standard Heads-Up Texas Hold'em equity simulations
PREFLOP_EQUITY = {
    'AA': 0.852, 'KK': 0.824, 'QQ': 0.799, 'JJ': 0.775, 'TT': 0.751,
    '99': 0.721, '88': 0.692, '77': 0.662, '66': 0.633, '55': 0.603,
    '44': 0.570, '33': 0.537, '22': 0.503,
    'AKs': 0.670, 'AQs': 0.661, 'AJs': 0.654, 'ATs': 0.647, 'A9s': 0.630,
    'A8s': 0.621, 'A7s': 0.611, 'A6s': 0.600, 'A5s': 0.599, 'A4s': 0.589,
    'A3s': 0.581, 'A2s': 0.570, 'KQs': 0.634, 'KJs': 0.626, 'KTs': 0.619,
    'K9s': 0.603, 'K8s': 0.588, 'K7s': 0.578, 'K6s': 0.568, 'K5s': 0.557,
    'K4s': 0.547, 'K3s': 0.537, 'K2s': 0.528, 'QJs': 0.603, 'QTs': 0.595,
    'Q9s': 0.580, 'Q8s': 0.564, 'Q7s': 0.548, 'Q6s': 0.538, 'Q5s': 0.528,
    'Q4s': 0.518, 'Q3s': 0.508, 'Q2s': 0.499, 'JTs': 0.575, 'J9s': 0.560,
    'J8s': 0.544, 'J7s': 0.528, 'J6s': 0.512, 'J5s': 0.502, 'J4s': 0.492,
    'J3s': 0.483, 'J2s': 0.473, 'T9s': 0.543, 'T8s': 0.527, 'T7s': 0.512,
    'T6s': 0.495, 'T5s': 0.479, 'T4s': 0.470, 'T3s': 0.460, 'T2s': 0.451,
    '98s': 0.511, '97s': 0.495, '96s': 0.480, '95s': 0.463, '94s': 0.447,
    '93s': 0.438, '92s': 0.429, '87s': 0.480, '86s': 0.465, '85s': 0.449,
    '84s': 0.432, '83s': 0.416, '82s': 0.407, '76s': 0.457, '75s': 0.441,
    '74s': 0.425, '73s': 0.408, '72s': 0.391, '65s': 0.437, '64s': 0.421,
    '63s': 0.405, '62s': 0.388, '54s': 0.419, '53s': 0.403, '52s': 0.386,
    '43s': 0.395, '42s': 0.378, '32s': 0.369,
    'AKo': 0.654, 'AQo': 0.645, 'AJo': 0.636, 'ATo': 0.628, 'A9o': 0.609,
    'A8o': 0.598, 'A7o': 0.587, 'A6o': 0.575, 'A5o': 0.573, 'A4o': 0.563,
    'A3o': 0.554, 'A2o': 0.543, 'KQo': 0.614, 'KJo': 0.606, 'KTo': 0.598,
    'K9o': 0.580, 'K8o': 0.563, 'K7o': 0.552, 'K6o': 0.541, 'K5o': 0.529,
    'K4o': 0.519, 'K3o': 0.508, 'K2o': 0.498, 'QJo': 0.581, 'QTo': 0.573,
    'Q9o': 0.555, 'Q8o': 0.537, 'Q7o': 0.520, 'Q6o': 0.508, 'Q5o': 0.497,
    'Q4o': 0.487, 'Q3o': 0.476, 'Q2o': 0.467, 'JTo': 0.550, 'J9o': 0.533,
    'J8o': 0.515, 'J7o': 0.497, 'J6o': 0.480, 'J5o': 0.468, 'J4o': 0.458,
    'J3o': 0.448, 'J2o': 0.438, 'T9o': 0.517, 'T8o': 0.499, 'T7o': 0.481,
    'T6o': 0.464, 'T5o': 0.446, 'T4o': 0.436, 'T3o': 0.425, 'T2o': 0.416,
    '98o': 0.482, '97o': 0.464, '96o': 0.447, '95o': 0.428, '94o': 0.411,
    '93o': 0.401, '92o': 0.392, '87o': 0.449, '86o': 0.432, '85o': 0.414,
    '84o': 0.396, '83o': 0.378, '82o': 0.369, '76o': 0.424, '75o': 0.406,
    '74o': 0.388, '73o': 0.370, '72o': 0.351, '65o': 0.402, '64o': 0.384,
    '63o': 0.366, '62o': 0.348, '54o': 0.381, '53o': 0.364, '52o': 0.346,
    '43o': 0.354, '42o': 0.336, '32o': 0.325,
}

def get_preflop_equity(c1: int, c2: int) -> float:
    key = get_canonical_hand(c1, c2)
    return PREFLOP_EQUITY.get(key, 0.500)

def calculate_equity(
    my_cards: list[int],
    community_cards: list[int],
    opp_revealed_card: int | None = None,
    num_simulations: int = 70
) -> float:
    """
    Computes equity (win rate + 0.5 * tie rate) given:
    - my_cards: [c1, c2]
    - community_cards: [c3, c4, c5, ...] (3, 4, or 5 cards)
    - opp_revealed_card: int or None (if we won Sneak Peek auction)
    """
    dead_cards = set(my_cards) | set(community_cards)
    if opp_revealed_card is not None:
        dead_cards.add(opp_revealed_card)
        
    remaining_deck = [c for c in range(52) if c not in dead_cards]
    n_comm = len(community_cards)
    cards_needed = 5 - n_comm

    # Case A: River (5 community cards) and Opponent Revealed Card is Known
    # We can do exact enumeration of ALL remaining possible cards for opponent!
    if n_comm == 5 and opp_revealed_card is not None:
        my_eval = evaluate_hand(my_cards + community_cards)
        wins = 0.0
        total = len(remaining_deck)
        for second_card in remaining_deck:
            opp_eval = evaluate_hand([opp_revealed_card, second_card] + community_cards)
            if my_eval > opp_eval:
                wins += 1.0
            elif my_eval == opp_eval:
                wins += 0.5
        return wins / total

    # Case B: Fast Monte Carlo
    wins = 0.0
    for _ in range(num_simulations):
        if opp_revealed_card is not None:
            # Opponent has opp_revealed_card + 1 sampled card
            if cards_needed == 0:
                opp_c2 = random.choice(remaining_deck)
                full_comm = community_cards
            else:
                sampled = random.sample(remaining_deck, 1 + cards_needed)
                opp_c2 = sampled[0]
                full_comm = community_cards + sampled[1:]
            opp_cards = [opp_revealed_card, opp_c2]
        else:
            # Opponent has 2 unknown cards
            if cards_needed == 0:
                opp_cards = random.sample(remaining_deck, 2)
                full_comm = community_cards
            else:
                sampled = random.sample(remaining_deck, 2 + cards_needed)
                opp_cards = sampled[:2]
                full_comm = community_cards + sampled[2:]

        my_eval = evaluate_hand(my_cards + full_comm)
        opp_eval = evaluate_hand(opp_cards + full_comm)
        if my_eval > opp_eval:
            wins += 1.0
        elif my_eval == opp_eval:
            wins += 0.5

    return wins / num_simulations
