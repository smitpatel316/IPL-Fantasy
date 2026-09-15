"""Pure lineup validation (D7 slots, D8 overseas cap). No DB, no I/O —
league-core (P2-L2) and the PUT /api/teams/{id}/lineup endpoint both use this.

Input shape: lineup = {"WK": [player_id], "BAT": [player_id, ...], ...}
             roles  = {player_id: {"role": "BAT", "is_overseas": bool}}
"""

from .constants import (
    OVERSEAS_STARTER_CAP,
    ROSTER_SLOTS,
    SLOT_ELIGIBILITY,
    STARTER_SLOTS,
)


class LineupError(ValueError):
    pass


def validate_lineup(lineup: dict[str, list[int]], roles: dict[int, dict]) -> dict:
    """Validate a weekly XI. Returns a summary dict; raises LineupError."""
    if not isinstance(lineup, dict):
        raise LineupError("lineup must be an object of slot -> [player_id]")

    unknown_slots = [s for s in lineup if s not in ROSTER_SLOTS]
    if unknown_slots:
        raise LineupError(f"unknown slots: {unknown_slots}")

    seen: dict[int, str] = {}
    starters: list[int] = []
    for slot, pids in lineup.items():
        if not isinstance(pids, list):
            raise LineupError(f"slot {slot}: must be a list of player ids")
        if len(pids) > ROSTER_SLOTS[slot]:
            raise LineupError(
                f"slot {slot}: {len(pids)} players exceed max {ROSTER_SLOTS[slot]}"
            )
        for pid in pids:
            if pid in seen:
                raise LineupError(f"player {pid} in two slots ({seen[pid]} and {slot})")
            seen[pid] = slot
            info = roles.get(pid)
            if info is None:
                raise LineupError(f"player {pid}: unknown player/role")
            if info["role"] not in SLOT_ELIGIBILITY[slot]:
                raise LineupError(
                    f"player {pid} (role {info['role']}) not eligible for {slot}"
                )
            if slot in STARTER_SLOTS:
                starters.append(pid)

    overseas_starters = sum(1 for pid in starters if roles[pid].get("is_overseas"))
    if overseas_starters > OVERSEAS_STARTER_CAP:
        raise LineupError(
            f"{overseas_starters} overseas starters exceeds cap of {OVERSEAS_STARTER_CAP} (D8)"
        )

    return {
        "ok": True,
        "starters": len(starters),
        "expected_starters": sum(ROSTER_SLOTS[s] for s in STARTER_SLOTS),
        "overseas_starters": overseas_starters,
        "total_rostered": len(seen),
    }
