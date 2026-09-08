from __future__ import annotations

import subprocess
from pathlib import Path

_ENV = {
    "GIT_AUTHOR_NAME": "Test Author", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test Author", "GIT_COMMITTER_EMAIL": "test@example.com",
}


def _git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path


MIT_TEXT = (
    "MIT License\n\nCopyright (c) 2024 Example Author\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    'of this software and associated documentation files (the "Software"), to deal.\n'
)
APACHE_2_TEXT = "\n                 Apache License\n           Version 2.0, January 2004\n"
BSD_2_TEXT = (
    "Redistribution and use in source and binary forms, with or without\n"
    "modification, are permitted provided that the following conditions are met:\n\n"
    "1. Redistributions of source code must retain the above copyright notice.\n"
    "2. Redistributions in binary form must reproduce the above copyright notice.\n"
)
BSD_3_TEXT = BSD_2_TEXT + (
    "3. Neither the name of the copyright holder nor the names of its contributors\n"
    "   may be used to endorse or promote products derived from this software.\n"
)
# A real hard-wrapped BSD-3-Clause LICENSE (narrower column width than
# BSD_3_TEXT above): clause 2's signature phrase is split by a newline
# right in the middle -- "the above" / "copyright" -- exactly the pattern
# that broke the old literal-substring match.
BSD_3_LINE_WRAPPED_TEXT = (
    "Redistribution and use in source and binary forms, with or without\n"
    "modification, are permitted provided that the following conditions\n"
    "are met:\n\n"
    "1. Redistributions of source code must retain the above copyright\n"
    "   notice, this list of conditions and the following disclaimer.\n\n"
    "2. Redistributions in binary form must reproduce the above\n"
    "   copyright notice, this list of conditions and the following\n"
    "   disclaimer in the documentation and/or other materials provided\n"
    "   with the distribution.\n\n"
    "3. Neither the name of the copyright holder nor the names of its\n"
    "   contributors may be used to endorse or promote products derived\n"
    "   from this software without specific prior written permission.\n"
)
GPL_3_TEXT = "GNU GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007\n"
GPL_2_TEXT = "GNU GENERAL PUBLIC LICENSE\n                       Version 2, June 1991\n"
LGPL_3_TEXT = (
    "GNU LESSER GENERAL PUBLIC LICENSE\n                       Version 3, 29 June 2007\n\n"
    "This version incorporates the terms of version 3 of the GNU General Public License.\n"
)
MPL_2_TEXT = "Mozilla Public License Version 2.0\n==================================\n"
ISC_TEXT = (
    "Permission to use, copy, modify, and/or distribute this software for any\n"
    "purpose with or without fee is hereby granted.\n"
)
UNLICENSE_TEXT = "This is free and unencumbered software released into the public domain.\n"
CC0_TEXT = "Creative Commons Legal Code\n\nCC0 1.0 Universal\n"
# A realistic NOTICE-style document: real MPL-2.0 license text (its own
# "Mozilla Public License" ... "Version 2.0" pair, in order), followed by
# a passing mention of "the Apache License" with no second "Version 2.0"
# of its own. Apache-2.0's signature is ("Apache License", "Version 2.0")
# -- both phrases are literally present *somewhere* in this text (the
# "Version 2.0" belongs to MPL's own clause), and Apache-2.0 is checked
# before MPL-2.0 in SPDX_SIGNATURES, so the old "all(p in text)" check
# misclassified this as Apache-2.0. It's really MPL-2.0: the document's
# own "Version 2.0" precedes "Apache License", so ordered matching finds
# no "Version 2.0" *after* "Apache License" and correctly falls through.
APACHE_MPL_FALSE_POSITIVE_TEXT = (
    "Mozilla Public License Version 2.0\n==================================\n\n"
    "This Source Code Form is subject to the terms of the Mozilla Public\n"
    "License, v. 2.0. If a copy of the MPL was not distributed with this\n"
    "file, You can obtain one at http://mozilla.org/MPL/2.0/.\n\n"
    "Portions of this repository were vendored in from a dependency\n"
    "distributed under the terms of the Apache License; see NOTICE.\n"
)
# BSD-2-Clause's two signature phrases, present but in the REVERSE of
# their declared order (clause 2's phrase, then clause 1's) -- must NOT
# match BSD-2-Clause (nor BSD-3-Clause): a real BSD license's clauses are
# numbered and always appear source-code-clause-first.
BSD_2_REVERSED_ORDER_TEXT = (
    "Redistributions in binary form must reproduce the above copyright notice.\n"
    "Redistributions of source code must retain the above copyright notice.\n"
)
# The counter-example that broke the ordered-scan-only fix (commit
# ba6e469): a bare, unrelated "Apache License" mention comes FIRST,
# followed by a rule line, followed by a genuine MPL-2.0 block whose OWN
# "Version 2.0" is what ordered-scan (with no section bound) would wrongly
# borrow to complete Apache-2.0's ("Apache License", "Version 2.0")
# signature -- ordered-scan alone is satisfied because "Apache License"'s
# position is still before "Version 2.0"'s. Splitting on the "---" rule
# line puts the bare mention and the MPL block in different sections, so
# Apache-2.0 never sees both of its phrases in one section and MPL-2.0
# (checked after Apache-2.0) correctly wins instead.
LEADING_APACHE_MENTION_TRAILING_MPL_BLOCK_TEXT = (
    "THIRD-PARTY NOTICES\n\n"
    "This distribution includes code originally licensed under the Apache "
    "License;\nsee vendor/foo/NOTICE for attribution details.\n\n"
    "---\n\n"
    "Mozilla Public License Version 2.0\n"
    "==================================\n\n"
    "This Source Code Form is subject to the terms of the Mozilla Public\n"
    "License, v. 2.0.\n"
)
# A second, self-invented adversarial shape: THREE rule-delimited sections
# (using three different rule characters, "=", "-", "*", to prove the
# splitter isn't tuned to one specific character), where the first section
# bare-mentions Apache with no "Version 2.0" of its own, the middle section
# is unrelated filler with no license phrases at all, and only the third
# section is a genuine, complete MPL-2.0 block. Correct answer is still
# MPL-2.0: Apache-2.0's signature never completes in any single section,
# and the middle section contributes nothing to either signature.
MULTI_SECTION_APACHE_MENTION_THEN_FILLER_THEN_MPL_BLOCK_TEXT = (
    "THIRD-PARTY NOTICES\n"
    "====================\n\n"
    "This module vendors code originally released under the Apache "
    "License,\nper upstream's NOTICE file; no further Apache text is "
    "reproduced here.\n\n"
    "--------------------\n\n"
    "This section intentionally left blank for future dependency "
    "additions.\n\n"
    "********************\n\n"
    "Mozilla Public License Version 2.0\n"
    "==================================\n\n"
    "This Source Code Form is subject to the terms of the Mozilla\n"
    "Public License, v. 2.0.\n"
)
# The exact same false-positive shape as LEADING_APACHE_MENTION_TRAILING_
# MPL_BLOCK_TEXT above, but with the "---" rule line replaced by a single
# blank line -- this is what broke attempt 2 (f0d603c): rule-line section
# splitting doesn't fire when there's no rule line, even though the
# document's structure (an unrelated bare mention, then a real MPL block)
# is identical. Tightest-window matching doesn't depend on any separator
# at all, so this must resolve the same way: MPL-2.0.
BLANK_LINE_SEPARATED_APACHE_MENTION_THEN_MPL_BLOCK_TEXT = (
    "THIRD-PARTY NOTICES\n\n"
    "This distribution includes code originally licensed under the Apache "
    "License;\nsee vendor/foo/NOTICE for attribution details.\n\n"
    "\n"
    "Mozilla Public License Version 2.0\n"
    "==================================\n\n"
    "This Source Code Form is subject to the terms of the Mozilla Public\n"
    "License, v. 2.0.\n"
)
# Same false-positive shape again, separated by a Markdown-style heading
# instead of a rule line or a blank line -- the other structural shape
# attempt 2's verifier confirmed broke f0d603c.
HEADING_SEPARATED_APACHE_MENTION_THEN_MPL_BLOCK_TEXT = (
    "## Bundled Dependency: foo-lib\n\n"
    "This distribution includes code originally licensed under the Apache "
    "License;\nsee vendor/foo/NOTICE for attribution details.\n\n"
    "## Bundled Dependency: bar-lib\n\n"
    "Mozilla Public License Version 2.0\n"
    "==================================\n\n"
    "This Source Code Form is subject to the terms of the Mozilla Public\n"
    "License, v. 2.0.\n"
)
# Self-invented adversarial case: no separator of ANY kind, not even a
# blank line -- the bare Apache mention and the MPL block are on directly
# adjacent lines. Proves the fix doesn't depend on finding *some*
# boundary at all; it only cares how tightly each signature's own phrases
# cluster.
NO_SEPARATOR_LINE_ADJACENT_APACHE_MENTION_THEN_MPL_BLOCK_TEXT = (
    "This distribution includes code originally licensed under the Apache License;\n"
    "see vendor/foo/NOTICE for attribution details.\n"
    "Mozilla Public License Version 2.0\n"
    "This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.\n"
)
# Self-invented three-way contamination: bare mentions of Apache-2.0 AND
# GPL-2.0 (neither with its own second phrase) surround a genuine,
# complete MPL-2.0 block. Proves the fix generalizes past exactly two
# competing licenses.
THREE_WAY_CONTAMINATION_TEXT = (
    "This bundle vendors code under the Apache License from one dependency.\n"
    "Another dependency, foo-cli, is licensed under GNU GENERAL PUBLIC LICENSE "
    "terms (see its own file).\n"
    "Mozilla Public License Version 2.0\n"
    "==================================\n\n"
    "This Source Code Form is subject to the terms of the Mozilla Public "
    "License, v. 2.0.\n"
)
# Self-invented "break your own fix" attempt, and the one that succeeds:
# a bare, casual mention of the license's own full name -- "Apache License
# Version 2.0" -- written naturally in one breath is structurally
# IDENTICAL (two phrases immediately adjacent) to a genuine Apache-2.0
# header ("Apache License\nVersion 2.0, January 2004" collapses to the
# same shape). There is no textual feature left to tell a bare mention
# of the license's own name apart from the license's own title once both
# are this tight, so this document -- genuinely MIT-licensed, with an
# incidental one-line mention of Apache-2.0 elsewhere -- is misclassified
# as Apache-2.0. Tracked in test_spdx_match.py as a documented, expected
# (xfail) limitation, not a hidden one.
BARE_LICENSE_NAME_MENTION_ADJACENT_TO_MIT_TEXT = (
    "See the Apache License Version 2.0 notice below for the vendored file.\n\n"
) + MIT_TEXT
