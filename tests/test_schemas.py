from src.schemas.models import (
    ExtractionBundle,
    Source,
    Tender,
    Yacht,
    YachtAlias,
    YachtEvent,
)


def test_models_instantiation():
    yacht = Yacht(id=1, name="Test Yacht", build_year=2015)
    tender = Tender(id=1, yacht_id=1, name="Tender")
    alias = YachtAlias(yacht_id=1, alias="TY")
    event = YachtEvent(yacht_id=1, event="launched", date="2024-01-01")
    source = Source(url="http://example.com", domain="example.com")
    bundle = ExtractionBundle(
        yachts=[yacht],
        tenders=[tender],
        aliases=[alias],
        events=[event],
        sources=[source],
    )
    assert bundle.yachts[0].name == "Test Yacht"
