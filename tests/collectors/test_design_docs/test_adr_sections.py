from __future__ import annotations

from repo_analyser.collectors.design_docs.adr_sections import has_standard_sections, is_reversibility_tagged

from ._design_docs_helpers import ADR_ACCEPTED, ADR_PROPOSED_NO_SECTIONS


def test_full_context_decision_consequences_shape_detected() -> None:
    assert has_standard_sections(ADR_ACCEPTED) is True


def test_partial_shape_is_not_counted_as_standard() -> None:
    assert has_standard_sections(ADR_PROPOSED_NO_SECTIONS) is False


def test_bold_field_convention_also_counts() -> None:
    text = "**Context**: why.\n**Decision**: what.\n**Consequences**: so what."
    assert has_standard_sections(text) is True


def test_reversibility_tag_detected() -> None:
    assert is_reversibility_tagged(ADR_ACCEPTED) is True
    assert is_reversibility_tagged("one-way door, no going back") is True
    assert is_reversibility_tagged("this change is irreversible") is True


def test_irreversible_does_not_falsely_match_reversible_alone() -> None:
    # A pure "irreversible" mention should still count as tagged (it IS a
    # reversibility tag) -- but must not register as *two* independent hits
    # via a naive substring search finding "reversible" inside it too.
    text = "This decision is irreversible."
    assert is_reversibility_tagged(text) is True


def test_no_reversibility_tag_at_all() -> None:
    assert is_reversibility_tagged(ADR_PROPOSED_NO_SECTIONS) is False
