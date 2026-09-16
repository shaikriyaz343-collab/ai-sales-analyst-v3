import pandas as pd

from backend.api.services.evidence import format_source_records, resolve_source_record_column


def test_resolve_source_record_column_prefers_normalized_aliases():
    data = pd.DataFrame({"OpportunityID": ["O1"], "Amount": [100]})
    assert resolve_source_record_column(data, "opportunity_id") == "OpportunityID"


def test_resolve_source_record_column_falls_back_to_generic_id_field():
    data = pd.DataFrame({"custom_id": ["C1", "C2"], "value": [1, 2]})
    assert resolve_source_record_column(data) == "custom_id"


def test_format_source_records_is_deterministic_and_filters_missing_ids():
    values = pd.Series(["O2", None, "O1", "O2", "", "nan"])
    assert format_source_records(values, "OpportunityID") == [
        "OpportunityID=O2",
        "OpportunityID=O1",
    ]
