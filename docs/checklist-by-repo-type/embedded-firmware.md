# Embedded / Firmware Repo

*Part of the [Meta & Content-Purpose Repos](README.md) family: Smaller categories, sorted by what's inside rather than how code is split: a repo that only points at other repos, a published package, infrastructure-as-code, or pure documentation.*

## How to Detect This Repo Type

| Signal | How to Check |
|---|---|
| `platformio.ini`, a Makefile targeting a cross-compiler (e.g. `arm-none-eabi-gcc`), `.ino` files, or vendor HAL/CMSIS directories | `test -f platformio.ini` · `grep -l arm-none-eabi Makefile` |

## Audit Checklist

| Criterion | What It Checks | Tools (keyless-first) |
|---|---|---|
| **MISRA C/C++ compliance** | code conforms to the MISRA coding-standard rules that automotive, medical, and industrial contracts frequently mandate outright. | `Cppcheck (MISRA addon)` |
| **Memory-safety / undefined-behavior static analysis** | buffer overruns, use-after-free, and other undefined behavior are caught at build time, since there's no OS memory protection or runtime safety net to catch them at run time instead. | `Clang Static Analyzer`, `Clang-Tidy` |
| **Worst-case-execution-time & deadline analysis** | the longest possible execution path through a real-time task is measured against its scheduling deadline, since timing itself is a correctness property in a real-time system. | `Percepio Tracealyzer` |
| **Firmware security testing** | bootloader, OTA update signing, and hardcoded keys are tested in stages — extraction, emulation, dynamic testing — following a methodology built specifically for firmware. | `OWASP FSTM` |
| **Hardware-in-the-loop CI** | tests run against an emulation of the real target architecture in CI, not only against the host machine's own architecture where a peripheral or timing bug would never surface. | `Renode (Antmicro, via its GitHub Action)` |
| **Secure-boot / OTA rollback protection** | the boot chain rejects unsigned or downgraded firmware, since a bad field update can permanently brick hardware nobody can physically reach to fix. | `manufacturer secure-boot chain verification` |
