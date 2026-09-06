from __future__ import annotations

from repo_analyser.collectors.license_compliance.spdx_match import match_spdx_id

from ._license_compliance_helpers import (
    APACHE_2_TEXT,
    BSD_2_TEXT,
    BSD_3_TEXT,
    CC0_TEXT,
    GPL_2_TEXT,
    GPL_3_TEXT,
    ISC_TEXT,
    LGPL_3_TEXT,
    MIT_TEXT,
    MPL_2_TEXT,
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
