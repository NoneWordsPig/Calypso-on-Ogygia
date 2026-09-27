"""State names and the locations/animations of stationary activities."""

from dataclasses import dataclass
from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    WALKING = "WALKING"
    FISHING = "FISHING"
    WORKING = "WORKING"
    SLEEPING = "SLEEPING"


@dataclass(frozen=True)
class Activity:
    destination: str
    animation: str


# New location-based activities can add a state and a specification here.
ACTIVITIES = {
    State.FISHING: Activity(destination="fishing", animation="fish_cast"),
    State.WORKING: Activity(destination="computer_use", animation="work"),
    State.SLEEPING: Activity(destination="bed", animation="sleep"),
}
