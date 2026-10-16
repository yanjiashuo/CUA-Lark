# Release Checklist

## Security

- [x] No committed `.env` or `configs/config.yaml`
- [x] No API keys or access tokens in the release tree
- [x] Runtime outputs, screenshots, archives and large videos are ignored
- [x] Parent/historical `.env` auto-discovery removed
- [x] Real contact names replaced with synthetic roles
- [ ] Revoke and rotate every key that existed in the private workspace
- [x] Run `python scripts/security_scan.py --git-history` on the sealed local history; run it again immediately before push

## Code and tests

- [x] One canonical source tree
- [x] Project tests pass (`179/179` at v1.0.0 seal)
- [x] Source compiles
- [x] CLI help works
- [x] Web UI uses the canonical runner
- [x] Chat Completions and Responses API adapters share environment-first credential loading
- [x] Experimental Accessibility/CLI verification code excluded from the pure-vision release

## Documentation

- [x] README and quick start
- [x] Architecture and evaluation methodology
- [x] Security policy and contribution guide
- [x] License and changelog
- [x] Honest limitations and metric definitions
- [ ] Replace any placeholder repository URL if the final GitHub owner/name changes

## GitHub

- [ ] Create a new public repository named `CUA-Lark`
- [ ] Confirm the remote is the intended account and empty repository
- [ ] Push the clean `main` branch
- [ ] Verify the remote commit equals local `HEAD`
- [ ] Enable secret scanning and push protection if available
- [ ] Add repository description and topics
- [ ] Create `v1.0.0` tag/release after final review
