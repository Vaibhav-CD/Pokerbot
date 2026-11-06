"""
Card representation and utilities for Pokerbot.
A card is represented internally as an integer in [0, 51]:
    card = (rank << 2) | suit
    rank in [0..12] corresponding to '2' through 'A'
    suit in [0..3] corresponding to 's', 'h', 'd', 'c'
"""

RANK_CHARS = "23456789TJQKA"
SUIT_CHARS = "shdc"

RANK_TO_INT = {r: i for i, r in enumerate(RANK_CHARS)}
SUIT_TO_INT = {s: i for i, s in enumerate(SUIT_CHARS)}
INT_TO_RANK = {i: r for i, r in enumerate(RANK_CHARS)}
INT_TO_SUIT = {i: s for i, s in enumerate(SUIT_CHARS)}

class Card:
    @staticmethod
    def from_str(card_str: str) -> int:
        """Parses a 2-char string like 'Ah', 'Ts', '2c' into card integer."""
        if len(card_str) != 2:
            raise ValueError(f"Invalid card string: {card_str}")
        rank_char = card_str[0].upper()
        suit_char = card_str[1].lower()
        if rank_char not in RANK_TO_INT or suit_char not in SUIT_TO_INT:
            raise ValueError(f"Invalid card string: {card_str}")
        return (RANK_TO_INT[rank_char] << 2) | SUIT_TO_INT[suit_char]

    @staticmethod
    def to_str(card_int: int) -> str:
        """Formats card integer into 'Ah', 'Ts', etc."""
        r = card_int >> 2
        s = card_int & 3
        return f"{INT_TO_RANK[r]}{INT_TO_SUIT[s]}"

    @staticmethod
    def rank(card_int: int) -> int:
        return card_int >> 2

    @staticmethod
    def suit(card_int: int) -> int:
        return card_int & 3

    @staticmethod
    def full_deck() -> list[int]:
        return list(range(52))
