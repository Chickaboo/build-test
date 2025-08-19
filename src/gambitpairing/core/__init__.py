"""Types used in Gambit Pairing"""

from typing import List, Optional, Tuple

from gambitpairing.core.player import Player

MatchPairing = Tuple[int, int]  # Tuple of player indices
RoundSchedule = Tuple[MatchPairing, ...]  # All pairings for one round
Pairings = Tuple[List[Tuple[Player, Player]], Optional[Player]]
MaybePlayer = Optional[Player]
Players = List[Player]

#  LocalWords:  MatchPairing RoundSchedule
