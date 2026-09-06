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
