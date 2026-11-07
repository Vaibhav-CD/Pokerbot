"""
Sub-microsecond 5, 6, and 7-card Hand Evaluator.
Returns an integer score or comparable tuple (hand_type, ...).
Hand types:
    8: Straight Flush
    7: Four of a Kind
    6: Full House
    5: Flush
    4: Straight
    3: Three of a Kind
    2: Two Pair
    1: One Pair
    0: High Card
"""

def evaluate_hand(cards: list[int]) -> tuple:
    """
    Evaluates 5, 6, or 7 cards and returns a comparable tuple.
    Higher tuple strictly beats a lower tuple.
    cards: list of ints in [0..51]
    """
    suits = [0, 0, 0, 0]
    ranks = [0] * 13
    rank_mask = 0
    suit_masks = [0, 0, 0, 0]

    for c in cards:
        r = c >> 2
        s = c & 3
        suits[s] += 1
        ranks[r] += 1
        rank_mask |= (1 << r)
        suit_masks[s] |= (1 << r)

    # 1. Flush suit detection (straight flush checked first, plain flush later)
    flush_suit = -1
    for s in range(4):
        if suits[s] >= 5:
            flush_suit = s
            break

    if flush_suit != -1:
        f_mask = suit_masks[flush_suit]
        m = f_mask << 1
        if f_mask & 0x1000:  # Ace
            m |= 1
        consec = m & (m >> 1) & (m >> 2) & (m >> 3) & (m >> 4)
        if consec:
            top_rank = (consec.bit_length() - 1) + 3
            return (8, top_rank)

    # 2. Check Straight
    m = rank_mask << 1
    if rank_mask & 0x1000:
        m |= 1
    consec = m & (m >> 1) & (m >> 2) & (m >> 3) & (m >> 4)
    has_straight = False
    straight_top = -1
    if consec:
        has_straight = True
        straight_top = (consec.bit_length() - 1) + 3

    # Multiplicity grouping
    quads = -1
    trips = []
    pairs = []
    for r in range(12, -1, -1):
        cnt = ranks[r]
        if cnt == 4:
            quads = r
        elif cnt == 3:
            trips.append(r)
        elif cnt == 2:
            pairs.append(r)

    # 3. Four of a kind
    if quads != -1:
        kicker = -1
        for r in range(12, -1, -1):
            if r != quads and ranks[r] > 0:
                kicker = r
                break
        return (7, quads, kicker)

    # 4. Full House
    if trips:
        if len(trips) >= 2:
            return (6, trips[0], trips[1])
        if pairs:
            return (6, trips[0], pairs[0])

    # 5. Flush (beats straight, loses to full house)
    if flush_suit != -1:
        f_mask = suit_masks[flush_suit]
        flush_ranks = []
        for r in range(12, -1, -1):
            if f_mask & (1 << r):
                flush_ranks.append(r)
                if len(flush_ranks) == 5:
                    break
        return (5, tuple(flush_ranks))

    # 6. Straight
    if has_straight:
        return (4, straight_top)

    # 6. Three of a kind
    if trips:
        kickers = []
        for r in range(12, -1, -1):
            if r != trips[0] and ranks[r] > 0:
                kickers.append(r)
                if len(kickers) == 2:
                    break
        return (3, trips[0], tuple(kickers))

    # 7. Two Pair
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        kicker = -1
        for r in range(12, -1, -1):
            if r != p1 and r != p2 and ranks[r] > 0:
                kicker = r
                break
        return (2, p1, p2, kicker)

    # 8. One Pair
    if len(pairs) == 1:
        p = pairs[0]
        kickers = []
        for r in range(12, -1, -1):
            if r != p and ranks[r] > 0:
                kickers.append(r)
                if len(kickers) == 3:
                    break
        return (1, p, tuple(kickers))

    # 9. High Card
    top_5 = []
    for r in range(12, -1, -1):
        if ranks[r] > 0:
            top_5.append(r)
            if len(top_5) == 5:
                break
    return (0, tuple(top_5))
