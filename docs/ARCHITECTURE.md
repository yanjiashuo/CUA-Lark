# Architecture

## 1. Design position

CUA-Lark is a screenshot-first Computer-Use Agent for Feishu/Lark. The model decides what to do from the current image, a natural-language task, compact action history, and reusable public operation rules. It does not read the DOM or Accessibility Tree to replace visual reasoning.

The phrase “pure vision” refers to perception, state understanding, target choice, and completion judgment. Deterministic code is still used around the model for schema parsing, coordinate conversion, action allowlists, safety boundaries, execution, evidence capture, and reporting.

## 2. Execution loop

1. `Screen.capture()` captures the Feishu/Lark application window, a Docs browser window, or an explicitly requested full screen.
2. The runner selects scenario text for IM, Docs, Calendar/Mail fallback, or general desktop use.
3. Optional VLM rule selection chooses a small rule bundle and creates a Goal Contract.
4. The prompt builder combines the user instruction, recent observed history, action policy, scenario protocol, rules, and Goal Contract.
5. The VLM returns one action with visual grounding evidence.
6. The parser maps normalized 0–1000 coordinates into screenshot pixels and then screen coordinates.
7. Safety and optional Grounding Check run before execution.
8. The GUI adapter executes through PyAutoGUI.
9. A new screenshot records the observed result; the loop continues until `finished`, failure, cancellation, or the step budget.
10. Optional final visual verification and process-quality checks determine the reported state.

## 3. Core modules

| Layer | Module | Responsibility |
| --- | --- | --- |
| Runtime | `runtime/config.py` | Project-local paths, environment loading, YAML settings |
| Perception | `adapters/screen.py` | Window discovery, capture, scale metadata, visual differences |
| Model | `adapters/vlm.py` | Chat Completions / Responses API image calls and retry behavior |
| Domain | `domain/models.py` | Test cases, actions, steps, results and coordinates |
| Grounding | `domain/action_parser.py`, `domain/coordinates.py` | Parse model output and map coordinates |
| Execution | `adapters/gui.py` | Mouse, keyboard, scroll, drag and batch execution |
| Planning | `testing/prompt.py`, `testing/rule_selector.py` | Step prompt, verification prompt, Rule Pool and Goal Contract |
| Reliability | `testing/action_policy.py`, `testing/grounding_check.py`, `testing/process_quality.py` | Allowed actions, risky-click review and trajectory quality |
| Orchestration | `testing/runner.py` | Capture–decide–act–observe loop |
| Evidence | `reporting/writer.py` | JSON, Markdown, screenshots, timing and Mermaid flow |
| Interface | `cli.py`, `web/app.py` | CLI and local Web control surfaces |

## 4. Goal Contract

The Rule Selector derives a contract from the user instruction and the visible UI:

- `goal`: user-visible final state;
- `completion_evidence`: evidence sufficient to finish;
- `non_completion_evidence`: common false positives such as drafts, old messages, previews, or open menus;
- `must_not`: duplication and destructive-action constraints.

The contract is fixed before main execution and is never built from hidden `expected` or verifier assertions.

## 5. Grounding contract

Visual actions use a five-part record:

```text
target + bbox + point + confidence + evidence
```

`bbox` and `point` are initially normalized to the screenshot. Capture metadata records the actual window bounds and scale, allowing the executor to map the point to the real desktop. Reports store the raw model output, mapped point, crop, nearby elements, and any Grounding Check correction.

## 6. Reliability layers

- Action-policy inference limits action types by product and task.
- Docs host checks prevent operations on unrelated apps, system UI, address bars, and wrong browser tabs.
- Grounding Check can ask the VLM to review high-risk or all click points on an annotated crop.
- Loop suppression stops repeated bold toggles, divider insertion loops, and premature table-repair completion.
- Process-quality rules distinguish nominal completion from a clean trajectory, including real @ tokens, real replies, correct title/body placement, no raw Markdown residue, and no unfinished selection state.
- The final verifier uses only final-state criteria and is separated from the execution prompt.

## 7. Reporting model

Reports are written after each step, not only at the end. A crash therefore leaves a partial, inspectable trajectory. Machine-readable `record.json` and `summary.json` coexist with reviewer-oriented `steps.md`, `flow.md`, screenshots, overlays, and per-stage timing.

## 8. Deliberate exclusions

- No vendored copy of the unrelated `trycua/cua` repository.
- No DOM or Accessibility Tree grounding in the public v1.0 core.
- No product API used as hidden execution state.
- No runtime screenshots, private chat data, test-account identifiers, local configuration, or API keys in Git.
- No claim that historical “ever passed” cases form one clean, current full-suite pass.
