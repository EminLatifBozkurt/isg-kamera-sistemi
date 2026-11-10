import pytest
from pydantic import ValidationError

from isg_api.employees import employee_search_pattern
from isg_api.main import create_app
from isg_api.management_schemas import (
    CameraWriteRequest,
    EmployeeWriteRequest,
    RuleDefinitionRequest,
    canonical_rule_definition,
    rule_definition_hash,
)


def test_webcam_source_is_normalized_with_safe_defaults() -> None:
    request = CameraWriteRequest(name="  Ofis   Kamerası ", source_type="webcam")

    assert request.name == "Ofis Kamerası"
    assert request.source_config == {"device_index": 0}


@pytest.mark.parametrize(
    "source_type, source_config",
    [
        ("recorded_video", {"relative_path": "../gizli.mp4"}),
        ("recorded_video", {"relative_path": "C:\\video.mp4"}),
        ("recorded_video", {"relative_path": "demo/video.exe"}),
        ("webcam", {"device_index": -1}),
        ("webcam", {"password": "saklanmamali"}),
        ("rtsp", {"url": "rtsp://kamera.example/live", "password": "gizli"}),
    ],
)
def test_unsafe_or_unsupported_camera_source_is_rejected(
    source_type: str, source_config: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        CameraWriteRequest(
            name="Deneme Kamera",
            source_type=source_type,
            source_config=source_config,
        )


def test_employee_fields_are_normalized() -> None:
    request = EmployeeWriteRequest(
        employee_number="  isc-001 ",
        full_name="  Ahmet   Yılmaz ",
        department="  Üretim   Hattı ",
    )

    assert request.employee_number == "ISC-001"
    assert request.full_name == "Ahmet Yılmaz"
    assert request.department == "Üretim Hattı"


def test_valid_rule_definition_is_canonical_and_hash_is_stable() -> None:
    first = RuleDefinitionRequest.model_validate(
        {
            "required_equipment": ["vest", "helmet"],
            "zones": [
                {
                    "id": "makine",
                    "name": "Makine çevresi",
                    "polygon": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.8, "y": 0.1},
                        {"x": 0.8, "y": 0.8},
                        {"x": 0.1, "y": 0.8},
                    ],
                    "required_equipment": ["gloves", "goggles"],
                }
            ],
        }
    )
    second = RuleDefinitionRequest.model_validate(
        {
            "required_equipment": ["helmet", "vest"],
            "zones": [
                {
                    "id": "makine",
                    "name": "Makine çevresi",
                    "polygon": [
                        {"x": 0.1, "y": 0.1},
                        {"x": 0.8, "y": 0.1},
                        {"x": 0.8, "y": 0.8},
                        {"x": 0.1, "y": 0.8},
                    ],
                    "required_equipment": ["goggles", "gloves"],
                }
            ],
        }
    )

    first_definition = canonical_rule_definition(first)
    second_definition = canonical_rule_definition(second)
    assert first_definition == second_definition
    assert rule_definition_hash(first_definition) == rule_definition_hash(second_definition)


@pytest.mark.parametrize(
    "polygon",
    [
        [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.9},
            {"x": 0.1, "y": 0.9},
            {"x": 0.9, "y": 0.1},
        ],
        [
            {"x": 0.1, "y": 0.1},
            {"x": 0.5, "y": 0.5},
            {"x": 0.9, "y": 0.9},
        ],
        [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.1, "y": 0.1},
        ],
    ],
)
def test_invalid_polygon_is_rejected(polygon: list[dict[str, float]]) -> None:
    with pytest.raises(ValidationError):
        RuleDefinitionRequest.model_validate(
            {
                "zones": [
                    {
                        "id": "riskli-alan",
                        "name": "Riskli alan",
                        "polygon": polygon,
                    }
                ]
            }
        )


def test_duplicate_zone_or_equipment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RuleDefinitionRequest.model_validate({"required_equipment": ["helmet", "helmet"]})

    zone = {
        "id": "uretim",
        "name": "Üretim alanı",
        "polygon": [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.5, "y": 0.9},
        ],
    }
    with pytest.raises(ValidationError):
        RuleDefinitionRequest.model_validate({"zones": [zone, zone]})


def test_management_routes_are_in_openapi_contract() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/v1/cameras" in paths
    assert "/api/v1/cameras/{camera_id}/rules" in paths
    assert "/api/v1/employees" in paths
    assert "/api/v1/employees/{employee_id}/events" in paths
    assert "/api/v1/employees/{employee_id}/history-summary" in paths
    assert "/api/v1/equipment" in paths


def test_employee_search_escapes_like_wildcards() -> None:
    assert employee_search_pattern("  A_100%  ") == "%A\\_100\\%%"
