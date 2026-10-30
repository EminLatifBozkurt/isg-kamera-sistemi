"""Modelden bağımsız ekipman kural değerlendirmesi.

Bu kod görüntüye bakmaz ve olay/bildirim oluşturmaz. Gelecekte analiz bileşeninin
ürettiği, ilgili kişiye ait gözlemler bu fonksiyonlara verilecek. Zamansal doğrulama
ve tekrar bildirim engeli ayrıca geliştirilecek.
"""

from collections.abc import Iterable, Mapping
from enum import StrEnum


class Equipment(StrEnum):
    """İlk veri seti incelemesi için aday sınıflar; doğrulanmış model desteği değildir."""

    HELMET = "helmet"
    VEST = "vest"
    GOGGLES = "goggles"
    GLOVES = "gloves"
    BOOTS = "boots"


class Observation(StrEnum):
    WORN = "worn"
    MISSING = "missing"
    UNKNOWN = "unknown"


class Assessment(StrEnum):
    COMPLIANT = "compliant"
    VIOLATION_CANDIDATE = "violation_candidate"
    UNASSESSABLE = "unassessable"


def resolve_requirements(
    camera_requirements: frozenset[Equipment],
    active_zone_requirements: Iterable[frozenset[Equipment]] = (),
) -> frozenset[Equipment]:
    """Kamera temeli ile kişinin içinde olduğu bölgelerin şartlarını birleştirir.

    Bölgeler kamera zorunluluğunu kaldırmaz. Hangi bölgelerin aktif olduğuna bu
    fonksiyon karar vermez; bu bilgi ileride konum hesabından gelecek.
    """
    return camera_requirements.union(*active_zone_requirements)


def assess_equipment(
    requirements: frozenset[Equipment],
    observations: Mapping[Equipment, Observation],
) -> dict[Equipment, Assessment]:
    """Yalnız zorunlu ekipmanları değerlendir; gözlem yoksa eksik varsayma.

    MISSING, analiz tarafından açık eksiklik kanıtı sağlandığında kullanılacak.
    Dedektörün bir ekipmanı bulamaması tek başına MISSING değildir.
    """
    assessments: dict[Equipment, Assessment] = {}
    for equipment in sorted(requirements):
        observation = observations.get(equipment, Observation.UNKNOWN)
        if observation == Observation.WORN:
            assessments[equipment] = Assessment.COMPLIANT
        elif observation == Observation.MISSING:
            assessments[equipment] = Assessment.VIOLATION_CANDIDATE
        else:
            assessments[equipment] = Assessment.UNASSESSABLE
    return assessments
