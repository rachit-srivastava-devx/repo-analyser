from __future__ import annotations

from repo_analyser.collectors.license_compliance.spdx_match import (
    _signatures_match_in_order,
    match_spdx_id,
)
from repo_analyser.collectors.license_compliance.spdx_sections import (
    split_into_sections,
)

from ._license_compliance_helpers import (
    APACHE_2_TEXT,
    APACHE_MPL_FALSE_POSITIVE_TEXT,
    BSD_2_REVERSED_ORDER_TEXT,
    BSD_2_TEXT,
    BSD_3_LINE_WRAPPED_TEXT,
    BSD_3_TEXT,
    CC0_TEXT,
    GPL_2_TEXT,
    GPL_3_TEXT,
    ISC_TEXT,
    LEADING_APACHE_MENTION_TRAILING_MPL_BLOCK_TEXT,
    LGPL_3_TEXT,
    MIT_TEXT,
    MPL_2_TEXT,
    MULTI_SECTION_APACHE_MENTION_THEN_FILLER_THEN_MPL_BLOCK_TEXT,
    UNLICENSE_TEXT,
)


class TestMatchSpdxId:
    def test_mit(self) -> None:
        assert match_spdx_id(MIT_TEXT) == "MIT"

    def test_apache_2(self) -> None:
        assert match_spdx_id(APACHE_2_TEXT) == "Apache-2.0"

    def test_bsd_2_clause(self) -> None:
        assert match_spdx_id(BSD_2_TEXT) == "BSD-2-Clause"

    def test_bsd_3_clause_is_not_misdetected_as_bsd_2_clause(self) -> None:
        assert match_spdx_id(BSD_3_TEXT) == "BSD-3-Clause"

    def test_bsd_3_clause_survives_hard_wrapped_signature_phrase(self) -> None:
        """Regression test: a real LICENSE that hard-wraps clause 2's
        signature phrase across two lines must still match BSD-3-Clause,
        not fall through to "unknown"."""
        assert match_spdx_id(BSD_3_LINE_WRAPPED_TEXT) == "BSD-3-Clause"

    def test_gpl_2(self) -> None:
        assert match_spdx_id(GPL_2_TEXT) == "GPL-2.0"

    def test_gpl_3(self) -> None:
        assert match_spdx_id(GPL_3_TEXT) == "GPL-3.0"

    def test_lgpl_3_is_not_misdetected_as_gpl_3(self) -> None:
        assert match_spdx_id(LGPL_3_TEXT) == "LGPL-3.0"

    def test_mpl_2(self) -> None:
        assert match_spdx_id(MPL_2_TEXT) == "MPL-2.0"

    def test_isc(self) -> None:
        assert match_spdx_id(ISC_TEXT) == "ISC"

    def test_unlicense(self) -> None:
        assert match_spdx_id(UNLICENSE_TEXT) == "Unlicense"

    def test_cc0(self) -> None:
        assert match_spdx_id(CC0_TEXT) == "CC0-1.0"

    def test_empty_text_is_unknown(self) -> None:
        assert match_spdx_id("") == "unknown"

    def test_unrelated_text_is_unknown(self) -> None:
        assert match_spdx_id("This is a totally custom, unrecognized license.") == "unknown"

    def test_only_one_of_several_required_phrases_present_is_unknown(self) -> None:
        """Apache-2.0 needs both "Apache License" and "Version 2.0" --
        only the first, alone, must not satisfy the signature."""
        assert match_spdx_id("This project uses the Apache License.\n") == "unknown"

    def test_apache_mpl_version_2_0_false_positive_is_resolved(self) -> None:
        """Regression test for the real false-positive class this fix
        closes: Apache-2.0's ("Apache License", "Version 2.0") and
        MPL-2.0's ("Mozilla Public License", "Version 2.0") share the
        literal phrase "Version 2.0". A document containing real MPL-2.0
        text (whose own "Version 2.0" precedes a later, unrelated mention
        of "the Apache License") used to satisfy Apache-2.0's two phrases
        under "present anywhere, any order" and misclassify -- Apache-2.0
        is checked before MPL-2.0 in SPDX_SIGNATURES, so it won the false
        match. Ordered, forward-only matching must resolve this as
        MPL-2.0, the license actually present."""
        assert match_spdx_id(APACHE_MPL_FALSE_POSITIVE_TEXT) == "MPL-2.0"

    def test_phrases_in_wrong_order_do_not_match(self) -> None:
        """BSD-2-Clause's two phrases, present but declared-order-reversed
        (clause 2's phrase before clause 1's), must not match -- a real
        BSD license's numbered clauses never appear out of order."""
        assert match_spdx_id(BSD_2_REVERSED_ORDER_TEXT) == "unknown"

    def test_signatures_match_in_order_helper_rejects_reversed_phrases(self) -> None:
        """Direct unit test of the ordered-scan helper itself: two phrases
        present in text but in the reverse of the order given must fail,
        even though a naive "all(p in text for p in phrases)" would pass."""
        assert _signatures_match_in_order("second first", ("first", "second")) is False
        assert _signatures_match_in_order("first second", ("first", "second")) is True

    def test_signatures_match_in_order_helper_handles_empty_text(self) -> None:
        assert _signatures_match_in_order("", ("anything",)) is False
        assert _signatures_match_in_order("", ()) is True

    def test_leading_apache_mention_trailing_mpl_block_resolves_to_mpl(self) -> None:
        """The counter-example that broke the ordered-scan-only fix
        (ba6e469): a bare "Apache License" mention precedes a rule line,
        which precedes a genuine MPL-2.0 block whose own "Version 2.0" is
        the ONLY "Version 2.0" in the document. Ordered-scan alone still
        wrongly returns Apache-2.0 here since "Apache License"'s position
        precedes "Version 2.0"'s; only a section bound between the rule
        line prevents Apache-2.0 from borrowing MPL's phrase."""
        assert (
            match_spdx_id(LEADING_APACHE_MENTION_TRAILING_MPL_BLOCK_TEXT)
            == "MPL-2.0"
        )

    def test_multi_section_document_with_irrelevant_middle_section_resolves_to_mpl(
        self,
    ) -> None:
        """Self-invented adversarial case beyond the given counter-example:
        three rule-delimited sections (three different rule characters),
        where only the last is a genuine, complete MPL-2.0 block. Proves
        the fix generalizes past exactly one rule line and one other
        section, and that an unrelated filler section doesn't interfere."""
        assert (
            match_spdx_id(MULTI_SECTION_APACHE_MENTION_THEN_FILLER_THEN_MPL_BLOCK_TEXT)
            == "MPL-2.0"
        )

    def test_huge_text_with_no_rule_line_still_matches(self) -> None:
        """A huge single-block LICENSE text (no rule line at all) must
        still match in one pass -- split_into_sections degrades to a
        single section, so this is unchanged from pre-fix behavior."""
        huge_padding = "x" * 500_000
        assert match_spdx_id(huge_padding + "\n" + MIT_TEXT) == "MIT"

    def test_unicode_text_around_signature_is_unknown_when_no_signature_present(
        self,
    ) -> None:
        assert match_spdx_id("© 2024 日本語 — all rights reserved") == "unknown"


class TestSplitIntoSections:
    def test_no_rule_line_returns_single_section(self) -> None:
        assert split_into_sections("just plain text\nwith two lines\n") == [
            "just plain text\nwith two lines\n"
        ]

    def test_empty_text_returns_single_empty_section(self) -> None:
        assert split_into_sections("") == [""]

    def test_splits_on_dash_rule_line(self) -> None:
        assert split_into_sections("first\n---\nsecond") == ["first\n", "second"]

    def test_splits_on_multiple_different_rule_characters(self) -> None:
        assert split_into_sections("a\n===\nb\n***\nc") == ["a\n", "b\n", "c"]

    def test_two_char_run_is_not_a_rule_line(self) -> None:
        """Only 3+ repeats count as a rule line -- "--" alone (e.g. an
        em-dash-style aside) must not split the text."""
        assert split_into_sections("a\n--\nb") == ["a\n--\nb"]
