# Changelog

## 1.0.0 - 2026-10-16

- Consolidated the active research line into one public release tree.
- Preserved the mature prompt, rule selection, Goal Contract, action policy, grounding checks, process quality checks, and reporting pipeline.
- Added the Gradio Web console from the late delivery prototype and adapted it to the canonical runner.
- Added OpenAI-compatible Chat Completions and Responses API transports with environment-first credential loading.
- Fixed the Docs unsafe-action guard so initial navigation steps no longer bypass explicit safety checks.
- Removed parent-workspace credential discovery, personal contact names, local absolute paths, runtime outputs, archives, vendored third-party source, and experimental Accessibility/CLI verification code from the public release.
- Added packaging metadata, security policy, contribution guide, release checklist, architecture and evaluation documentation.
- Verified `179/179` project tests.
