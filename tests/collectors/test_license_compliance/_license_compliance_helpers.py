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
