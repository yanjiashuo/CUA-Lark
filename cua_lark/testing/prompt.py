from __future__ import annotations

from cua_lark.domain.models import ActionKind, GoalContract, StepResult, TestCase


def build_step_prompt(
    case: TestCase,
    history: list[StepResult],
    *,
    rules_prompt: str = "",
    goal_contract: GoalContract | None = None,
) -> str:
    lines = [
        "Task:",
        case.instruction,
        "",
        *_input_material_lines(case),
        "",
        "Execution history:",
    ]
    if not history:
        lines.append("- none")
    else:
        for step in history[-6:]:
            action = step.action.kind.value if step.action else "parse_error"
            target = step.action.target if step.action else ""
            thought = step.action.thought if step.action else ""
            message = step.message or ("ok" if step.passed else "failed")
            visual = step.visual_change.get("status", "unknown") if isinstance(step.visual_change, dict) else step.visual_change
            lines.append(
                f"- step {step.index}: action={action}; target={target}; thought={thought}; "
                f"execution_result={message}; observed_visual_change={visual}"
            )
    lines.extend(_goal_contract_lines(goal_contract))
    if rules_prompt.strip():
        lines.extend(["", "Selected operation rules:", rules_prompt.strip()])
    lines.extend(
        [
            "",
            *_focus_stability_protocol(history),
            *_input_no_change_recovery_protocol(history),
            *_docs_insertion_focus_protocol(case, history),
            *_docs_structure_insertion_click_protocol(case, history),
            *_docs_move_recovery_protocol(case, history),
            *_docs_popup_close_recovery_protocol(case, history),
            *_docs_entry_repeat_protocol(case, history),
            *_docs_repeated_find_protocol(case, history),
            *_docs_structure_after_find_protocol(case, history),
            *_docs_slash_command_repeat_protocol(case, history),
            *_task_protocol(case),
            *_composer_protocol(case),
            *_general_product_navigation_protocol(case),
            *_docs_protocol(case),
            *_message_operation_protocol(case),
            *_attachment_share_protocol(case),
            *_rich_text_protocol(case),
            *_batch_protocol(case),
            "",
            "Choose the next concrete GUI action from the scenario action vocabulary.",
            "Follow the scenario response format exactly: include CompletionCheck, Thought, Grounding, Action, and Expected.",
            "For batch output, include exactly one compact JSON Actions: line after Action: batch().",
            "Always include an Action: line. If the next best step is to pause, use Action: wait().",
            "Do not mention hidden verifier assertions. Do not invent coordinates for invisible targets.",
        ]
    )
    return "\n".join(lines)


def _goal_contract_lines(goal_contract: GoalContract | None) -> list[str]:
    if not goal_contract:
        return []
    lines = ["", "Goal contract:"]
    if goal_contract.goal:
        lines.append(f"- Goal: {goal_contract.goal}")
    if goal_contract.completion_evidence:
        lines.append("- Completion evidence: " + "; ".join(goal_contract.completion_evidence))
    if goal_contract.non_completion_evidence:
        lines.append("- Non-completion evidence: " + "; ".join(goal_contract.non_completion_evidence))
    if goal_contract.must_not:
        lines.append("- Must not: " + "; ".join(goal_contract.must_not))
    return lines


def _focus_stability_protocol(history: list[StepResult]) -> list[str]:
    if not history:
        return []
    last = history[-1]
    if not isinstance(last.visual_change, dict) or last.visual_change.get("status") != "focus-likely":
        return []
    return [
        "Input focus stability protocol:",
        "- The previous click likely focused an input/composer/search field; caret visibility may blink and is not a stable screenshot signal.",
        "- Do not repeat the same input click only because the caret is not visible. If the task needs text input and no blocking popup appeared, proceed with type_text.",
        "",
    ]


def _input_no_change_recovery_protocol(history: list[StepResult]) -> list[str]:
    if not history:
        return []
    recent_type_steps = [
        step
        for step in history[-3:]
        if step.action
        and step.action.kind == ActionKind.TYPE_TEXT
        and isinstance(step.visual_change, dict)
        and step.visual_change.get("status") == "no-visible-change"
    ]
    if len(recent_type_steps) < 2:
        return []
    last_text = recent_type_steps[-1].action.text if recent_type_steps[-1].action else ""
    prev_text = recent_type_steps[-2].action.text if recent_type_steps[-2].action else ""
    if last_text != prev_text:
        return []
    return [
        "Input no-change recovery protocol:",
        "- The same text was typed more than once, but the screenshot did not visibly change.",
        "- Do not type that same text again as the next action.",
        "- If the old query/text is still visible or selected in a search/input field, first refocus the visible field or clear it with backspace/visible clear control, then type once.",
        "- If the intended query is already visible and a matching result is shown, open the visible result or press Enter instead of repeating type_text.",
        "",
    ]


def _docs_insertion_focus_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_edit_task(text) or not history:
        return []
    last = history[-1]
    if not last.action or last.action.kind.value != "click":
        return []
    visual_status = last.visual_change.get("status", "unknown") if isinstance(last.visual_change, dict) else last.visual_change
    target_text = " ".join([last.action.target, last.action.thought]).lower()
    if visual_status not in {"no-visible-change", "focus-likely", "small-change"}:
        return []
    if not any(term in target_text for term in ["paragraph", "段落", "正文", "body", "end of", "末尾", "cursor", "光标"]):
        return []
    return [
        "Docs insertion focus protocol:",
        "- The previous click targeted a document body paragraph or insertion point. In Docs, caret/focus changes can be visually subtle.",
        "- If no blocking popup appeared and the next task is to add or edit text, do not keep clicking the same paragraph endpoint.",
        "- Proceed with the requested type_text content, or use shift enter/enter first only if a new paragraph is needed before typing.",
        "",
    ]


def _docs_structure_insertion_click_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    text = " ".join([case.id, case.name, case.instruction, case.stage]).lower()
    if not _docs_table_task(text) and "分割线" not in text and "divider" not in text:
        return []
    last = history[-1]
    if not last.action or last.action.kind != ActionKind.CLICK:
        return []
    target_text = " ".join([last.action.target, last.action.thought, last.action.raw_text]).lower()
    if not _is_docs_structure_insertion_point_text(target_text):
        return []
    return [
        "Docs structure insertion-point protocol:",
        "- The previous click targeted the trailing end of an anchor line or a body insertion point for a table/divider/structure task.",
        "- Caret placement in Docs may be visually subtle; do not repeat that same insertion-point click as the next action.",
        "- If the anchor sentence has trailing punctuation such as '。' or '.', keep the caret after that punctuation, then create a true empty body block with hotkey enter or shift enter before opening slash/table/divider controls.",
        "- The next action should advance the structure insertion: create the empty block, open a visible insert/table/divider control, or use a clear fallback. It should not be another click on the same line end.",
        "",
    ]


def _docs_move_recovery_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_move_task(text):
        return []
    observed_zero = any(
        _contains_any(
            " ".join(
                [
                    step.action.target if step.action else "",
                    step.action.thought if step.action else "",
                    step.message or "",
                    step.raw_model or "",
                ]
            ).lower(),
            ["0 matches", "0/0", "0 / 0", "no matches"],
        )
        for step in history
    )
    if not observed_zero:
        return []
    return [
        "Docs move dirty-data recovery protocol:",
        "- A prior step already observed zero matches for the source paragraph. Do not search, scroll, or infer that the source is above/below the current viewport.",
        "- The next goal is fixture recovery: close any find panel if it is still open, then focus immediately before the visible target paragraph and type the exact source paragraph once followed by Enter.",
        "- If the target paragraph is visible, do not leave it to hunt for the missing source. Insert the source immediately before that target.",
        "",
    ]


def build_verify_prompt(case: TestCase) -> str:
    assertion = case.verification.get("assertion") or case.expected
    lines = [
        "You are verifying the final screenshot of a GUI test.",
        "Return exactly one line starting with PASS or FAIL.",
        f"User instruction: {case.instruction}",
        f"Expected result: {case.expected}",
        f"Assertion: {assertion}",
    ]
    lines.extend(_docs_verify_protocol(case))
    return "\n".join(lines)


def _docs_entry_repeat_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_entry_open_task(text):
        return []
    recent_clicks = [
        step
        for step in history[-4:]
        if step.action
        and step.action.kind in {ActionKind.CLICK, ActionKind.DOUBLE_CLICK}
        and _contains_any(
            " ".join([step.action.target, step.action.thought, step.action.raw_text]),
            ["search result", "document result", "document row", "document title", "文档", "搜索结果"],
        )
    ]
    if len(recent_clicks) < 2:
        recent_open_attempts = [
            step
            for step in history[-5:]
            if step.action
            and step.action.kind in {ActionKind.CLICK, ActionKind.HOTKEY, ActionKind.WAIT}
            and _contains_any(
                " ".join([step.action.target, step.action.thought, step.action.raw_text]),
                ["search result", "document result", "exact title", "exact matching", "目标文档", "搜索结果"],
            )
        ]
        if len(recent_open_attempts) < 3:
            return []
        return [
            "Docs entry repeat-stop protocol:",
            "- You have already tried to open the same exact document result and then waited or pressed Enter, but the same search/result surface appears to remain.",
            "- First inspect the current screenshot: if the requested document title is now visible as the opened page title, return finished immediately.",
            "- Do not click that same result again. If the same search popup still blocks the page, use hotkey esc once to close it, then continue from the underlying Docs entry surface or a different visible open affordance.",
            "",
        ]
    targets = [" ".join([step.action.target, step.action.thought]).lower() for step in recent_clicks]
    repeated = any(
        targets[i] and targets[i + 1] and (targets[i] in targets[i + 1] or targets[i + 1] in targets[i])
        for i in range(len(targets) - 1)
    )
    if not repeated:
        return []
    return [
        "Docs entry repeat-stop protocol:",
        "- You have already clicked the same visible document/search result more than once in this entry/open task.",
        "- First inspect the current screenshot: if the requested document title is now visible as the opened page title, return finished immediately.",
        "- If the same search popup/result is still visible, do not click that same result again. Use hotkey esc once to close a blocking search popup, then continue from the underlying Docs entry surface or a different visible open affordance.",
        "",
    ]


def _docs_repeated_find_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    find_attempts = [
        step
        for step in history[-6:]
        if step.action
        and _contains_any(
            " ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(),
            ["find", "查找", "command f", "文档内搜索", "in-document search"],
        )
    ]
    if len(find_attempts) < 3:
        return []
    return [
        "Docs repeated-find stop protocol:",
        "- Recent successful steps have repeatedly opened or typed into document find/search. Do not issue command f, type the same anchor, or reopen the find panel again as the next action.",
        "- First inspect the current screenshot. If the requested anchor/phrase is visible in the page, operate directly on that visible text or its adjacent insertion point.",
        "- If a find panel is open and blocks work, close it once with Esc, then continue from the visible target text. If the target is still not visible after closing, scroll the live Docs body rather than repeating the same find query.",
        "",
    ]


def _docs_slash_command_repeat_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_table_task(text) and "分割线" not in text and "divider" not in text:
        return []
    slash_attempts = [
        step
        for step in history[-8:]
        if step.action
        and (
            step.action.text.strip().lower() in {"/", "/表格", "/table", "/分割线", "/divider"}
            or _contains_any(
                " ".join([step.action.text, step.action.thought, step.action.target, step.action.raw_text]).lower(),
                ["slash", "表格", "table", "分割线", "divider"],
            )
        )
    ]
    if len(slash_attempts) < 2:
        return []
    return [
        "Docs slash-command repeat-stop protocol:",
        "- Recent steps already tried slash-command text for this structure task, but no visible slash menu or rendered structure appeared.",
        "- Do not type '/', '/表格', '/table', '/分割线', or similar slash text again as the next action.",
        "- If literal slash-command text is visible in the body, clear it once; then use a visible Docs toolbar, block handle, insert '+', table/divider menu item, or another non-slash visible control.",
        "- The insert '+' must be a Docs-page insert control near the editor or toolbar, not the browser tab/new-page plus in the browser chrome.",
        "",
    ]


def _docs_structure_after_find_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _docs_table_task(text) and "分割线" not in text and "divider" not in text:
        return []
    saw_find = any(
        step.action
        and (
            (step.action.kind == ActionKind.HOTKEY and (step.action.key or "").lower() == "command f")
            or _contains_any(" ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(), ["find", "查找", "搜索"])
        )
        for step in history[-8:]
    )
    if not saw_find:
        return []
    saw_esc_after_find = False
    for step in history[-8:]:
        if step.action and step.action.kind == ActionKind.HOTKEY and (step.action.key or "").lower() == "esc":
            saw_esc_after_find = True
    if saw_esc_after_find:
        return []
    return [
        "Docs structure-after-find protocol:",
        "- You used document find/search to locate the anchor for a table/divider/structure task. The find popup or active search highlight may still be open.",
        "- Before typing '/', using slash commands, or inserting structure, close the find/search panel with hotkey esc once.",
        "- After Esc, operate from the visible anchor, place the caret after the full sentence including final punctuation, create a true empty body block, then continue.",
        "",
    ]


def _docs_popup_close_recovery_protocol(case: TestCase, history: list[StepResult]) -> list[str]:
    if (case.product or "").lower() != "docs" or not history:
        return []
    recent_close_clicks = [
        step
        for step in history[-3:]
        if step.action
        and step.action.kind == ActionKind.CLICK
        and _contains_any(
            " ".join([step.action.target, step.action.thought, step.action.raw_text]).lower(),
            ["close", "关闭", "x button", "搜索弹窗", "search popup"],
        )
        and isinstance(step.visual_change, dict)
        and step.visual_change.get("status") in {"no-visible-change", "small-change"}
    ]
    if len(recent_close_clicks) < 1:
        return []
    return [
        "Docs popup close recovery protocol:",
        "- The previous click tried to close a Docs popup or search popup but produced little or no visible change.",
        "- Do not click the same close/X target again as the next action.",
        "- Prefer hotkey esc once to dismiss the popup. If Esc was already tried and the popup-looking area still remains, treat it as embedded page/document content and continue through visible Docs navigation or create controls.",
        "",
    ]


def _task_protocol(case: TestCase) -> list[str]:
    protocols: list[str] = []
    if _mentions_required(case):
        protocols.extend(
            [
                "Task-specific operation protocol:",
                "- This task requires a real @ mention token.",
                "- Do not type a plain '@Name message' as normal text.",
                "- First create the mention token through the visible mention UI: type only '@' or click the visible @ button, then select the target person from the mention picker.",
                "- After the mention token is inserted, append only the remaining message text without clearing or overwriting the token.",
                "- Send the message only after the real mention token and remaining text are both visible in the input area.",
            ]
        )
    return protocols


def _general_product_navigation_protocol(case: TestCase) -> list[str]:
    """Minimal universal Feishu app-entry hint for products without deep prompt rules."""
    product = (case.product or "").lower()
    if product in ("docs", "im", ""):
        return []
    product_name_map = {
        "calendar": "日历/Calendar",
        "mail": "邮箱/Mail",
        "base": "多维表格/Base",
        "vc": "视频会议/VC",
    }
    display_name = product_name_map.get(product, product)
    return [
        "",
        "Product navigation protocol:",
        f"- This task targets the Feishu {display_name} module.",
        f"- If the current screenshot does NOT show the {display_name} interface, recover to the Feishu host in the simplest visible way:",
        "  1. If any live Feishu sidebar, tab, or window is already visible, use that visible Feishu host as the starting point.",
        "  2. If Feishu is visible but not already on the target surface, stay within the visible Feishu host and identify the relevant entry from the current screenshot and task.",
        "  3. If Feishu is not visible at all, use one visible app-launch action to open or activate Feishu, then continue from the visible Feishu host.",
        "  4. Use a launcher fallback such as Spotlight only when no Feishu surface is visible at all, and use it once.",
        f"- Once you are inside the {display_name} module, proceed with the task instructions using the visible UI elements.",
        "- Do not wander through unrelated apps, web pages, or generic search results to locate Feishu when a visible Feishu surface or a direct app-launch path exists.",
        "- Do not attempt to perform task actions (create events, compose emails, etc.) while still on an unrelated screen.",
    ]


def _composer_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() == "docs":
        return []
    if not _is_send_or_compose_task(case):
        return []
    lines = [
        "",
        "Composer state protocol:",
        "- Before composing a new outgoing message, inspect the visible composer.",
        "- If the composer contains unrelated draft text, emoji-only leftovers, a stale local file path, or partial text from a previous failed attempt, clear it before starting the new message.",
        "- If the composer already contains the desired message or a desired token/attachment for the current task, preserve it and continue from that visible state.",
    ]
    if _mentions_required(case):
        lines.extend(
            [
                "- For mention tasks, after a real mention token is inserted, do not use command a or backspace in the composer unless you are explicitly abandoning the whole draft and restarting from an empty composer.",
                "- If the mention picker does not appear after typing '@', clear the unrelated draft first, then create the mention token again from the empty composer.",
            ]
        )
    return lines


def _docs_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() != "docs":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    lines = [
        "",
        "Docs operation protocol:",
        "- Use the visible Feishu Docs UI. Do not use hidden APIs, fixed coordinates, local files, or clipboard-only shortcuts to create, edit, or share documents.",
        "- If the user provided local text or Markdown material in this prompt, you may paste that provided content into the visible Docs editor after visually opening the target document and focusing the correct body area.",
        "- Pasting provided text material is allowed as a user-level input action; using local files, hidden APIs, hidden links, DOM, or backend state to bypass the visible Docs UI is not allowed.",
        "- Ignore browser chrome such as Safari tabs, address bar, browser share button, and browser new-tab plus unless the task explicitly asks to control the browser.",
        "- Distinguish the document title field, body editor, toolbar, slash-command menu, search results, and share dialog by current screenshot evidence.",
        "- Docs host precondition: before any Docs edit, format, link, share, permission, find, drag, type, or editor hotkey action, confirm the current screenshot is a live Feishu/Lark Docs host surface. This applies even when the instruction does not name a document title and assumes a document is already open.",
        "- A live Docs host surface is a real Docs editor/page/home/search/share UI in the active app or browser host. A screenshot, result report, chat transcript, note, image, preview, or embedded page that merely depicts Docs is not a live Docs host.",
        "- If the screenshot is not a live Docs host, do not press command-k/command-f/command-b, do not type, drag, or click toolbar controls as if editing Docs. Recover to Feishu app -> 云文档/Docs first, then continue, even if the case text is otherwise already about Docs content.",
        "- Target-document precheck protocol: for every Docs edit, format, link, comment, share, material, or provision task, first decide whether the current screenshot is already the exact target cloud document. If it is the target document in browser Docs, operate there. If it is not the target document, do not search, create, or navigate further inside browser Docs; recover through Feishu app -> 云文档/Docs, search or create the exact title there, and then continue after browser Docs handoff.",
        "- If the exact target document is visible only inside the Feishu desktop embedded editor for a content/provision task, do not edit the body and do not return finished. Use a visible open-in-browser/external-open control if available, or return to Feishu app -> 云文档/Docs, search the exact title, open the matching result, and wait for browser handoff.",
        *_docs_browser_execution_host_protocol(text),
        "- Do not operate controls that are merely depicted inside the document body, images, screenshots, cards, or embedded content. A popup-looking panel inside the document page is not a live blocking dialog unless it visibly floats above the app UI and responds as an overlay.",
        "- If a popup-looking object remains after close/Esc attempts, or it has document watermarks/page layout around it, treat it as embedded document content and stop trying to close it; continue via real Docs navigation/search controls.",
        "- Entry decision protocol: first decide from the current screenshot whether the target document or required Docs state is already visible. If yes, stay on this page and continue the requested operation or finish if the goal is already satisfied.",
        "- For document entry/open/current-document tasks, if the exact requested document title is already visible in the Docs title, breadcrumb, or main document area, return finished immediately; do not click Edit, the body, search, navigation, or the same target document again just to keep using the document.",
        "- Opening or remaining on the readable target document satisfies entry/open tasks. Edit mode is required only when the instruction explicitly asks to change content, formatting, sharing, or permissions.",
        "- Unified Docs entry protocol: for document entry/open tasks, if the exact target document is not already visible, return to the Feishu app/Docs cloud-document entry surface, search the exact full document title from the cloud-docs content search box/top Docs search, open the matching result, and finish only after the exact title is visible on the document page.",
        "- For cloud-document entry/open tasks, do not use the far-left Feishu global search box, browser Docs home/search, or a recent-list shortcut as the primary search surface; use the Feishu app Docs cloud-document search area instead.",
        "- When switching from one already-open Docs document to a different named document, first return to the Feishu app/Docs cloud-document entry surface, then search the exact title there. Do not open directly from the recent list as the default route, and do not use the editor-page top-right magnifier as the primary document-entry search.",
        "- If a Docs search box is already open and contains the exact full document title, visually identify and click the matching result with the exact title once. On the next screenshot, if the exact title is visible on the opened document page, return finished immediately. If the same search popup remains, do not click the same result again as the immediate next action; wait once for navigation/loading evidence, then use Enter or another visible open affordance only if the same focused result is still present.",
        "- If multiple exact-title search results are visible, do not default to the first same-title row blindly. Prefer the row whose snippet, metadata, or surrounding context best matches the current case's unique anchor or expected document state, then wait for navigation evidence.",
        "- If replacing an old Docs search query with the exact target title produces no visible change, do not keep typing the same title. Refocus or clear the visible Docs search field once, then type again, or open the visible exact-title result if it is already shown.",
        "- To close a Docs search popup, prefer hotkey esc. A visible X inside the search input may only clear text or fail to dismiss the popup; if one close/X click leaves the popup unchanged, do not click that same X again.",
        "- Prefer exact-title Docs search over browser-tab switching, recent-list guessing, sidebar guessing, or scanning many documents.",
        "- Recent documents and sidebar entries are fallback routes only after the cloud-docs search route is unavailable or has clearly failed.",
        "- In Feishu Docs home/list/recent file tables, do not open a requested document directly from a recent row by default. Prefer the cloud-docs search box with the exact full title; use double-click on the exact title text only as fallback after search is unavailable or failed.",
        "- For document entry/open tasks, use one clear opening gesture on a visible exact-title search result after searching; direct recent-list row opening is fallback only.",
        "- For visible document list rows, target the middle of the full title text, not the icon, row edge, empty row space, date/time columns, or a highlighted different row.",
        "- After one opening gesture, wait for navigation or loading evidence on the next screenshot before retrying the same row.",
        "- Do not click the same exact-title search result in two consecutive steps.",
        "- If the same document row/card remains after one opening gesture, choose a different visible route such as sidebar/search/open button; do not do click-click-double-click loops on the same row.",
        "- For explicit new-document creation tasks, do not search for an existing same-title document first. If the exact requested document is not already open and already satisfying the goal, recover to Feishu app -> 云文档/Docs and use a visible New/Create document entry to create a fresh document with the requested title.",
        "- For create-or-confirm/provisioning tasks that explicitly ask to confirm reuse of an existing target, search the exact full document title at most once. If the visible result state clearly shows no matching document, close the search popup if needed and create a new document with the exact requested title. Do not repeat the same exact search.",
        "- For provisioning after no search result, shortcut create entries such as an unlabeled plus button are allowed only with evidence gating: surrounding Docs UI, tooltip/menu, toolbar/sidebar context, or previous visible state must support that it is a new/create control. If one shortcut attempt does not reveal a create/new-document menu or page, do not repeat it; switch to a clearer labeled 新建/新建文档/创建 entry, sidebar create entry, or Docs home create button.",
        "- For finding text inside the currently open document, prefer command f or a visibly document-scoped find box. Do not repeatedly click the top-right global search icon if it opens an app-wide/global search popup.",
        "- If Feishu desktop is visible but Docs is not open, use a visible Docs/云文档 entry. If neither Feishu nor Docs content is visible, choose or open the Feishu app first; use browser Docs only for browser-specific entry cases or when Feishu app recovery fails.",
        "- Do not click browser tabs, system menu icons, app icons, or browser chrome to navigate unless no Feishu/Docs content area is visible in the screenshot, or a visible browser tab is clearly the exact requested target document title.",
        "- For entry/open tasks, do not use browser tab switching as the primary path when a Docs entry/search route is available.",
        "- For non-browser entry cases, a frontmost browser Feishu Docs page is allowed as a precheck surface: if it already shows the exact target document, return finished immediately. If it is Feishu Docs but not the target document, do not use browser Docs home/search as the default route; switch/open Feishu app, enter 云文档/Docs, then search the exact full title.",
        "- For entry/open tasks from inside another document, do not use the editor-page top-right magnifier as the main way to open the requested document.",
        "- For entry/open search results, click a visible exact-title result before using Enter.",
        "- After a document entry/open task reaches the target document page, do not reopen search or click the target title again; return finished.",
        "- If a dropdown, menu, share dialog, or permission panel blocks the document and is unrelated to the current task, close it or click back into the Docs content area before continuing.",
        "- If the same blocking dialog or menu remains after a close-button click, do not repeat the same click; try Esc or a visible outside/content-area click to return to the Docs content.",
        "- If the document is loading, saving, or switching views, wait until the visible state is stable before the next content-editing action.",
        "- If the intended document or editor is not visible, navigate by visible Docs entry and cloud-docs search box rather than assuming a location. Recent document lists are fallback only after search is unavailable or failed.",
        "- Current-visible-target priority: if the requested target title, anchor, phrase, or paragraph is already visible in the current Docs page, do not open or repeat document find/search for it. Operate directly on the visible target or the visible insertion point next to it.",
        "- If a find/search panel is open while the requested target text is already visible in the page, do not type the same query again. Close the panel with Esc if it blocks the workspace, then continue from the visible target.",
        "- Treat document content as persistent test data: do not clear the whole document unless the task explicitly asks to replace all content.",
        "- Prefer adding new test content at the document end or a clearly empty paragraph, using the case id text in the instruction as the unique evidence for this run.",
        "- If the exact target text already exists, do not duplicate it unless the instruction explicitly says to add another copy; verify whether the visible state already satisfies the task.",
        "- Anchor insertion-point protocol: when inserting after an anchor sentence or paragraph, place the caret after the full visible sentence including its trailing Chinese/English punctuation such as 。、.、：、；、！、？. Do not insert before the final punctuation mark.",
        "- If the trailing punctuation of the anchor appears alone on the next line or separated from the sentence after an insertion, treat that as a boundary error; repair by keeping the punctuation attached to the original sentence before finishing.",
        "- Exact-span operation protocol: for tasks that format, link, replace, delete, copy, move, or otherwise modify a specified local text span, operate only on the exact requested span.",
        "- Exact-span means every requested character is included, including Chinese/English punctuation, quotes, spaces that are part of the quoted target, hyphens, digits, colons, and suffix IDs.",
        "- Before applying a local span action, visually check that the selection begins and ends on the requested text. Do not select the whole sentence, the whole paragraph, nearby spaces, neighboring words, or only the case-id anchor unless that is exactly the requested text.",
        "- If the selection boundary is visibly uncertain, clear the selection and use document find or a more precise selection route that is present in this case's allowed-action list before applying formatting, link, delete, replace, cut, or copy.",
        "- For Docs comment/annotation tasks, after the exact target span is selected and the floating toolbar appears, use the visible comment/speech-bubble icon in that toolbar. Do not use right-click as the normal comment path in Feishu Docs, and do not repeat drag-selection while the toolbar comment icon is already visible.",
        "- After a local span edit, clear transient find/search highlights, text selection, or floating toolbars before returning finished, unless the visible popup itself is required evidence such as a link URL popover.",
    ]
    if _docs_create_task(text):
        lines.extend(
            [
                "- Provision/create host protocol: start from the Feishu app -> 云文档/Docs surface. Do not open a browser new tab, address bar, ordinary web page, browser history, or unrelated app to create the document.",
                "- For document creation, use the visible new/create document control and verify that an editable document page is open before setting the title.",
                "- After opening or creating the provision target from Feishu cloud-docs, prefer browser Docs before typing the title or body material. Do not paste long material into the Feishu desktop embedded editor when browser handoff can be reached.",
                "- If the task only asks to enter/open a new editable document page, return finished as soon as a blank document editor is visible with a title field or body editor; do not set a title unless the instruction explicitly requests one.",
                "- After selecting a blank/new document card, if the current screenshot shows a loading state such as 创建中, loading, opening, or a spinner, wait for the editor page instead of clicking any create/new control again.",
                "- If a blank document editor, 未命名文档 title field, or editable body placeholder becomes visible after a create action, return finished for open-new-document smoke tasks.",
                "- If this task asks to ensure a document exists, first search the exact full title once. If no matching result is visible, create a new blank document and set the title; do not keep searching the same missing title.",
                "- When creating after a no-result search, a shortcut plus/create control is acceptable if current visual evidence supports it. If it does not produce a create/new-document menu or page after one attempt, abandon that shortcut and use a clearer create path.",
                "- If you are already inside any document editor while the requested provision document is not complete, do not keep creating or repairing from that editor page. First return to the cloud-docs home/library surface, then use the visible home/library New/Create control.",
                "- If the screenshot already shows an editable document page with a title field and body editor, do not click any create/new button again; return finished if the task only asks to enter a new editable document page.",
                "- When setting a title, target the title field specifically; do not type the title into the body editor unless the title field is unavailable and visibly equivalent.",
            ]
        )
    if _docs_edit_task(text):
        lines.extend(
            [
                "- For body editing, target the body editor specifically; do not overwrite the document title when the task asks for正文/body content.",
                "- In Feishu Docs, the body editor is below the document title and author/modified metadata line; a click inside the large title text is not a valid body-editing click.",
                "- Before typing body content, make sure the current screenshot shows a body paragraph, body placeholder, or insertion area below the author/modified metadata; if the candidate point is still within the title block, choose a lower body area first.",
                "- After typing body content, do not type the exact same case-id text again. If the text appears in the wrong title area, the case needs correction rather than duplicating it in the body.",
                "- Preserve existing relevant document content unless the task explicitly asks to replace it.",
                "- If unrelated old content is present, move to a safe empty line or document end before typing the new case-id text.",
            ]
        )
    if _docs_structure_task(text):
        lines.extend(
            [
                "- For headings and lists, create real document structure through visible formatting controls, slash commands, or valid editor shortcuts; do not merely type explanatory labels as plain text.",
                "- For heading + list tasks, the heading line must be a real heading/subheading style before finishing. A standalone ordinary body line above a valid bullet list is not enough.",
                "- For divider tasks, typed `/分割线` or `/divider` text is only a trigger. If plain text remains after the trigger, delete it and use the visible divider insertion control or slash-menu option until a rendered horizontal divider is visible.",
                "- For divider tasks, do not batch the anchor/insertion click together with typing `---`. First focus the exact point between the anchors, inspect the next screenshot, then insert the divider only if the caret/location is correct.",
                "- For divider tasks, if a slash or insert menu is open but no visible divider/separator option is present, do not scroll that menu more than once and do not click `更多` repeatedly. Close the menu, focus the empty body block between the target paragraphs, type `---`, then press Enter once; Feishu-style editors commonly render that Markdown shortcut as a horizontal divider.",
                "- For divider tasks, after typing `---` and pressing Enter once, do not type `---` again on the next step. First inspect for the thin rendered gray divider; it is easy to miss but counts as the divider.",
                "- For divider tasks, if `---` remains as plain text after Enter, delete only that plain `---` and switch to a visible insert/separator control if one is clearly available; do not keep typing more slash or menu search text.",
                "- For divider tasks between two existing anchors, avoid leaving an extra blank editable paragraph below the divider. The after-anchor should follow the divider with normal editor spacing, not a separate empty body line.",
                "- For divider tasks, if the divider is visible and the caret is in an empty paragraph between the divider and the after-anchor, use hotkey(key='delete') once to remove that empty paragraph and pull the after-anchor up to normal spacing. Do not use Backspace from that position unless the screenshot clearly shows it will not delete the divider.",
                "- For divider tasks, return finished as soon as a rendered horizontal divider is visible between the requested before/after anchors and there is no obvious extra blank paragraph inserted below it. A thin gray horizontal line counts as divider evidence even if a find popup, red search highlight, or caret is still visible.",
                "- Do not click the divider area, nearby empty line, or slash trigger again after a divider is already visible between the requested anchors.",
                "- When a focused paragraph shows a nearby block type control such as a T icon, paragraph-style button, six-dot/block handle, or formatting popover, use that visible control to choose heading or list style.",
                "- Do not invent unverified heading shortcuts such as command shift 1 unless the current screenshot or visible editor help explicitly indicates that shortcut is supported.",
                "- For a second-level heading, prefer the visible paragraph-style/T/block-type menu and choose heading 2/二级标题 after placing the cursor in that heading line.",
                "- If the requested heading text is visible as plain text with a literal markdown prefix like '## ', do not keep typing more markers; convert that same line through the visible style control instead.",
                "- After one clear structure insertion attempt, stop as soon as the requested text is visible with an obvious heading/list visual style; return finished and let the verifier judge the final state.",
                "- Do not repeatedly click, type spaces, backspace, or toggle edit mode just to cosmetically refine a heading/list after the requested structured content is already visible.",
                "- If a markdown shortcut leaves a visible marker but the requested text already appears with heading/list styling, do not keep repairing it within the same test case unless the instruction explicitly asks to remove that marker.",
                "- For marker-cleanup maintenance tasks, if the target heading is already visible without the marker and still has heading styling, return finished immediately.",
                "- For marker-cleanup maintenance tasks, do not switch view/edit mode just to look for an old marker when the current screenshot already shows the target heading without '#'.",
                "- For marker-cleanup maintenance tasks, only click near the heading and press Backspace when a visible leading '#' or '# ' is still directly before the target heading text.",
                "- If a cleanup attempt merged the target heading into the previous paragraph/list item or removed its heading styling, use command z once and reassess before any further edit.",
                "- Insert new headings or lists near the current document end; do not overwrite existing paragraphs or previous test evidence.",
                "- After inserting a list or heading, continue only from visible evidence that the editor accepted the structure or text.",
            ]
        )
    if _docs_heading_toc_task(text):
        lines.extend(
            [
                "- For heading plus outline/目录 tasks, first create the heading as a real heading, then use the visible outline/目录 button or left-side document outline to locate it.",
                "- The document outline/目录 is not the global Feishu file/navigation sidebar. If the left panel shows items such as 主页, 云盘, 知识库, recent documents, or document library entries, do not scroll or click it for a TOC task; open the document's own 目录/outline panel instead.",
                "- After creating the requested heading, go directly to the document 目录/outline control and click the exact new heading entry once. Do not repeatedly scroll the global sidebar or reopen search while the heading is already visible in the body.",
                "- If the new heading is already visible in large/bold heading style, return finished even if a duplicate plain or markdown-marker version is also visible from an earlier dirty run.",
                "- If the new heading is already visible with heading styling and the outline/目录 panel also shows it, the task is complete; return finished instead of retyping or reopening menus.",
                "- If the new heading is already visible in the current viewport because you just used the outline/目录 to jump there, return finished.",
                "- Do not create another copy of the same heading once the requested heading text is visible as a heading.",
            ]
        )
    if _docs_table_task(text):
        lines.extend(
            [
                "- For table tasks, create a real rendered Docs table through a visible table insert control, toolbar/menu table control, or slash-menu table option.",
                "- Do not rely on Markdown table text to auto-convert. A visible plain-text table like '| 事项 | 负责人 | 状态 |' is not success.",
                "- If a prior dirty run left a plain Markdown table after the anchor, do not keep pressing Enter to convert it; either use a visible table control nearby or insert a real table after that residue and fill the requested cells.",
                "- Before using a slash command for table insertion, close any open find/search popup, floating toolbar, slash remnant, insert menu, or transient panel with Esc/click-away as appropriate; clear transient find highlighting if it blocks judgment; create a true empty body block after the anchor; and place the caret at the start of that empty block.",
                "- After clicking the trailing end of the anchor line once, do not click that same line end again just because the caret is hard to see; create the empty block with Enter/Shift Enter or open a visible table insertion control.",
                "- If the top-right 编辑/修订/阅读 mode dropdown is open, close or settle that dropdown first by choosing the current 编辑 mode or clicking back into the document body; do not press slash while that dropdown, a floating toolbar, an insert menu, or another transient UI has focus.",
                "- When the anchor line has trailing punctuation such as '。', create the empty block after that punctuation, not between the sentence body and its final punctuation.",
                "- Try slash/table entry at most once: press a real slash key with hotkey(key='/') only after the caret is in that true empty body block, then wait for a visible slash menu. Do not use type_text('/') because pasted slash text may not trigger the menu.",
                "- Do not type '表格' unless a slash menu/search field is visibly open and receiving the command.",
                "- If '/' appears as ordinary body text, the slash command did not trigger; immediately clear that literal '/', do not type another '/', do not type '/表格', and do not keep typing more slash text.",
                "- Do not use the top-right global '+' or global new/create menu for inserting a table into the document body. Its items such as 多维表格/表格/文档 create separate files or apps, not an inline table at the anchor.",
                "- If literal slash-command text such as '/', '//', or '/表格' is visible in the document body, clear that literal command text before continuing; after one failed slash trigger, switch to a visible toolbar, block-type, insert, table, list, or divider control path.",
                "- Once the rendered table grid is visible, fill cells in reading order: header row left-to-right, then the data row left-to-right.",
                "- Do not press Enter to move between table cells, because Enter may add a line inside the current cell. Click the next visible empty table cell before typing its value.",
                "- Before typing into a table cell, check whether the intended value is already visible in that same cell; do not type the same header or row value twice.",
                "- A header and its data value stacked as two text lines inside the same table cell is not a valid two-row table. A visible horizontal row boundary must separate the header row from the data row.",
                "- Common bad table pattern to reject and repair: `事项` appears directly above `素材复核`, `负责人` directly above `测试扩展`, and `状态` directly above `完成` inside the same three tall cells, with no horizontal grid line between header text and data text. The empty row below does not make that a valid data row.",
                "- If a dirty run left header/data stacked in the same cells with an empty row below, repair it before finishing: move the data values into the empty row cells or replace the bad table with one clean table whose header and data are separated by a row boundary.",
                "- Count populated table ROWS, not text lines. A valid result has two populated rows: row 1 contains only the three headers, row 2 contains only the three data values. If the table visually has one populated row whose cells contain both header and data text, followed by a blank row, it is still wrong even though six text values are visible.",
                "- If a table repair case starts on a page where the table already exists, do not return finished as the first action unless you can clearly see two populated rows separated by a horizontal line. When there is any doubt, repair the table instead of finishing.",
                "- Dirty stacked-table repair sequence: select only the wrongly stacked data text in the first header cell, use hotkey command x, click the empty data-row cell directly below the same column, then use hotkey command v. Repeat for the other columns. Do not reopen document find/search after selecting a wrongly stacked data value; the target table is already visible.",
                "- A double-click on a wrongly stacked data value is only selection, not repair. After such a selection, the next meaningful action must cut, paste, delete, or otherwise move that data into the empty data row before finishing.",
                "- Table row separation geometry check (MANDATORY before finishing any table task): look at the vertical height of each table cell. A correctly separated 2-row table has short cells (single line of text per cell). If the first-row cells are visibly TALL (roughly double height of normal single-line cells) and each cell shows two lines of text stacked vertically, the header and data are in the SAME row — this is the stacking defect. A valid result requires: (1) the header row cells each contain exactly ONE line of text (事项 / 负责人 / 状态), (2) the data row cells each contain exactly ONE line of text (素材复核 / 测试扩展 / 完成), and (3) a visible horizontal grid line separates these two rows.",
                "- Do NOT return finished if you see tall cells with two lines of text per cell. This means the data was typed into the same cell as the header using Enter instead of clicking into the next row. You must repair this.",
                "- Return finished only when a rendered table grid or table block is visible with the requested headers and row values in SEPARATE rows.",
            ]
        )
    if _docs_undo_redo_task(text):
        lines.extend(
            [
                "- For undo/redo tasks, after typing the requested new text once, undo that insertion with command z, then restore it with command shift z or shift command z.",
                "- Do not type the same requested text again as a substitute for redo. Re-typing after undo fails the undo/redo workflow because it does not prove redo recovery.",
                "- After redo, return finished when the requested final text is visible once in the correct document body location.",
            ]
        )
    if _docs_share_task(text):
        lines.extend(
            [
                "- For sharing, open the visible Share/分享 workflow, add the requested recipient in the share dialog, and use the dialog's visible send/share/confirm control.",
                "- If the requested recipient is already visible in the collaborator/permission list, treat the permission state as already satisfied and report completion from that visible evidence instead of adding a duplicate.",
                "- Do not copy a hidden link or paste a link into IM as a substitute for the document share workflow unless the screenshot explicitly shows that link-sharing is the selected visible workflow.",
            ]
        )
        if _docs_share_inspect_task(text):
            lines.append(
                "- This task asks to inspect sharing state; opening the permission/share dialog is enough, and you must not send a new invitation."
            )
    if _docs_link_task(text):
        lines.extend(
            [
                "- For link tasks, if the requested target text is already visibly styled as a link, such as blue, underlined, or selected blue link text, return finished immediately.",
                "- Do not reopen the link dialog repeatedly after the target text visibly has link styling unless the task explicitly asks to inspect or change the URL.",
                "- Standard link path: select only the requested target text, use command k or the visible link icon once, type the exact requested URL into the link input, then confirm with Enter or the visible apply/confirm button.",
                "- When the link URL has just been typed into a visible link input field, the next action should confirm it with Enter or the visible confirm/apply button. Do not reselect the text before confirming.",
                "- Do not click a link confirm/apply button before entering the requested URL unless the input field already visibly contains that URL.",
                "- If a link popover is open on the requested target and shows the requested domain or URL, return finished; do not enter edit mode again.",
            ]
        )
    if _docs_bold_format_task(text):
        lines.extend(
            [
                "- Docs bold is a toggle, not a guaranteed set operation. First judge whether the exact requested target text is already bold from persistent document styling.",
                "- If the exact requested target text already appears visibly bold or thicker than adjacent normal body text, return finished. Do not select it again and do not press command b or click the B button again.",
                "- If the exact requested target text is not obviously bold, do not guess from a selected or search-highlighted state. First clear any transient selection or find/search highlight, then re-evaluate the persistent styling.",
                "- Only after the target is clearly not already bold should you select exactly that text and apply bold with one method only: either command b once or the visible B toolbar button once.",
                "- Use at most one bold toggle total per exact target span in this case. After the first bold attempt, do not press command b or click the B button again on the same target; that may toggle bold back off.",
                "- Before returning finished after a new bold operation, clear transient selection or find/search highlighting with Esc or a click in nearby blank body space, then recheck the same text from persistent document styling. If the floating toolbar or blue selection is still visible, keep clearing once more before finishing; do not treat a visible selection as a valid final state.",
                "- Never use a second bold toggle later in the same case to make sure the text is bold; bold changes are toggle actions and a second press can remove the formatting.",
                "- If the B toolbar button is visibly active while the exact target text is selected, the next action should clear the selection or finish after the persistent style is visible, not toggle B again.",
            ]
        )
    if _docs_partial_format_task(text):
        lines.extend(
            [
                "- For partial phrase formatting tasks, format only the requested phrase, not the whole sentence or the case-id anchor.",
                "- Include punctuation if it belongs to the requested phrase; do not leave a Chinese colon, quote mark, hyphen, digit, or suffix outside the formatted span.",
                "- If neighboring text becomes bold/highlighted by mistake, do not reselect the whole phrase or toggle the requested phrase again. Select only the wrongly formatted neighboring text and remove that same style once, then clear the selection and recheck.",
                "- When repairing partial-format spillover, preserve the requested phrase style. The repair target is the extra formatted neighbor, not the already-correct phrase.",
                "- After applying bold/highlight to the requested phrase, close any find/search panel with Esc or its visible close button before returning finished, so search-result highlighting is not confused with document formatting.",
                "- If the anchor text is only tinted because it is the active find result while the find panel is open, do not treat that tint as intentional formatting; clear the find/search state before final verification.",
                "- Return finished only after the requested phrase visibly has the requested style, surrounding words in the same sentence remain ordinary, and the surrounding anchor text is not selected or highlighted by an open find panel.",
            ]
        )
    if _docs_task_list_task(text):
        lines.extend(
            [
                "- For task-list/checklist tasks, create real checkbox/task items via a visible checklist control, slash-command task list, or editor markdown that renders into checkboxes.",
                "- For task-list/checklist tasks, do not choose divider/separator/分割线 menu items, and do not accept a rendered horizontal line as progress. A divider is wrong output for a checklist task.",
                "- Prefer visible options named 待办, 任务, 任务列表, checklist, or checkbox. If the visible menu row says 分割线/divider/separator, skip it and keep looking for the checklist/task-list option or use another visible checklist control.",
                "- If markdown text like '[ ] item' or numbered plain text remains visible, it is not a completed task-list state; use the visible block-type/list control to convert the lines to checklist/task-list items.",
                "- A line that visibly begins with the literal characters '[ ] DOCS-FEATURE-TASKLIST-OPEN' is still plain text, not an unchecked task item; do not return finished from that state.",
                "- If a divider appears where checklist items should be, treat it as a wrong structure and repair before finishing by creating the two requested checklist items after the divider or undoing the divider if safe.",
                "- Keep the requested open item unchecked. Mark only the requested done item checked, preferably by clicking its own checkbox after both items are visible.",
                "- When both task items are visible and the done item has a checked/completed visual style while the open item remains unchecked, return finished.",
            ]
        )
    if _docs_move_task(text):
        lines.extend(
            [
                "- For paragraph move/reorder tasks, move the existing source paragraph; do not type a duplicate source paragraph as a shortcut.",
                "- Preferred path: select the whole source paragraph or use its block handle, cut or drag it, then insert it immediately before the target paragraph.",
                "- If document find/search visibly reports 0 matches for the source paragraph, do not keep scrolling for the missing source. Treat the shared test document as dirty: close find, focus immediately before the target paragraph, insert the exact source paragraph once, and then verify no other source copy is visible.",
                "- After moving, verify from the visible document order: source should appear before target, and the old source position should not still contain a second copy.",
                "- If source is already directly before the target paragraph, return finished immediately.",
            ]
        )
    if _docs_nested_list_task(text):
        lines.extend(
            [
                "- For nested-list tasks, if the requested parent item and child item are both visible and the child is indented more than the parent, return finished immediately.",
                "- Do not retype the child item after it is already visible under the parent; repeated child text fails idempotence.",
                "- A markdown-style bullet parent plus visibly indented child is acceptable evidence of a nested list in Docs; do not keep trying to cosmetically refine it after the hierarchy is visible.",
            ]
        )
    if _docs_local_md_snippet_task(text):
        lines.extend(
            [
                "- For local Markdown snippet paste tasks, paste/type the requested bounded snippet once after the requested anchor.",
                "- If the snippet heading and all requested bullet lines are already visible after the anchor in the current screenshot, return finished immediately; do not paste the same snippet again.",
                "- For agenda snippets, do not finish when only the heading or first bullet is visible. Scroll slightly down until both requested agenda bullets, such as '同步目标' and '确认风险', are visible together.",
                "- Feishu Docs may paste Markdown as raw text instead of rendering it. After pasting, inspect the result before finishing.",
                "- If a heading remains as raw Markdown such as '# Title' or '### Title', repair it by deleting only the leading marker and following space, preserving the title text, then use a visible paragraph-style, block-type, or slash menu control to convert that line to the requested heading style.",
                "- If list items remain as raw Markdown such as '- 同步目标', repair them by removing only the literal '- ' prefixes or selecting the lines, then use a visible bullet-list/list control to convert them into real list items.",
                "- If a Markdown pipe table remains as literal text, do not try to fix it by deleting pipe characters. Insert a real Docs table/grid or table-like block near the target anchor and fill the cells with the Markdown table's header and row values.",
                "- After repairing a raw Markdown paste, make sure no raw Markdown markers, START/END markers, full-material roots, or duplicate wrong versions remain near the target anchor.",
                "- Do not keep re-entering edit mode or re-clicking the anchor after the snippet content is visible.",
            ]
        )
    return lines


def _docs_browser_execution_host_protocol(text: str) -> list[str]:
    if _docs_create_task(text) or not _docs_content_changing_task(text):
        return []
    return [
        "- Browser execution host protocol: for Docs content-changing tasks with an explicit target document title, the preferred editing host is the browser Docs page, not the Feishu desktop embedded editor.",
        "- If the exact target document is already open in a browser Docs host, continue there. If the screenshot is the Feishu desktop embedded Docs editor, do not start editing directly there; use Feishu app -> 云文档/Docs, search the exact full title, open the matching result, and wait for browser handoff before editing.",
        "- If the task does not state a target document title, do not invent one. Use the current live browser Docs page when it is visible; otherwise recover to a live Docs host before acting.",
        "- If the target document is visible only in the Feishu desktop embedded editor, that is proof of identity but not the preferred editing host. Move/open that same document into browser Docs before body editing, formatting, linking, comments, tables, dividers, material paste, or final completion.",
    ]


def _batch_protocol(case: TestCase) -> list[str]:
    allowed = {_normalize_allowed_action(item) for item in case.allowed_actions}
    if allowed and "batch" not in allowed:
        return []
    product = (case.product or "").lower()
    lines = [
        "",
        "Batch action protocol:",
        "- You may use Action: batch() only when every sub-action is already safe from the current screenshot and does not depend on a newly opened menu, picker, dialog, or changed document state.",
        "- Every batch sub-action must also be present in this case's allowed-action list; if a needed sub-action is absent, choose a permitted single action or a different visible route.",
        "- Use an Actions: JSON array after Action: batch(). Each item must include action/kind plus the same fields a normal action would need, such as point, content, key, target, evidence, or direction.",
        "- Do not include finished inside a batch. After executing a batch, wait for the next screenshot before deciding whether the goal is complete.",
        "- If any sub-action requires fresh visual confirmation, choose only the first action instead of batching.",
    ]
    if product == "docs":
        lines.extend(
            [
                "- Docs batch trial: prefer batching stable focus/type/hotkey sequences, for example click known body insertion point then type provided text, or focus document find then type query then press enter.",
                "- Do not batch across Docs structure menus, share dialogs, link popovers, comment panes, permission panels, or newly appearing slash-command results.",
                "- Do not batch multiple destructive edits such as cut/delete/reorder unless the selected text and insertion target are both visible and unambiguous in the current screenshot.",
            ]
        )
    return lines


def _normalize_allowed_action(value: str) -> str:
    aliases = {
        "type": "type_text",
        "type_text": "type_text",
        "left_double": "double_click",
        "double_click": "double_click",
        "right_single": "right_click",
        "right_click": "right_click",
    }
    return aliases.get((value or "").strip().lower(), (value or "").strip().lower())


def _mentions_required(case: TestCase) -> bool:
    text = " ".join(
        [
            case.instruction,
            case.name,
            case.product,
        ]
    ).lower()
    return "@" in text or "提及" in text or "mention" in text


def _input_material_lines(case: TestCase) -> list[str]:
    if not case.input_materials:
        return []
    include_content = _needs_full_input_material_content(case)
    if not include_content:
        return []
    lines = [
        "User-provided local input material:",
        "- Use this material only as content to paste/type after the correct visible input or editor area is focused.",
        "- Do not treat the material path as proof that the GUI task is complete.",
        "- For long provided material, do not repeat the full content in Action. Use the exact material reference token shown below, for example Action: type_text(content='{material:label}').",
    ]
    for material in case.input_materials:
        label = material.get("label") or "material"
        path = material.get("path") or ""
        content = material.get("content") or ""
        lines.extend([f"Material: {label}", f"Reference token: {{material:{label}}}", f"Path: {path}"])
        lines.extend(["Content:", "```markdown", content, "```"])
    return lines


def _needs_full_input_material_content(case: TestCase) -> bool:
    text = " ".join([case.id, case.name, case.instruction, case.stage]).lower()
    return any(
        term in text
        for term in [
            "docs-md-",
            "docs-feat-prep",
            "markdown",
            "本地",
            "material",
            "snippet",
            "片段",
            "议程",
            "小表格",
            "local-md",
            "local-table",
            "导入",
            "复制“docs-feature-local",
            "copy local",
        ]
    )


def _docs_create_task(text: str) -> bool:
    return any(term in text for term in ["创建", "新建", "create", "new document", "标题", "title"])


def _docs_entry_open_task(text: str) -> bool:
    return any(
        term in text
        for term in [
            "打开",
            "切换",
            "继续使用",
            "保持在",
            "入口",
            "open",
            "entry",
            "current-document",
            "docs_entry",
        ]
    ) and any(term in text for term in ["文档", "document", "docs"])


def _docs_edit_task(text: str) -> bool:
    return any(term in text for term in ["正文", "编辑", "输入", "追加", "body", "edit", "append", "content"])


def _docs_content_changing_task(text: str) -> bool:
    return any(
        term in text
        for term in [
            "正文",
            "编辑",
            "输入",
            "追加",
            "插入",
            "删除",
            "替换",
            "移动",
            "复制",
            "粘贴",
            "加粗",
            "高亮",
            "格式",
            "链接",
            "评论",
            "表格",
            "清单",
            "分割线",
            "标题",
            "列表",
            "代码",
            "引用",
            "body",
            "edit",
            "append",
            "insert",
            "delete",
            "replace",
            "move",
            "copy",
            "paste",
            "bold",
            "highlight",
            "format",
            "link",
            "comment",
            "table",
            "checklist",
            "divider",
            "heading",
            "list",
            "code",
            "quote",
        ]
    )


def _docs_structure_task(text: str) -> bool:
    return any(
        term in text
        for term in ["一级标题", "二级标题", "三级标题", "插入标题", "列表", "项目符号", "编号", "heading", "list", "bullet", "numbered"]
    ) or any(term in text for term in ["分割线", "divider"])


def _docs_marker_cleanup_task(text: str) -> bool:
    return any(term in text for term in ["markdown 标记", "markdown marker", "marker-cleanup", "# 标记"]) and any(
        term in text for term in ["标题", "heading", "docs-maint-002"]
    )


def _docs_heading_toc_task(text: str) -> bool:
    return any(term in text for term in ["目录", "大纲", "toc", "outline"]) and any(
        term in text for term in ["标题", "heading"]
    )


def _docs_undo_redo_task(text: str) -> bool:
    return any(term in text for term in ["撤销", "重做", "undo", "redo"])


def _docs_table_task(text: str) -> bool:
    return any(term in text for term in ["表格", "table"])


def _is_docs_structure_insertion_point_text(text: str) -> bool:
    return _contains_any(
        text,
        [
            "trailing end",
            "line end",
            "end of",
            "insertion point",
            "anchor line",
            "after the anchor",
            "cursor",
            "caret",
            "行尾",
            "末尾",
            "插入点",
            "锚点",
            "光标",
            "之后",
        ],
    )


def _docs_link_task(text: str) -> bool:
    return any(term in text for term in ["链接", "link", "url", "http://", "https://"])


def _docs_exact_span_task(text: str) -> bool:
    return any(
        term in text
        for term in [
            "指定文本",
            "局部文本",
            "局部短语",
            "短句",
            "词语",
            "phrase",
            "target text",
            "partial",
            "span",
            "删除",
            "替换",
            "加粗",
            "链接",
            "格式",
            "copy",
            "paste",
            "delete",
            "replace",
            "bold",
            "link",
            "format",
        ]
    ) and any(term in text for term in ["docs", "docs-", "文档"])


def _docs_partial_format_task(text: str) -> bool:
    return any(term in text for term in ["局部", "短语", "partial phrase", "partial"]) and any(
        term in text for term in ["格式", "加粗", "高亮", "format", "bold", "highlight"]
    )


def _docs_bold_format_task(text: str) -> bool:
    return any(term in text for term in ["加粗", "bold"]) and any(term in text for term in ["docs", "docs-", "文档"])


def _docs_task_list_task(text: str) -> bool:
    return any(term in text for term in ["任务列表", "待办", "清单", "checkbox", "checklist", "task list"])


def _docs_nested_list_task(text: str) -> bool:
    return any(term in text for term in ["嵌套列表", "nested list"]) or (
        "nested" in text and "list" in text
    )


def _docs_local_md_snippet_task(text: str) -> bool:
    return any(term in text for term in ["本地 markdown", "local markdown"]) and any(
        term in text for term in ["片段", "snippet", "议程", "agenda"]
    )


def _docs_move_task(text: str) -> bool:
    return any(term in text for term in ["移动", "重排", "move", "reorder"]) and any(
        term in text for term in ["段落", "paragraph"]
    )


def _contains_any(value: str, needles: list[str]) -> bool:
    lowered = (value or "").lower()
    return any(needle.lower() in lowered for needle in needles)


def _docs_share_task(text: str) -> bool:
    return any(term in text for term in ["分享", "权限", "协作者", "share", "permission", "collaborator"])


def _docs_share_inspect_task(text: str) -> bool:
    return any(term in text for term in ["查看", "检查", "inspect", "check"])


def _docs_verify_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() != "docs":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    lines = [
        "Docs verification protocol:",
        "- Verify only from visible screenshot evidence; do not infer success from the action history.",
        "- Check for negative evidence before returning PASS: visible wrong-version residue, stray slash-command text such as `/` or `/表格`, leaked START/END markers, accidental full-material paste, raw Markdown that should have rendered, or punctuation/colon/quote damage should make the result FAIL unless the task explicitly asks for that raw text.",
        "- The requested result must be at the requested target area, for example immediately after the named anchor. Do not count the same words if they only appear in the original material/source region, an outline/sidebar, search box, comment preview, or an earlier wrong attempt elsewhere on the page.",
        "- If both a wrong version and a correct version are visible, FAIL unless the instruction explicitly allows multiple versions; residual wrong content is document pollution.",
    ]
    if _docs_edit_task(text):
        lines.extend(
            [
                "- For body-editing tasks, PASS only if the requested text is visible in the document body below the title and author/modified metadata.",
                "- FAIL if the requested body text is appended to, merged into, or primarily displayed in the document title/top title area.",
                "- FAIL if the document title is visibly polluted by the current body-editing case id or body text, even if the same text also appears in the body.",
            ]
        )
    if _docs_structure_task(text):
        lines.extend(
            [
                "- For structure tasks, PASS only if the requested heading/list appears in the body content area, not as part of the document title.",
                "- For divider tasks, PASS only if a rendered horizontal divider is visible between the requested paragraphs; plain text `/分割线` is not enough.",
                "- For divider tasks between two existing anchors, PASS only if there is exactly one rendered divider between those anchors and no obvious extra blank editable paragraph or blue selected empty block below the divider.",
                "- For table tasks, PASS only if a rendered table grid/table block or clearly structured table UI is visible at the requested location; literal Markdown pipe text such as `| 阶段 | 动作 | 验收 |` is not a rendered table.",
                "- For table tasks with headers and data rows, FAIL if headers and data values are merely stacked as multiple text lines inside the same table cells. A visible horizontal row boundary must separate the header row from the data row.",
                "- Specifically FAIL the bad pattern where `事项` is directly above `素材复核`, `负责人` is directly above `测试扩展`, and `状态` is directly above `完成` inside the same three cells with no horizontal grid line between them; an empty row below those cells does not count as the filled data row.",
                "- Visual geometry verification: in a correctly formed 2-row table, each cell in the header row should be SHORT (single line height) and each cell in the data row should also be SHORT (single line height). If you see TALL cells (double the normal height) with two lines of text vertically stacked inside each cell, that is the stacking defect — FAIL immediately regardless of whether the correct text values are present.",
                "- Key visual cue: count the visible horizontal grid lines that pass through the FULL width of the table between text-containing rows. A valid header+data table needs at least one such full-width line separating the header text from the data text. If no such separator exists between '事项' and '素材复核', FAIL.",
                "- FAIL if literal slash-command text like `/`, `//`, `/表格`, `/table`, `/分割线`, or `/divider` remains visible in the document body after the operation.",
                "- For heading tasks, PASS only if the requested text is visible in a heading-sized, heading-bold, heading-labeled, or outline-recognized line.",
                "- For heading tasks, FAIL if the requested heading text has the same size/weight/paragraph style as nearby ordinary body text and is merely an independent plain line, even when the following list is correctly bulleted.",
                "- Do not fail solely because a markdown marker is still visible unless the marker clearly proves it is plain unformatted text.",
            ]
        )
    if _docs_marker_cleanup_task(text):
        lines.extend(
            [
                "- For marker-cleanup tasks, PASS if the target heading text is visible in the document body with heading-sized or heading-labeled styling and there is no visible leading '#' or '# ' immediately before that target heading.",
                "- Do not require edit mode or a visible text cursor for marker-cleanup verification; rendered view mode is acceptable if the final visible state satisfies the assertion.",
                "- FAIL only if a visible leading '#' remains directly before the target heading, the target heading text is damaged, or the heading style is visibly lost.",
            ]
        )
    if _docs_link_task(text):
        lines.extend(
            [
                "- For link tasks, PASS if the requested target text is visibly formatted as a link, for example blue, selected blue, or underlined link text.",
                "- A visible URL popup is useful but not required when the assertion accepts link styling.",
                "- FAIL if the visible link styling appears to cover the wrong span, omits requested punctuation/suffix characters, or spills onto neighboring words that were not requested.",
            ]
        )
    if _docs_exact_span_task(text):
        lines.extend(
            [
                "- For exact-span local text operations, inspect the visible final document state carefully around the requested target.",
                "- PASS only if every requested character in the local target span is preserved or modified as requested, including punctuation, quotes, hyphens, digits, colons, and suffix IDs.",
                "- FAIL if the operation visibly missed punctuation or suffix characters, modified only part of the requested span, or also modified neighboring text that was not requested.",
                "- Do not count active find/search highlighting, blue text selection, or a floating toolbar as proof of persistent formatting.",
            ]
        )
    if _docs_partial_format_task(text):
        lines.extend(
            [
                "- For partial phrase formatting tasks, PASS if only the requested phrase has bold/highlight styling while the rest of the sentence remains ordinary text.",
                "- Do not count transient find/search result tinting or text selection as document formatting.",
                "- If the final screenshot still shows the target phrase selected, be conservative: PASS only if the persistent font weight/color/background can be distinguished from the selection highlight; otherwise FAIL and require the selection to be cleared first.",
                "- If a find/search panel is still open and the anchor is tinted only as the active search result, judge the actual document style rather than the search highlight.",
            ]
        )
    if _docs_task_list_task(text):
        lines.extend(
            [
                "- For task-list tasks, PASS only if the requested open item and done item are both visible as checklist/task items.",
                "- The open item should appear unchecked, while the done item should appear checked, struck through, or otherwise completed.",
                "- FAIL if the items remain only as plain markdown markers like '[ ]' or ordinary numbered text without checkbox/task-list styling.",
            ]
        )
    if _docs_nested_list_task(text):
        lines.extend(
            [
                "- For nested-list tasks, PASS if the parent item and child item are both visible and the child item is visibly indented under the parent.",
                "- A markdown bullet marker is acceptable if the visual hierarchy is clear.",
            ]
        )
    if _docs_local_md_snippet_task(text):
        lines.extend(
            [
                "- For local Markdown snippet tasks, PASS only if the requested bounded snippet content is visible after the anchor, including the snippet heading and all expected bullet lines.",
                "- For agenda snippets, FAIL if only the heading or only one agenda bullet is visible and the other required bullet is below the fold or absent.",
                "- FAIL if the visible result after the anchor includes the snippet START/END marker lines, a full material root marker, or other source-boundary text unless the instruction explicitly asks to paste those markers.",
                "- FAIL if the content after the target anchor is raw Markdown when the task expects a human-clean Docs paste, for example visible `###` heading markers, plain `- ` bullet markers that did not render as list bullets, or a stray punctuation-only line introduced by the paste.",
                "- Do not count the original bounded snippet in the source material section as success; the copied snippet must be visible at the requested paste anchor.",
            ]
        )
    if _docs_move_task(text):
        lines.extend(
            [
                "- For paragraph move tasks, PASS only if the source paragraph is visibly before the target paragraph and no second source copy remains visible at the old location.",
                "- FAIL if the source was duplicated instead of moved.",
            ]
        )
    if _docs_share_task(text):
        lines.extend(
            [
                "- For share tasks, PASS if the screenshot shows the requested recipient in the collaborator/permission UI, or a visible success toast confirming invitation/share/permission modification.",
                "- Treat Chinese success messages such as 邀请成员成功, 已分享, 修改成员权限成功, or 已获得权限 as valid success evidence for a document share workflow.",
                "- Do not require the recipient name to remain visible if a transient success toast clearly confirms the share or permission update just completed.",
            ]
        )
    return lines


def _message_operation_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() == "docs":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    lines: list[str] = []
    if "回复" in text or "reply" in text:
        lines.extend(
            [
                "",
                "Reply operation protocol:",
                "- This task requires a real reply/reference relationship, not an ordinary new text message.",
                "- First identify the concrete live chat bubble to reply to, then use its visible context menu or hover toolbar reply control.",
                "- Do not type or send the reply text until the composer visibly shows a reply quote/reference block or reply mode for that target message.",
                "- If no reply quote/reference block is visible after an attempted menu action, recover by targeting the message bubble again; do not fall back to plain sending.",
            ]
        )
    if "标记" in text or "mark" in text:
        lines.extend(
            [
                "",
                "Message mark protocol:",
                "- Marking a message or conversation requires operating the target item menu/state; do not send explanatory text as a substitute.",
                "- For message marking, target the real live chat bubble and use its context menu or visible message toolbar.",
            ]
        )
    if "表情回复" in text or "反应" in text or "reaction" in text:
        lines.extend(
            [
                "",
                "Message reaction protocol:",
                "- Emoji reactions must be added to a real live chat bubble; do not send an emoji as a normal message unless the task explicitly asks to send an emoji message.",
                "- Use the target message hover toolbar or context menu before selecting the emoji reaction.",
            ]
        )
    return lines


def _attachment_share_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() == "docs":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not _is_attachment_or_share_task(text):
        return []

    lines = [
        "",
        "Attachment and share protocol:",
        "- The final user goal is to send/share a real attachment, cloud document, card, or rich object; do not send a file path, document title, contact name, or explanation as a plain text message.",
        "- When a cloud-document list row is visible, prefer the row's more/menu control and then its visible share/send option.",
        "- When a share/send popup is visible, search/select the intended recipient inside that popup, then use the popup's visible send/share button.",
        "- When a local file picker is visible, select the requested file object and confirm with the picker Open/Choose button, then send from the Feishu confirmation popup if it appears.",
    ]
    if "搜索" in text or "search" in text:
        lines.extend(
            [
                "- In Feishu search results, a cloud-document result row can expose a right-side inline chain/link/share/send icon. If this icon is visible for the first result, prefer clicking that row-level icon to share/insert the result into the current chat.",
                "- After clicking an inline link/share/send icon, continue only from visible evidence: a share popup, a document card/attachment preview in the composer, or a visible send button for that object.",
                "- Do not assume the document link was copied to the clipboard, and do not use command v to paste an invisible share link unless the screenshot visibly shows a copy/link workflow that asks for paste.",
                "- For search-result popups, clicking a result may only select it. If the same result popup remains after one click and the UI hints that Enter opens the result, use hotkey enter instead of repeatedly clicking the same result.",
                "- Do not invent a more/three-dot button on a search result row. Use only controls that are visibly present, such as the right-side chain/link/share/send icon, visible share button, or Enter-open hint.",
                "- If a cloud-document search popup has no visible row-level share/link/send icon, use the first result only to identify the target title, then close the popup and locate that same document row in the visible cloud-document list behind it.",
                "- To close a Feishu search popup, prefer hotkey esc. The X inside the search input may only clear the query text and leave the popup open.",
                "- After closing a cloud-document search popup, do not reopen the same search just to select the same result again. Continue from the underlying document list row and its visible more/share controls.",
                "- If you have already clicked or pressed Enter on the same search result and the same search popup is still visible, do not click, press Enter, or wait on that same result again. The next action should be hotkey esc to close the search popup.",
                "- After a search result opens or returns to a document/detail/list state, continue toward the visible share/send control for that selected object.",
            ]
        )
    if "个人名片" in text or "名片" in text or "card" in text:
        lines.extend(
            [
                "- For personal card tasks, open the composer plus/more sending options, choose the visible personal-card/contact-card option, select the first visible card/contact in that picker, then send it as a card.",
            ]
        )
    return lines


def _is_attachment_or_share_task(text: str) -> bool:
    return any(
        term in text
        for term in [
            "附件",
            "图片",
            "文件",
            "云文档",
            "文档",
            "分享",
            "名片",
            "attachment",
            "file",
            "image",
            "document",
            "share",
            "card",
        ]
    )


def _rich_text_protocol(case: TestCase) -> list[str]:
    if (case.product or "").lower() == "docs":
        return []
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    if not any(term in text for term in ["加粗", "bold", "富文本", "格式"]):
        return []
    return [
        "",
        "Rich text protocol:",
        "- For a bold text message, prefer enabling the visible bold B control in the composer before typing the message, then type the message once and send it.",
        "- Avoid using command a for bold formatting unless the screenshot clearly shows the target composer text is selected; command a may select the wrong scope or have no visible effect.",
        "- After pressing send/enter, if the target message text is visible as the latest outgoing chat bubble, the send goal is complete; return finished instead of clicking the composer and typing the same text again.",
        "- If the target message is already visible but the composer still contains a duplicate unsent draft, clear that duplicate draft before finishing; do not send it again.",
    ]


def _is_send_or_compose_task(case: TestCase) -> bool:
    text = " ".join([case.instruction, case.name, case.stage]).lower()
    return any(
        term in text
        for term in [
            "发送",
            "发给",
            "回复",
            "分享",
            "send",
            "reply",
            "share",
            "upload",
            "提及",
            "@",
        ]
    )


def _allowed_actions_line(case: TestCase) -> str:
    if not case.allowed_actions:
        return "Use only the actions listed in the scenario system prompt."
    return ", ".join(case.allowed_actions)
