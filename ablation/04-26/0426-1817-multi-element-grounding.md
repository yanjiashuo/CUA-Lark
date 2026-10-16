# 0426-1817 多元素 Grounding P0

## 目标

推进纯视觉多元素 grounding：每一步 VLM 除了输出当前动作的 `Grounding` 外，还输出多个相关可见 UI 元素，用于诊断密集界面中的目标、邻近干扰控件和可复用区域。

## Baseline

此前每步只有单个 `Grounding`：

- 一个 target
- 一个 bbox
- 一个 point
- 一个 confidence
- 一个 grounding crop

这能支持单点执行和 bbox/point 自洽检查，但不能同时记录输入框、发送按钮、@ 按钮、表情按钮、picker option 等多个元素。

## 改动变量

新增观测型 `Elements:` 输出，不直接改变执行坐标：

```text
Elements: [{"name":"...","role":"action_target|nearby_confuser|reusable_context","bbox":[x1,y1,x2,y2],"point":[x,y],"confidence":0.00,"evidence":"..."}]
```

实现点：

- scenario prompt 要求输出 `Elements`。
- step prompt 要求 VLM 先 ground 多个相关元素，包含当前动作目标和附近易混控件。
- parser 解析 `Elements` 并转换 0-1000、image、screen 坐标。
- report 生成 `NN-elements.png` 多元素覆盖图。
- `steps.md` 展示元素摘要和 overlay。

## 命令

快速单测：

```bash
python -m pytest tests/test_action_parser.py tests/test_prompt.py tests/test_reporting.py tests/test_grounding_check.py tests/test_process_quality.py tests/test_screen.py
```

static dry-run：

```bash
python scripts/run_test.py \
  --round 0426-1808-multi-element-grounding-dryrun \
  --case IM-P2-006 \
  --static-screen results/0426-1707-bbox-parser-gate-im-p2-006-20260426-170729/cases/IM-P2-006__测试联系人并发送消息/01-before.png \
  --dry-run-response "<包含 Elements 的固定响应>"
```

## 结果路径

- dry-run 报告：`results/0426-1808-multi-element-grounding-dryrun-20260426-181701/README.md`
- case steps：`results/0426-1808-multi-element-grounding-dryrun-20260426-181701/cases/IM-P2-006__测试联系人并发送消息/steps.md`
- overlay：`results/0426-1808-multi-element-grounding-dryrun-20260426-181701/cases/IM-P2-006__测试联系人并发送消息/01-elements.png`

## 指标

- 单测：20 passed。
- dry-run：1/1 passed。
- 生成 `01-elements.png`：是。
- `steps.md` 展示 Elements 摘要：是。

## 真实 VLM/GUI 测试补充

### 0426-1822 首轮

报告：

```text
results/0426-1822-multi-element-grounding-real-im-p2-006-20260426-182235/README.md
```

结论：

- 失败很快发生，原因是测试前置状态不干净：飞书窗口在后方，截图像素被 VS Code 覆盖。
- VLM 能输出 `Elements`，但漏掉 `Action` 行。
- 该轮不能评价 Feishu 视觉定位质量，只能说明必须先保证目标窗口无遮挡，并且 `Action` 不能被诊断字段挤掉。

### 0426-1825 第二轮

报告：

```text
results/0426-1825-multi-element-grounding-real-im-p2-006-rerun-20260426-182443/README.md
```

结论：

- 飞书已置前，但模型输出在多行 `Elements` 第二个对象中间被截断。
- 原因是 `max_tokens=260` 偏小，且 `Elements` 放在 `Action` 前面，诊断字段把关键动作行挤掉。
- 修正：将输出协议改为 `Action` 优先，`Elements` 放在 `Action` 后作为可选紧凑单行；同时 VLM `max_tokens` 提升到 700。

### 0426-1827 第三轮

报告：

```text
results/0426-1827-multi-element-grounding-real-im-p2-006-action-first-20260426-182615/README.md
```

结果：

- 运行 10 步，失败原因：`max steps reached: 10`。
- 10/10 步成功解析 Action。
- 10/10 步生成 `NN-elements.png`。
- Grounding checks: 5。
- Grounding skipped: 1。
- Grounding corrections: 1。

关键发现：

- 多元素 grounding 格式在真实 VLM 下已经稳定，不再破坏 Action 解析。
- 失败不来自 `Elements`，而来自脏输入框状态下的 mention 流程恢复。
- Step 3 在已有 👍 草稿内容后输入 `@`，没有打开真实 mention picker。
- Step 4 grounding-check 发现原始 mention option 不成立，修正到 @ 工具栏按钮。
- 随后模型反复执行 `command a`、`backspace`、点击输入框，但没有重新开始创建 mention token，最终耗尽步数。

## 当前结论

P0 多元素 grounding 值得保留，但“测试通过”还不能成立。它已经证明：

- 真实 VLM 可以按紧凑 `Elements` 输出。
- report/overlay 对诊断有价值。
- Action-first 协议比 Elements-first 更安全。

它还没有证明：

- 多元素 grounding 能提升最终任务成功率。
- 多元素 grounding 已经被 grounding-check 或执行策略有效利用。
- mention token 流程能在脏输入框状态下稳定恢复。

## 结论

值得保留，但只能算 P0 观测能力通过，不算端到端优化通过。下一步应先修 mention 脏输入框恢复策略，再做 P1：把 `Elements` 接入 grounding-check prompt 或 action point 与 action_target bbox 的一致性校验。
