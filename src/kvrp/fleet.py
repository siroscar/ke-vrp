"""Heterogeneous fleet definition. All cost numbers are PLACEHOLDERS (KES) - calibrate before
drawing conclusions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleSpec:
    name: str
    mode: str                 # "road" | "air"
    count: int
    capacity: int
    speed_kmh: float          # free-flow speed; road speeds are further scaled by terrain
    fixed_cost: int           # per vehicle used (hire / charter / mobilisation)
    cost_per_km: int          # must be a multiple of 10 (distance unit is 0.1 km)
    shift_h: float            # must be back at depot by this time
    max_km: float | None = None   # range limit (fuel) - mainly for aircraft

    @property
    def cost_per_hm(self) -> int:
        return self.cost_per_km // 10


ROAD = [
    VehicleSpec("truck", "road", 8, 150, 55, 15_000, 80, 16),
    VehicleSpec("van",   "road", 10, 50, 70, 7_000, 50, 16),
]
AIR = [
    VehicleSpec("helicopter", "air", 2, 30, 200, 400_000, 1_200, 11, max_km=600),
]

FLEETS: dict[str, list[VehicleSpec]] = {
    "road_only": ROAD,
    "mixed": ROAD + AIR,
}
