# Evaluation Report

## 1. Why the metrics are separated

CUA-Lark evolved through repeated real-GUI experiments. A case may pass in one environment and later fail after UI changes, state contamination, model variance, or a stricter human review. For that reason, this report does not compress every run into one headline pass rate.

Four terms are used:

1. **Unit test pass**: deterministic, offline Python tests pass in the release tree.
2. **Single-run pass**: the automated verifier marked one concrete run as passed.
3. **Ever passed**: at least one retained real-GUI record for a unique case is `passed`.
4. **Clean pass**: automated status and human screenshot/trajectory review both accept the result without visible residue or shortcut artifacts.

## 2. Release verification

| Check | Result |
| --- | ---: |
| Project-owned Python tests | 179/179 passed |
| Python compilation | passed |
| CLI help smoke test | passed |
| Release-tree secret scan | 0 real credential findings at seal time |
| Committed archives/videos/runtime outputs | 0 |

These checks validate software consistency; they do not operate the real Feishu client.

## 3. Historical real-GUI evidence

| Stage | Result | Interpretation |
| --- | ---: | --- |
| M1 basic actions | 7/7 | Early action primitives passed the historical acceptance run |
| Historical IM basic | 5/5 | Five basic IM end-to-end cases passed |
| Historical IM advanced | 5/5 | Five advanced IM end-to-end cases passed |
| New-framework retained cases | 75 of 77 unique non-setup cases ever passed | Cross-round coverage, not one clean simultaneous regression |
| Docs demonstration chain | 7/7 | Final curated Docs demo cases passed in their retained run |

The 75 ever-passed cases consist of 62 Docs, 9 IM, and 4 Calendar unique case IDs in retained records. Two unique cases did not have a retained pass: one IM case remained `running`, and one Mail demo case failed.

## 4. Iteration evidence

- A screenshot-only probe reduced one historical operation from about 127.32 seconds to 21.78 seconds, showing the value of removing unnecessary planning overhead for simple tasks.
- A later IM @-mention optimization reduced the observed trajectory from 12 steps to 8, and then to 6 steps / 115.87 seconds after bbox–point consistency gating. These are case-specific ablation results, not general latency guarantees.
- Docs expanded from initial coverage gaps to 56 claimed functional operations, followed by stricter screenshot review that reopened false positives. The final methodology distinguishes automatic status, human visual review, targeted rerun, and clean pass.

Related experiment notes are retained under `ablation/`.

## 5. Known limitations

- Real-GUI outcomes depend on Feishu version, account state, screen layout, display scaling, permissions, network and model behavior.
- Calendar has fewer retained cases than IM and Docs; Mail does not have a retained passing demo case.
- The repository does not ship private screenshots or raw run outputs, so historical figures are summarized rather than fully reproducible from public data alone.
- VLM rule selection adds a model call and can increase latency; static rules are available when repeatability matters more.
- Full-screen fallback increases the risk of grounding unrelated applications and is disabled for strict Docs flows unless explicitly allowed.

## 6. Recommended future benchmark

For a publishable benchmark, freeze the Feishu version, account fixture, screen resolution, model and sampling parameters; run each case at least three times; report pass@1, clean-pass rate, median steps, median latency, recovery rate, grounding correction rate, and human-review disagreement. Publish only sanitized screenshots and synthetic test identities.
