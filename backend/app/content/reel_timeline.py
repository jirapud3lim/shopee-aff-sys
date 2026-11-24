"""Validate the renderable subset of a Master Prompt v2 storyboard."""

import math
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field

FPS = 30
REEL_FRAMES = 15 * FPS
SCENE_TEXT_LIMIT = 120
Seconds = Annotated[float, Field(ge=0, le=120, allow_inf_nan=False, strict=True)]
AssetId = Annotated[str, Field(pattern=r"^A(?:[1-9]|1[0-2])$")]


class PlanScene(BaseModel):
    start_s: Seconds
    end_s: Seconds
    source: Literal["REAL_VIDEO", "REAL_PHOTO"]
    asset_id: AssetId
    source_range_s: tuple[Seconds, Seconds] | None = None
    subtitle_th: str | None = Field(default=None, max_length=SCENE_TEXT_LIMIT)
    edit: Literal["hold", "cut"] = "cut"


class ReelPlan(BaseModel):
    duration_s: Literal[15]
    status: Literal["ready_for_preview", "review_required"]
    scenes: list[PlanScene] = Field(min_length=1, max_length=12)


@dataclass(frozen=True)
class TimelineShot:
    asset_index: int
    frames: int
    start_frame: int = 0
    subtitle: str = ""


def compile_timeline(plan: ReelPlan, capacities: list[int | None]) -> list[TimelineShot]:
    shots = []
    cursor = 0.0
    for index, scene in enumerate(plan.scenes, start=1):
        start = round(scene.start_s * FPS)
        end = round(scene.end_s * FPS)
        length = end - start
        if not math.isclose(scene.start_s, cursor, abs_tol=1e-6) or length <= 0 or end > REEL_FRAMES:
            raise ValueError(f"Scene {index}: timecodes must be contiguous from 0 to 15 seconds")
        cursor = scene.end_s
        asset = int(scene.asset_id[1:]) - 1
        if asset >= len(capacities):
            raise ValueError(f"Scene {index}: upload {scene.asset_id} before rendering")
        capacity = capacities[asset]
        source_start = 0
        if capacity is None:
            if scene.source != "REAL_PHOTO" or scene.source_range_s is not None:
                raise ValueError(f"Scene {index}: {scene.asset_id} is a photo and takes no source time range")
        else:
            if scene.source != "REAL_VIDEO" or scene.source_range_s is None:
                raise ValueError(f"Scene {index}: specify the source time range for {scene.asset_id}")
            source_start, source_end = (round(seconds * FPS) for seconds in scene.source_range_s)
            if source_start + length > source_end or source_end > capacity:
                raise ValueError(f"Scene {index}: source range must fit the clip and cover its scene length")
        subtitle = (scene.subtitle_th or "").strip()
        if len(subtitle.splitlines()) > 3:
            raise ValueError(f"Scene {index}: subtitle has more than three lines")
        shots.append(TimelineShot(asset, length, source_start, subtitle))

    if not math.isclose(cursor, 15, abs_tol=1e-6):
        raise ValueError("The plan must end at 15 seconds")
    return shots
