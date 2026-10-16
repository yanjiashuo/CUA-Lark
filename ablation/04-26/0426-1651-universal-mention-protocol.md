# 通用 Mention Token 协议

## 目标

验证把 @ 提及路径写入通用执行 prompt 后，是否能减少 IM-P2-006 中的过程副作用：

- plain `@姓名 ...` 文本输入次数
- 多次 enter 发送次数
- 总步数
- 最终是否仍 PASS

## Baseline

历史结果：

```text
results/0426-1627-grounding-check-im-p2-006-20260426-162715/README.md
```

回填后的过程质量：

```text
multiple_enter_sends:3
plain_at_text_inputs:3
grounding_corrected:1
```

## 改动变量

唯一目标变量：当 case instruction/name/product 中包含 `@`、`提及` 或 `mention` 时，`build_step_prompt()` 自动加入通用 mention token 执行协议。scenario prompt 不重复展开该协议，只提醒模型遵守 user prompt 中的 task-specific operation protocol。

协议要求：

- 必须创建真实 @ mention token。
- 禁止直接输入 plain `@Name message`。
- 先通过可见 mention UI 创建 token，再追加剩余文本。
- token 和剩余文本都可见后才能发送。

## 当前验证

单测：

```bash
python -m pytest tests/test_prompt.py tests/test_process_quality.py tests/test_reporting.py
```

结果：4 passed。

Prompt 抽查：

```text
Task:
去和测试联系人的聊天里 @测试联系人，并发送消息“CUA-Lark Phase2 @提及 006”

Task-specific operation protocol:
- This task requires a real @ mention token.
- Do not type a plain '@Name message' as normal text.
- First create the mention token through the visible mention UI: type only '@' or click the visible @ button, then select the target person from the mention picker.
- After the mention token is inserted, append only the remaining message text without clearing or overwriting the token.
- Send the message only after the real mention token and remaining text are both visible in the input area.
```

确认：执行 prompt 未包含 YAML `expected`。

## 待跑真实对比

建议下一次真实 GUI 对比命令：

```bash
conda run -n feishu python scripts/run_test.py \
  --round 0426-1651-universal-mention-protocol-im-p2-006 \
  --case IM-P2-006 \
  --max-steps 12 \
  --final-verify \
  --grounding-check
```

重点观察：

- `plain_at_text_input_count` 是否从 3 降到 0。
- `enter_send_count` 是否从 3 降到 1。
- 是否仍需要 grounding correction。
- 总步数是否下降。

## 当前结论

先保留。该改动属于通用任务协议，不引入 case-specific fallback，也不改变执行器路径。真正效果需要下一轮真实 GUI ablation 确认。

## 0426-1653 真实 GUI 结果

命令：

```bash
conda run -n feishu python scripts/run_test.py \
  --round 0426-1653-universal-mention-protocol-im-p2-006 \
  --case IM-P2-006 \
  --max-steps 12 \
  --final-verify \
  --grounding-check
```

报告路径：

```text
results/0426-1653-universal-mention-protocol-im-p2-006-20260426-165349/README.md
```

结果：

| 指标 | 上一轮全量 grounding-check | 本轮通用 mention 协议 + high-risk grounding |
| --- | ---: | ---: |
| 状态 | passed | passed |
| 步数 | 12 | 8 |
| 耗时 | 339.83s | 184.89s |
| enter 发送次数 | 3 | 1 |
| plain `@姓名...` 输入次数 | 3 | 0 |
| grounding-check correction | 1 | 0 |

关键路径：

- Step 4：只输入 `@` 打开 mention picker。
- Step 5：点击 `测试联系人 mention option in the dropdown`，插入真实 mention token。
- Step 6：追加剩余文本 ` CUA-Lark Phase2 @提及 006`。
- Step 7：只发送一次。

结论：通用 mention 协议有效，显著减少副作用路径和步数。过程质量诊断已调整为只把以 `@姓名...` 开头的直接输入计为 plain mention 问题；单独输入 `@` 打开 picker 和消息正文里的 `@提及` 不计为问题。
