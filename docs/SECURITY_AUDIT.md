# Security Cleanup Record

Date: 2026-10-16

## Findings before cleanup

- One historical `.env` contained a live provider key.
- Two local YAML configurations contained two live provider keys.
- One local debug script contained one of those keys.
- Two historical ZIP archives contained the `.env` credential.
- The late delivery README contained an author-machine absolute path.
- The late runtime searched adjacent historical directories for `.env` files.

## Remediation

- Removed the plaintext `.env`, two credential-bearing YAML files, and credential-bearing debug script.
- Permanently deleted the two ZIP files containing `.env` and two redundant construction archives.
- Built the public release in a new directory without inheriting old Git history.
- Restricted environment loading to the project-local `.env` only.
- Added `.gitignore`, `.env.example`, environment-first configuration, a secret scanner, and this release checklist.
- Excluded runtime reports, private screenshots, the 2 GB demo video, vendored third-party source, and experimental branches from the public repository.

## Required external action

Deletion does not invalidate a credential. The owner must rotate every key that appeared in the old `.env`, YAML files, debug script, or ZIP archives before using the public repository. This item remains open until provider-side rotation is confirmed.
