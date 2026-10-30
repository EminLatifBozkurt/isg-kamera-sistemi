"""Görüntü modeli yerine açık gözlemlerle kritik iş kurallarını sınar."""

from isg_api.rules import (
    Assessment,
    Equipment,
    Observation,
    assess_equipment,
    resolve_requirements,
)


def test_same_missing_helmet_is_only_a_candidate_where_required():
    observations = {Equipment.HELMET: Observation.MISSING}
    office = resolve_requirements(frozenset())
    production = resolve_requirements(frozenset({Equipment.HELMET}))

    assert assess_equipment(office, observations) == {}
    assert assess_equipment(production, observations) == {
        Equipment.HELMET: Assessment.VIOLATION_CANDIDATE
    }


def test_overlapping_zones_add_requirements_without_removing_camera_base():
    camera = frozenset({Equipment.HELMET, Equipment.VEST})
    zones = [frozenset({Equipment.GOGGLES}), frozenset({Equipment.GLOVES, Equipment.HELMET})]

    requirements = resolve_requirements(camera, iter(zones))

    assert requirements == {Equipment.HELMET, Equipment.VEST, Equipment.GOGGLES, Equipment.GLOVES}
    assert camera == {Equipment.HELMET, Equipment.VEST}


def test_unseen_and_unknown_equipment_are_not_missing_equipment():
    requirements = frozenset({Equipment.GLOVES, Equipment.BOOTS})

    assert assess_equipment(requirements, {Equipment.GLOVES: Observation.UNKNOWN}) == {
        Equipment.BOOTS: Assessment.UNASSESSABLE,
        Equipment.GLOVES: Assessment.UNASSESSABLE,
    }


def test_worn_and_missing_gear_are_assessed_independently_for_one_person():
    requirements = frozenset({Equipment.HELMET, Equipment.VEST})
    observations = {
        Equipment.HELMET: Observation.WORN,
        Equipment.VEST: Observation.MISSING,
        Equipment.GOGGLES: Observation.MISSING,
    }

    assert assess_equipment(requirements, observations) == {
        Equipment.HELMET: Assessment.COMPLIANT,
        Equipment.VEST: Assessment.VIOLATION_CANDIDATE,
    }
