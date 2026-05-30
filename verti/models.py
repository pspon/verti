"""SQLModel ORM models for the Verti Garden Planner.

These replace the previous flat-file (CSV/JSON) storage. The schema is split
into three concerns:

* **Plan data** (per growing season): :class:`Seed`, :class:`GardenBed` /
  :class:`BedPlant`, :class:`PlantingProgress`, :class:`Harvest`.
* **Rules**: :class:`PlantingRule` — frost-relative scheduling deltas.
* **Reference data**: :class:`Companion`, :class:`SpacingGuide`,
  :class:`PlantColor`, :class:`IconMap`.
"""

import datetime
from typing import List, Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


# ─── Plan data ──────────────────────────────────────────────────────────────
class Seed(SQLModel, table=True):
    """A seed/variant entry within a single growing-season plan."""

    id: Optional[int] = Field(default=None, primary_key=True)
    season_year: int = Field(index=True)  # the plan year, e.g. 2025 / 2026

    seed: str = ""
    variant: str = ""
    brand: str = ""
    packet_year: Optional[int] = None  # CSV "Year" — packet purchase year
    days_to_maturity: Optional[int] = None
    days_after_transplant: Optional[int] = None
    season: str = ""
    per_square: Optional[float] = None
    sun: str = ""
    frost: str = ""
    planting_method: str = ""
    plant_this_year: Optional[bool] = None  # CSV "Plant in <year>"
    transplant_delta: Optional[int] = None
    last_frost_delta: Optional[int] = None
    start_indoors: Optional[datetime.date] = None  # CSV "Start Indoors"
    transplant_sow: Optional[datetime.date] = None  # CSV "Transplant / Sow"

    @property
    def display_name(self) -> str:
        return f"{self.seed} {self.variant}".strip()


class GardenBed(SQLModel, table=True):
    """A physical garden bed and its assigned plant families."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    width: float = 0.0
    length: float = 0.0
    bed_type: str = ""  # JSON "type"
    sun: str = ""

    plants: List["BedPlant"] = Relationship(
        back_populates="bed",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "BedPlant.position"},
    )


class BedPlant(SQLModel, table=True):
    """A plant family assigned to a :class:`GardenBed` (ordered)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    bed_id: int = Field(foreign_key="gardenbed.id", index=True)
    plant_name: str = ""
    position: int = 0

    bed: Optional[GardenBed] = Relationship(back_populates="plants")


class PlantingProgress(SQLModel, table=True):
    """Per-season tracking of sowing / transplanting status for a plant."""

    __table_args__ = (
        UniqueConstraint("season_year", "display_name", name="uq_progress_year_plant"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    season_year: int = Field(index=True)
    display_name: str = Field(index=True)
    start_status: str = "not_started"  # not_started | in_progress | done | skipped
    transplant_status: str = "not_started"
    start_actual: Optional[datetime.date] = None
    transplant_actual: Optional[datetime.date] = None
    notes: str = ""
    bed: str = ""


class Harvest(SQLModel, table=True):
    """A logged harvest event."""

    id: Optional[int] = Field(default=None, primary_key=True)
    date: Optional[datetime.date] = None
    plant: str = ""
    variant: str = ""
    quantity_kg: Optional[float] = None
    notes: str = ""


# ─── Rules ────────────────────────────────────────────────────────────────────
class PlantingRule(SQLModel, table=True):
    """Frost-relative scheduling rule for a plant (keyed by display name)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str = Field(unique=True, index=True)
    seed: str = ""
    variant: str = ""
    brand: str = ""
    days_to_maturity: Optional[int] = None
    days_after_transplant: Optional[int] = None
    season: str = ""
    per_square: Optional[float] = None
    sun: str = ""
    frost_tolerance: str = ""
    planting_method: str = ""
    start_indoors_delta: Optional[int] = None
    transplant_delta: Optional[int] = None
    last_frost_delta: Optional[int] = None


# ─── Reference data ─────────────────────────────────────────────────────────
class Companion(SQLModel, table=True):
    """Companion-planting relationships for a plant."""

    id: Optional[int] = Field(default=None, primary_key=True)
    plant: str = Field(unique=True, index=True)
    good: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    bad: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: str = ""


class SpacingGuide(SQLModel, table=True):
    """Square-foot spacing guidance for a plant."""

    id: Optional[int] = Field(default=None, primary_key=True)
    plant: str = Field(unique=True, index=True)
    spacing_in: Optional[float] = None
    row_spacing_in: Optional[float] = None
    depth_in: Optional[float] = None


class PlantColor(SQLModel, table=True):
    """Display colour (hex) for a plant in charts/layouts."""

    id: Optional[int] = Field(default=None, primary_key=True)
    plant: str = Field(unique=True, index=True)
    color: str = ""


class IconMap(SQLModel, table=True):
    """Emoji icon lookups (sun / frost categories)."""

    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)  # 'sun' | 'frost'
    key: str = ""
    icon: str = ""
