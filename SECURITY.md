# Security Policy

## Supported version

Only the latest `1.x` release is supported with security fixes.

## Reporting a vulnerability

Do not open a public issue containing credentials, private screenshots, account identifiers, or a reproducible exploit against another person's environment. After the GitHub repository is published, use GitHub's private security advisory flow. Until then, contact the maintainer privately.

Include the affected version, impact, minimal reproduction, and suggested mitigation. Remove API keys, access tokens, cookies, document URLs, user names, chat content, and screenshots that are not necessary to reproduce the issue.

## Credential policy

- Put secrets only in environment variables or an untracked `.env` file.
- Keep `api_key` empty in committed YAML.
- Never attach `.env`, `configs/config.yaml`, runtime reports, or raw screenshots to an issue.
- Treat every key that has appeared in a source file, terminal transcript, archive, or Git commit as compromised and rotate it at the provider.

## GUI automation risk

CUA-Lark controls the real mouse and keyboard. Run it with a dedicated test account and test data, close unrelated applications, enable PyAutoGUI failsafe, and review the selected YAML case before execution. The project does not provide a security boundary against an untrusted model response.

## Local Web UI

The Gradio app binds to `127.0.0.1` and uses `share=False` by default. Do not expose it to an untrusted network without adding authentication and an external sandbox.
