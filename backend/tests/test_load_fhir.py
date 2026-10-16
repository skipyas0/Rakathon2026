"""R4 repairs applied when loading the organisers' bundles. Run: uv run pytest tests/test_load_fhir.py"""

from mdt_backend.load_fhir import DERIVED_FROM_REPORT, to_r4, to_transaction


def test_invalid_ids_and_references_are_rewritten():
    res = to_r4(
        {
            "resourceType": "DiagnosticReport",
            "id": "P01-lab01",
            "result": [{"reference": "Observation/P01-lab01-hb_f"}],
        }
    )
    assert res["result"] == [{"reference": "Observation/P01-lab01-hb-f"}]
    assert to_r4({"resourceType": "Observation", "id": "P01-lab01-hb_f"})["id"] == "P01-lab01-hb-f"


def test_derived_from_report_moves_to_extension():
    report = {"reference": "DiagnosticReport/P01-pat01"}
    doc = {"reference": "DocumentReference/P01-doc01"}
    res = to_r4({"resourceType": "Observation", "id": "o", "derivedFrom": [report, doc]})
    assert res["derivedFrom"] == [doc]
    assert res["extension"] == [{"url": DERIVED_FROM_REPORT, "valueReference": report}]

    only_report = to_r4({"resourceType": "Observation", "id": "o", "derivedFrom": [report]})
    assert "derivedFrom" not in only_report

    no_report = to_r4({"resourceType": "Observation", "id": "o", "derivedFrom": [doc]})
    assert "extension" not in no_report


def test_empty_answers_are_dropped():
    res = to_r4(
        {
            "resourceType": "QuestionnaireResponse",
            "id": "q",
            "item": [
                {"linkId": "a", "answer": [{"valueString": ""}]},
                {"linkId": "b", "answer": [{"valueInteger": 0}]},
            ],
        }
    )
    assert res["item"] == [{"linkId": "a"}, {"linkId": "b", "answer": [{"valueInteger": 0}]}]


def test_collection_becomes_put_transaction():
    tx = to_transaction(
        {"type": "collection", "entry": [{"resource": {"resourceType": "Patient", "id": "P01"}}]}
    )
    assert tx["type"] == "transaction"
    assert tx["entry"][0]["request"] == {"method": "PUT", "url": "Patient/P01"}
