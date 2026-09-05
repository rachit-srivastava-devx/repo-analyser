"""One module per measured dimension. Each collector wraps exactly one
external tool (or git itself), and writes its raw findings as CSV/JSON --
never a silent empty result. See core.util.ToolExecutionError and
docs/adr/0001-fail-loud-not-silent.md.
"""
