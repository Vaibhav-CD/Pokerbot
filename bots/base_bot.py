from abc import ABC, abstractmethod
from core.game_state import RoundState

class BaseBot(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def handle_new_round(self, round_num: int, is_sb: bool, my_cards: list[int]):
        pass

    @abstractmethod
    def handle_auction_query(self, state: RoundState) -> int:
        """Returns the sealed bid amount (integer >= 0)."""
        pass

    @abstractmethod
    def handle_action_query(self, state: RoundState) -> tuple[str, int]:
        """Returns (action_type, amount), where action_type is 'CHECK','CALL','RAISE','FOLD'."""
        pass

    @abstractmethod
    def handle_auction_result(
        self,
        won_auction: bool,
        my_bid: int,
        opp_bid: int | None,
        opp_revealed_card: int | None,
        my_revealed_card: int | None
    ):
        pass

    @abstractmethod
    def handle_round_over(self, state: RoundState, chip_delta: int, opp_cards: list[int] | None = None):
        pass
