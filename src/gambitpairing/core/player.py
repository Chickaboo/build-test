# Gambit Pairing
# Copyright (C) 2025  Gambit Pairing developers
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
from typing import Any, Dict, List, Optional, Tuple

from gambitpairing.core.constants import B, W
from gambitpairing.core.utils import generate_id, setup_logger

logger = setup_logger(__name__)


class Player:
    """Represents a player in the tournament."""

    def __init__(
        self,
        name: str,
        rating: Optional[int] = None,
        player_id: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        club: Optional[str] = None,
        federation: Optional[str] = None,
        gender: Optional[str] = None,
        dob: Optional[str] = None,
        fide_id: Optional[int] = None,
        fide_title: Optional[str] = None,
        fide_standard: Optional[int] = None,
        fide_rapid: Optional[int] = None,
        fide_blitz: Optional[int] = None,
        birth_year: Optional[int] = None,
    ) -> None:
        self.id: str = player_id or generate_id("player_")
        self.name: str = name
        self.rating: int = rating if rating is not None else 1000
        self.phone: Optional[str] = phone
        self.email: Optional[str] = email
        self.club: Optional[str] = club
        self.federation: Optional[str] = federation
        self.gender: Optional[str] = gender
        self.dob: Optional[str] = dob
        # FIDE-related metadata (optional)
        self.fide_id: Optional[int] = fide_id
        self.fide_title: Optional[str] = fide_title
        self.fide_standard: Optional[int] = fide_standard
        self.fide_rapid: Optional[int] = fide_rapid
        self.fide_blitz: Optional[int] = fide_blitz
        self.birth_year: Optional[int] = birth_year
        self.score: float = 0.0
        self.is_active: bool = True  # Used for withdrawals

        # History
        self.color_history: List[Optional[str]] = []  # Stores W, B, or None (for bye)
        self.opponent_ids: List[Optional[str]] = []
        self.results: List[Optional[float]] = []
        self.running_scores: List[float] = []
        self.has_received_bye: bool = False
        self.num_black_games: int = 0  # Counts actual games played as Black
        self.float_history: List[int] = []  # Track rounds where player floated down
        self.match_history: List[Optional[Dict[str, Any]]] = (
            []
        )  # Stores {'opponent_id': str, 'opponent_score': float}

        # Tiebreakers (calculated)
        self.tiebreakers: Dict[str, float] = {}

        # Runtime cache
        self._opponents_played_cache: List[Optional["Player"]] = []

    @property
    def age(self) -> Optional[int]:
        """Calculate age from birth year or date of birth."""
        from datetime import date

        # Try to calculate from birth year first
        if self.birth_year:
            current_year = date.today().year
            return current_year - self.birth_year

        # Try to calculate from date of birth
        if self.dob:
            try:
                if isinstance(self.dob, str):
                    # Parse various date formats
                    if "-" in self.dob:  # YYYY-MM-DD format
                        birth_date = date.fromisoformat(self.dob)
                    else:  # Try other formats if needed
                        return None
                else:
                    return None

                today = date.today()
                age = today.year - birth_date.year
                # Adjust if birthday hasn't occurred this year
                if today.month < birth_date.month or (
                    today.month == birth_date.month and today.day < birth_date.day
                ):
                    age -= 1
                return age
            except (ValueError, AttributeError):
                return None

        return None

    @property
    def date_of_birth(self) -> Optional[str]:
        """Return the date of birth, maintaining compatibility."""
        return self.dob

    @date_of_birth.setter
    def date_of_birth(self, value: Optional[str]) -> None:
        """Set the date of birth, maintaining compatibility."""
        self.dob = value

    def __repr__(self) -> str:
        status = "" if self.is_active else " (Inactive)"
        return f"{self.name} ({self.rating}){status}"

    def get_opponent_objects(
        self, players_dict: Dict[str, "Player"]
    ) -> List[Optional["Player"]]:
        """Resolves opponent ID's to Player objects using the provided dictionary."""
        if len(self._opponents_played_cache) != len(self.opponent_ids):
            self._opponents_played_cache = [
                players_dict.get(opp_id) if opp_id else None
                for opp_id in self.opponent_ids
            ]
        return self._opponents_played_cache

    def get_last_two_colors(self) -> Tuple[Optional[str], Optional[str]]:
        """Returns the colors of the last two non-bye games played."""
        valid_colors = [c for c in self.color_history if c is not None]
        if len(valid_colors) >= 2:
            return valid_colors[-1], valid_colors[-2]
        elif len(valid_colors) == 1:
            return valid_colors[-1], None
        else:
            return None, None

    def get_color_preference(self) -> Optional[str]:
        """Determines color preference based on FIDE/USCF rules.
        1. Absolute: If last two played games had same color, must get the other.
        2. Preference: If colors are unbalanced, prefer the color that moves towards balance.
        Returns: "White", "Black", or None if no preference or perfectly balanced.
        """
        valid_played_colors = [c for c in self.color_history if c is not None]

        if len(valid_played_colors) >= 2:
            last_color = valid_played_colors[-1]
            second_last_color = valid_played_colors[-2]
            if last_color == second_last_color:
                return B if last_color == B else W

        white_games_played = valid_played_colors.count(W)
        black_games_played = valid_played_colors.count(B)

        if white_games_played > black_games_played:
            return B
        elif black_games_played > white_games_played:
            return W

        return None

    def add_round_result(
        self, opponent: Optional["Player"], result: float, color: Optional[str]
    ) -> None:
        """Records the outcome of a round for the player."""
        opponent_id = opponent.id if opponent else None
        self.opponent_ids.append(opponent_id)
        self.results.append(result)

        # Record match details for both players before updating scores
        player_score_before_round = self.score
        opponent_score_before_round = opponent.score if opponent else 0.0

        self.match_history.append(
            {
                "opponent_id": opponent_id,
                "player_score": player_score_before_round,
                "opponent_score": opponent_score_before_round,
            }
        )
        if opponent:
            opponent.match_history.append(
                {
                    "opponent_id": self.id,
                    "player_score": opponent_score_before_round,
                    "opponent_score": player_score_before_round,
                }
            )

        self.score += result
        self.running_scores.append(self.score)
        self.color_history.append(color)  # color can be None for a bye
        if color == B:
            self.num_black_games += 1
        if opponent is None:  # This means it was a bye
            self.has_received_bye = True
            logging.debug(f"Player {self.name} marked as having received a bye.")
        self._opponents_played_cache = []  # Invalidate cache

    def to_dict(self) -> Dict[str, Any]:
        """Serializes player data."""
        data = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Player":
        """Deserializes player data."""
        # Handle backward compatibility for sex/gender field consolidation
        gender = data.get("gender") or data.get("sex")

        player = cls(
            name=data["name"],
            rating=data.get("rating", 1000),
            player_id=data["id"],
            phone=data.get("phone"),
            email=data.get("email"),
            club=data.get("club"),
            federation=data.get("federation"),
            gender=gender,
            dob=data.get("dob"),
            fide_id=data.get("fide_id"),
            fide_title=data.get("fide_title"),
            fide_standard=data.get("fide_standard"),
            fide_rapid=data.get("fide_rapid"),
            fide_blitz=data.get("fide_blitz"),
            birth_year=data.get("birth_year"),
        )
        for key, value in data.items():
            if hasattr(player, key) and not key.startswith("_"):
                setattr(player, key, value)
        # Ensure essential lists exist if loading older format without them
        for list_attr in [
            "color_history",
            "opponent_ids",
            "results",
            "running_scores",
            "float_history",
        ]:
            if not hasattr(player, list_attr) or getattr(player, list_attr) is None:
                setattr(player, list_attr, [])
        if not hasattr(player, "has_received_bye"):  # For older save files
            player.has_received_bye = (
                (None in player.opponent_ids) if player.opponent_ids else False
            )
        if not hasattr(player, "num_black_games"):  # For older save files
            player.num_black_games = (
                player.color_history.count(B) if player.color_history else 0
            )

        return player
