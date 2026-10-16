# Contributing

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[web,dev]'
pytest -q
```

## Design rules

1. Keep screenshot/VLM perception as the source of GUI decisions. Do not add DOM, Accessibility Tree, or product API state as a hidden replacement for visual reasoning.
2. Keep `instruction`, `expected`, and `verification.assertion` separate. Execution prompts may use the user instruction, screenshot, compact history, action policy, and public scenario/rule protocol; they must not receive hidden pass criteria.
3. Send every operation through the shared `Action` model, coordinate mapping, safety checks, executor, screenshot capture, and reporting path.
4. Put reusable scenario behavior in `cua_lark/scenarios/` or `cua_lark/rules/`, not in case-specific hard-coded branches.
5. Do not commit credentials, personal chat content, private screenshots, run outputs, archives, or large media.

## Tests

All pull requests must pass:

```bash
pytest -q
python -m compileall -q cua_lark scripts
python scripts/security_scan.py
```

Real GUI runs are environment-dependent and should be documented separately with the command, selected cases, model/backend, date, results path, and human review conclusion.
