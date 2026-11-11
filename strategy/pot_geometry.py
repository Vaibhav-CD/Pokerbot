"""
Pot Geometry and Stack-to-Pot Ratio (SPR) Sizing Engine.
Calculates mathematically optimal bet sizes across streets
to maximize Expected Value on monster hands and control pots on medium holdings.
"""

def calculate_spr(my_chips: int, opp_chips: int, pot: int) -> float:
    """Stack-to-Pot Ratio = min(our_chips, opp_chips) / pot."""
    if pot <= 0:
        return 999.0
    eff_stack = min(my_chips, opp_chips)
    return eff_stack / pot

def geometric_bet_fraction(spr: float, streets_remaining: int) -> float:
    """
    Solves for constant geometric bet fraction f such that:
    (1 + 2f)^N = 2 * SPR + 1
    f = ((2 * SPR + 1)^(1/N) - 1) / 2
    """
    if streets_remaining <= 0 or spr <= 0:
        return 0.50

    target = 2.0 * spr + 1.0
    f = (target ** (1.0 / streets_remaining) - 1.0) / 2.0
    # Bound between 25% pot (min reasonable bet) and 150% pot (overbet)
    return max(0.25, min(1.50, f))

def get_optimal_bet_size(
    street: str,
    my_chips: int,
    opp_chips: int,
    pot: int,
    equity: float,
    is_calling_station: bool = False
) -> int:
    """
    Determines optimal bet amount (chips to bet) based on hand strength and SPR:
    - Monster Value (equity >= 0.82): Geometric sizing to commit stacks.
    - Strong Value (equity 0.68 - 0.82): 50% - 75% pot sizing.
    - Medium / Pot Control (equity 0.55 - 0.68): Small 30% - 40% bet.
    - Bluff / Semi-bluff (equity 0.35 - 0.50): 33% - 45% pot to risk less chips.
    """
    spr = calculate_spr(my_chips, opp_chips, pot)
    streets_map = {"FLOP": 3, "TURN": 2, "RIVER": 1}
    streets_left = streets_map.get(street, 1)

    # 1. Monster Hand (Nuts / Sets / Strong Flushes)
    if equity >= 0.82:
        geo_f = geometric_bet_fraction(spr, streets_left)
        # If calling station, we can bet even bigger!
        if is_calling_station:
            geo_f = min(1.80, geo_f * 1.25)
        # Sizing relative to pot
        target = int(pot * geo_f)
        return max(20, target)

    # 2. Strong Hand (Overpair, Top Pair Good Kicker)
    elif equity >= 0.68:
        # 55% - 75% pot depending on street
        base_f = 0.65 if street != "RIVER" else 0.55
        if is_calling_station:
            base_f += 0.15
        return max(20, int(pot * base_f))

    # 3. Medium Value (Top Pair Weak Kicker, Second Pair)
    elif equity >= 0.55:
        # Keep pot manageable (35% - 45% pot)
        base_f = 0.38
        return max(20, int(pot * base_f))

    # 4. Bluff / Semi-bluff
    else:
        # Risk minimal chips for maximal fold equity
        base_f = 0.33
        return max(20, int(pot * base_f))
