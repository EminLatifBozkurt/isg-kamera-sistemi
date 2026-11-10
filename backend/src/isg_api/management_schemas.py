"""Kamera kaynakları, çalışanlar ve bölge kuralları için ortak doğrulama.

Bu modül veritabanına bağlı değildir. Böylece riskli yol/şekil kontrolleri hem API
isteklerinde hem de birim testlerinde aynı kurallarla çalışır.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isg_api.models import CameraSourceType
from isg_api.rules import Equipment

EMPLOYEE_NUMBER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
ZONE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
VIDEO_SUFFIXES = frozenset({".mp4", ".avi", ".mov", ".mkv", ".webm"})
GEOMETRY_EPSILON = 1e-9


class StrictRequest(BaseModel):
    """Yazım hatalı veya beklenmeyen alanları sessizce kabul etmez."""

    model_config = ConfigDict(extra="forbid")


class WebcamSourceConfig(StrictRequest):
    device_index: int = Field(default=0, ge=0, le=31)
    width: int | None = Field(default=None, ge=160, le=7680)
    height: int | None = Field(default=None, ge=120, le=4320)
    fps: float | None = Field(default=None, ge=1, le=120)

    @model_validator(mode="after")
    def dimensions_are_a_pair(self) -> WebcamSourceConfig:
        if (self.width is None) != (self.height is None):
            raise ValueError("Webcam genişliği ve yüksekliği birlikte verilmelidir")
        return self


class RecordedVideoSourceConfig(StrictRequest):
    relative_path: str = Field(min_length=5, max_length=240)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or "\\" in normalized or ":" in normalized or "\x00" in normalized:
            raise ValueError("Video yolu yalnız güvenli ve göreli POSIX yol olmalıdır")
        path = PurePosixPath(normalized)
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise ValueError("Video yolu mutlak olamaz veya üst klasöre çıkamaz")
        if path.suffix.lower() not in VIDEO_SUFFIXES:
            raise ValueError("Desteklenmeyen video uzantısı")
        return str(path)


def validate_camera_source(
    source_type: CameraSourceType, source_config: dict[str, Any]
) -> dict[str, Any]:
    """Kaynak türüne ait yalnız izinli ve parola içermeyen ayarları döndürür."""
    if source_type is CameraSourceType.WEBCAM:
        config = WebcamSourceConfig.model_validate(source_config)
        return config.model_dump(exclude_none=True)
    if source_type is CameraSourceType.RECORDED_VIDEO:
        config = RecordedVideoSourceConfig.model_validate(source_config)
        return config.model_dump()
    # Öğrenci ortamında gerçek RTSP kamera ve güvenli kimlik kasası doğrulanmadı.
    # Bu yüzden URL/parola kabul edip düz metin saklamak yerine özellik kapalıdır.
    raise ValueError("RTSP kaynağı henüz etkin değil; webcam veya kayıtlı video seçin")


class CameraWriteRequest(StrictRequest):
    name: str = Field(min_length=2, max_length=120)
    source_type: CameraSourceType
    source_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Kamera adı en az 2 karakter olmalıdır")
        return normalized

    @model_validator(mode="after")
    def validate_source(self) -> CameraWriteRequest:
        self.source_config = validate_camera_source(self.source_type, self.source_config)
        return self


class EmployeeWriteRequest(StrictRequest):
    employee_number: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=2, max_length=160)
    department: str | None = Field(default=None, max_length=120)

    @field_validator("employee_number")
    @classmethod
    def normalize_employee_number(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not EMPLOYEE_NUMBER_PATTERN.fullmatch(normalized):
            raise ValueError(
                "Çalışan numarası yalnız harf, rakam, nokta, tire ve alt çizgi içerebilir"
            )
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Ad soyad en az 2 karakter olmalıdır")
        return normalized

    @field_validator("department")
    @classmethod
    def normalize_department(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


class ActiveStateRequest(StrictRequest):
    is_active: bool


class NormalizedPoint(StrictRequest):
    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def finite_coordinates(self) -> NormalizedPoint:
        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("Bölge koordinatları sonlu sayı olmalıdır")
        return self


def polygon_area(points: list[NormalizedPoint]) -> float:
    return (
        abs(
            sum(
                point.x * points[(index + 1) % len(points)].y
                - points[(index + 1) % len(points)].x * point.y
                for index, point in enumerate(points)
            )
        )
        / 2
    )


def orientation(a: NormalizedPoint, b: NormalizedPoint, c: NormalizedPoint) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def point_on_segment(a: NormalizedPoint, b: NormalizedPoint, p: NormalizedPoint) -> bool:
    return (
        min(a.x, b.x) - GEOMETRY_EPSILON <= p.x <= max(a.x, b.x) + GEOMETRY_EPSILON
        and min(a.y, b.y) - GEOMETRY_EPSILON <= p.y <= max(a.y, b.y) + GEOMETRY_EPSILON
        and abs(orientation(a, b, p)) <= GEOMETRY_EPSILON
    )


def segments_intersect(
    a: NormalizedPoint,
    b: NormalizedPoint,
    c: NormalizedPoint,
    d: NormalizedPoint,
) -> bool:
    o1, o2 = orientation(a, b, c), orientation(a, b, d)
    o3, o4 = orientation(c, d, a), orientation(c, d, b)
    if (o1 > GEOMETRY_EPSILON) != (o2 > GEOMETRY_EPSILON) and (o3 > GEOMETRY_EPSILON) != (
        o4 > GEOMETRY_EPSILON
    ):
        return True
    return any(
        (abs(value) <= GEOMETRY_EPSILON and point_on_segment(segment_start, segment_end, point))
        for value, segment_start, segment_end, point in (
            (o1, a, b, c),
            (o2, a, b, d),
            (o3, c, d, a),
            (o4, c, d, b),
        )
    )


def validate_simple_polygon(points: list[NormalizedPoint]) -> None:
    coordinates = [(point.x, point.y) for point in points]
    if len(set(coordinates)) != len(coordinates):
        raise ValueError("Bölge çokgeninde aynı nokta tekrar edemez")
    if polygon_area(points) <= GEOMETRY_EPSILON:
        raise ValueError("Bölge çokgeninin sıfırdan büyük bir alanı olmalıdır")

    edge_count = len(points)
    for first in range(edge_count):
        first_next = (first + 1) % edge_count
        for second in range(first + 1, edge_count):
            second_next = (second + 1) % edge_count
            if first == second or first_next == second or second_next == first:
                continue
            if segments_intersect(
                points[first],
                points[first_next],
                points[second],
                points[second_next],
            ):
                raise ValueError("Bölge çokgeni kendi kendini kesemez")


def normalize_equipment(values: list[Equipment]) -> list[Equipment]:
    if len(set(values)) != len(values):
        raise ValueError("Aynı ekipman bir kuralda birden fazla kez seçilemez")
    return sorted(values, key=lambda item: item.value)


class ZoneRuleRequest(StrictRequest):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    polygon: list[NormalizedPoint] = Field(min_length=3, max_length=50)
    required_equipment: list[Equipment] = Field(default_factory=list, max_length=5)

    @field_validator("id")
    @classmethod
    def normalize_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not ZONE_ID_PATTERN.fullmatch(normalized):
            raise ValueError("Bölge kimliği küçük harf, rakam, tire ve alt çizgi içerebilir")
        return normalized

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Bölge adı en az 2 karakter olmalıdır")
        return normalized

    @field_validator("required_equipment")
    @classmethod
    def equipment_is_unique(cls, value: list[Equipment]) -> list[Equipment]:
        return normalize_equipment(value)

    @model_validator(mode="after")
    def polygon_is_simple(self) -> ZoneRuleRequest:
        validate_simple_polygon(self.polygon)
        return self


class RuleDefinitionRequest(StrictRequest):
    required_equipment: list[Equipment] = Field(default_factory=list, max_length=5)
    zones: list[ZoneRuleRequest] = Field(default_factory=list, max_length=32)

    @field_validator("required_equipment")
    @classmethod
    def equipment_is_unique(cls, value: list[Equipment]) -> list[Equipment]:
        return normalize_equipment(value)

    @model_validator(mode="after")
    def zones_are_unique(self) -> RuleDefinitionRequest:
        ids = [zone.id for zone in self.zones]
        if len(set(ids)) != len(ids):
            raise ValueError("Bölge kimlikleri kamera kuralı içinde benzersiz olmalıdır")
        return self


def canonical_rule_definition(rule: RuleDefinitionRequest) -> dict[str, Any]:
    """Sıralama farklarını kaldırarak veritabanı ve özet için kararlı JSON üretir."""
    return {
        "required_equipment": [item.value for item in rule.required_equipment],
        "zones": [
            {
                "id": zone.id,
                "name": zone.name,
                "polygon": [{"x": point.x, "y": point.y} for point in zone.polygon],
                "required_equipment": [item.value for item in zone.required_equipment],
            }
            for zone in sorted(rule.zones, key=lambda item: item.id)
        ],
    }


def rule_definition_hash(definition: dict[str, Any]) -> str:
    encoded = json.dumps(
        definition,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
