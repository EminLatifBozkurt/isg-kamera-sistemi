"""ByteTrack çıktısını kişilere ve görünür PPE ekipmanlarına dönüştürür."""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from enum import StrEnum
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from isg_api.video_source import VideoFrame

PERSON_CLASS = "person"
EQUIPMENT_CLASSES = frozenset({"helmet", "gloves", "vest", "boots", "goggles"})
BODY_REGIONS = {
    "helmet": (0.0, 0.35),
    "goggles": (0.0, 0.40),
    "vest": (0.15, 0.75),
    "gloves": (0.20, 0.85),
    "boots": (0.65, 1.05),
}


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        values = (self.x1, self.y1, self.x2, self.y2)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Kutu koordinatları sonlu olmalıdır")
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("Kutu sağ/alt değeri sol/üst değerinden büyük olmalıdır")

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def intersection_ratio(self, other: BoundingBox) -> float:
        """Diğer kutunun ne kadarının bu kutu içinde kaldığını hesaplar."""
        width = max(0.0, min(self.x2, other.x2) - max(self.x1, other.x1))
        height = max(0.0, min(self.y2, other.y2) - max(self.y1, other.y1))
        return (width * height) / (other.width * other.height)


@dataclass(frozen=True, slots=True)
class TrackedDetection:
    class_name: str
    confidence: float
    box: BoundingBox
    track_id: int | None = None


class AssignmentStatus(StrEnum):
    ASSIGNED = "assigned"
    AMBIGUOUS = "ambiguous"
    UNASSIGNED = "unassigned"


@dataclass(frozen=True, slots=True)
class EquipmentAssignment:
    equipment: str
    status: AssignmentStatus
    person_track_id: int | None
    candidate_track_ids: tuple[int, ...]
    score: float | None
    reason: str


@dataclass(frozen=True, slots=True)
class PersonPpeObservation:
    track_id: int
    box: BoundingBox
    detected_equipment: frozenset[str]
    ambiguous_equipment: frozenset[str]


@dataclass(frozen=True, slots=True)
class TrackedFrameResult:
    session_id: str
    frame_index: int
    detections: tuple[TrackedDetection, ...]
    people: tuple[PersonPpeObservation, ...]
    assignments: tuple[EquipmentAssignment, ...]
    inference_ms: float


def _candidate_score(person: BoundingBox, equipment: BoundingBox, kind: str) -> float | None:
    inside = person.intersection_ratio(equipment)
    center_x, center_y = equipment.center
    horizontal_distance = abs(center_x - person.center[0]) / person.width
    vertical_position = (center_y - person.y1) / person.height
    region_start, region_end = BODY_REGIONS[kind]
    region_tolerance = 0.12
    if inside < 0.45:
        return None
    if not region_start - region_tolerance <= vertical_position <= region_end + region_tolerance:
        return None
    region_penalty = 0.0
    if vertical_position < region_start:
        region_penalty = region_start - vertical_position
    elif vertical_position > region_end:
        region_penalty = vertical_position - region_end
    return inside * 0.7 + max(0.0, 1.0 - horizontal_distance) * 0.3 - region_penalty


def assign_equipment_to_people(
    detections: list[TrackedDetection], *, ambiguity_margin: float = 0.12
) -> tuple[tuple[PersonPpeObservation, ...], tuple[EquipmentAssignment, ...]]:
    """Ekipmanı en uygun kişiye atar; yakın iki adayda kesin karar vermez."""
    if not 0 <= ambiguity_margin <= 1:
        raise ValueError("Belirsizlik farkı 0 ile 1 arasında olmalıdır")
    persons = [
        detection
        for detection in detections
        if detection.class_name.lower() == PERSON_CLASS and detection.track_id is not None
    ]
    detected = {int(person.track_id): set() for person in persons}
    ambiguous = {int(person.track_id): set() for person in persons}
    assignments: list[EquipmentAssignment] = []

    for item in detections:
        kind = item.class_name.lower()
        if kind not in EQUIPMENT_CLASSES:
            continue
        candidates = sorted(
            (
                (score, int(person.track_id))
                for person in persons
                if (score := _candidate_score(person.box, item.box, kind)) is not None
            ),
            reverse=True,
        )
        candidate_ids = tuple(track_id for _, track_id in candidates)
        if not candidates:
            assignments.append(
                EquipmentAssignment(
                    kind,
                    AssignmentStatus.UNASSIGNED,
                    None,
                    (),
                    None,
                    "Ekipman hiçbir kişinin beklenen vücut bölgesinde değil",
                )
            )
            continue
        best_score, best_id = candidates[0]
        if len(candidates) > 1 and best_score - candidates[1][0] < ambiguity_margin:
            for _, track_id in candidates:
                ambiguous[track_id].add(kind)
            assignments.append(
                EquipmentAssignment(
                    kind,
                    AssignmentStatus.AMBIGUOUS,
                    None,
                    candidate_ids,
                    round(best_score, 4),
                    "Ekipman birden fazla kişiye benzer yakınlıkta",
                )
            )
            continue
        detected[best_id].add(kind)
        assignments.append(
            EquipmentAssignment(
                kind,
                AssignmentStatus.ASSIGNED,
                best_id,
                candidate_ids,
                round(best_score, 4),
                "Ekipman kişinin beklenen vücut bölgesiyle eşleşti",
            )
        )

    observations = tuple(
        PersonPpeObservation(
            track_id=int(person.track_id),
            box=person.box,
            detected_equipment=frozenset(detected[int(person.track_id)]),
            ambiguous_equipment=frozenset(ambiguous[int(person.track_id)]),
        )
        for person in persons
    )
    return observations, tuple(assignments)


class UltralyticsPpeTracker:
    """Yerel PPE modelini ByteTrack ile tek kamera oturumunda çalıştırır."""

    def __init__(
        self,
        model_path: Path,
        *,
        device: str = "0",
        confidence: float = 0.25,
        image_size: int = 640,
        model: Any | None = None,
    ) -> None:
        if not model_path.is_file() and model is None:
            raise ValueError(f"Yerel PPE modeli bulunamadı; indirme yapılmadı: {model_path}")
        if not 0 < confidence <= 1 or image_size <= 0:
            raise ValueError("Güven eşiği 0-1 arasında, görüntü boyutu pozitif olmalıdır")
        if model is None:
            # Ultralytics eksik takip paketlerini kendiliğinden kurmaya çalışabilir.
            # Kullanıcı onayı olmadan ağ/paket değişikliği yapılmasını kesin kapatıyoruz.
            os.environ.setdefault("YOLO_AUTOINSTALL", "False")
            project_root = Path(__file__).resolve().parents[3]
            config_dir = project_root / "data" / "ultralytics-config"
            config_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("YOLO_CONFIG_DIR", str(config_dir.resolve()))
            if find_spec("lap") is None:
                raise RuntimeError(
                    "ByteTrack için lap paketi eksik; otomatik indirme kapalı. "
                    "Kurulum için önce kullanıcı onayı alınmalıdır."
                )
            from ultralytics import YOLO

            model = YOLO(str(model_path.resolve()))
        self._model = model
        self._device = device
        self._confidence = confidence
        self._image_size = image_size
        self._session_id: str | None = None

    def start_session(self, session_id: str) -> None:
        """Yeni kamera oturumunda ByteTrack belleğini kesin olarak sıfırlar."""
        if not session_id:
            raise ValueError("Oturum kimliği boş olamaz")
        predictor = getattr(self._model, "predictor", None)
        for tracker in getattr(predictor, "trackers", ()) if predictor else ():
            tracker.reset()
        self._session_id = session_id

    def process_frame(self, frame: VideoFrame) -> TrackedFrameResult:
        if frame.session_id != self._session_id:
            raise RuntimeError("Kare etkin takip oturumuna ait değil")
        started = time.perf_counter()
        results = self._model.track(
            source=frame.image,
            persist=True,
            tracker="bytetrack.yaml",
            conf=self._confidence,
            imgsz=self._image_size,
            device=self._device,
            verbose=False,
        )
        result = results[0]
        detections: list[TrackedDetection] = []
        boxes = result.boxes
        if boxes is not None:
            coordinates = boxes.xyxy.cpu().tolist()
            class_ids = boxes.cls.int().cpu().tolist()
            confidences = boxes.conf.cpu().tolist()
            track_ids = (
                boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(boxes)
            )
            for xyxy, class_id, score, track_id in zip(
                coordinates, class_ids, confidences, track_ids, strict=True
            ):
                detections.append(
                    TrackedDetection(
                        class_name=str(result.names[class_id]),
                        confidence=round(float(score), 4),
                        box=BoundingBox(*(float(value) for value in xyxy)),
                        track_id=int(track_id) if track_id is not None else None,
                    )
                )
        people, assignments = assign_equipment_to_people(detections)
        return TrackedFrameResult(
            session_id=frame.session_id,
            frame_index=frame.frame_index,
            detections=tuple(detections),
            people=people,
            assignments=assignments,
            inference_ms=round((time.perf_counter() - started) * 1000, 3),
        )
