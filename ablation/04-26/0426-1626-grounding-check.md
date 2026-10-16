# Grounding Check 预执行视觉校正 Ablation

## 目标

验证 `--grounding-check` 是否能提升密集 UI 区域内点击坐标的可靠性，尤其是飞书输入框工具栏、表情按钮、@ 按钮、mention picker 等小图标/小目标场景。

## Baseline

```bash
conda run -n feishu python scripts/run_test.py \
  --round 0426-1601-baseline-before-visual-grounding \
  --stage im_basic_send \
  --max-steps 12 \
  --final-verify
```

报告：

```text
results/0426-1601-baseline-before-visual-grounding-20260426-160108/README.md
```

baseline 摘要：

- 6/6 passed
- 38 steps
- 843.91s
- `IM-P2-006`: 12 steps, 331.88s

## 优化变量

唯一新增变量：

```bash
--grounding-check
```

含义：对坐标点击类动作，在真实执行前生成标注截图并让 VLM 判断/修正候选点击点。

## 实现状态

已实现：

- 新增 `cua_lark/testing/grounding_check.py`
- 新增 CLI 参数 `--grounding-check`
- 报告新增：
  - `NN-grounding-check.png`
  - `Action.grounding_check`
  - `steps.md` 中的 Grounding check 字段
- 单测：`tests/test_grounding_check.py`

## Dry-run 验证

```bash
python scripts/run_test.py \
  --static-screen results/smoke-20260426-150321/cases/IM-P2-001__发送普通文本给测试联系人/final.png \
  --dry-run-response "..." \
  --case IM-P2-001 \
  --round 0426-1626-grounding-check-dryrun \
  --max-steps 1 \
  --grounding-check
```

报告：

```text
results/0426-1626-grounding-check-dryrun-20260426-162622/README.md
```

说明：该 dry-run 预期失败于 `max steps reached: 1`，但已验证 `01-grounding-check.png` 和报告字段能够生成。

## 真实对比

运行重点 case：

```bash
conda run -n feishu python scripts/run_test.py \
  --round 0426-1627-grounding-check-im-p2-006 \
  --case IM-P2-006 \
  --max-steps 12 \
  --final-verify \
  --grounding-check
```

报告：

```text
results/0426-1627-grounding-check-im-p2-006-20260426-162715/README.md
```

结果：

| 指标 | Baseline IM-P2-006 | `--grounding-check` |
| --- | ---: | ---: |
| 状态 | passed | passed |
| 步数 | 12 | 12 |
| 耗时 | 331.88s | 339.83s |
| grounding-check 图 | 0 | 5 |
| corrected point | 0 | 1 |
| 过程质量 warning | 未回填 | multiple_enter_sends:3; plain_at_text_inputs:3; grounding_corrected:1 |

关键校正：

- Step 8：目标是 `@ button in the chat input toolbar with 测试联系人`。
- 初始红色十字落在 plus button 上。
- grounding-check 返回 `CORRECTED`，将点击点修正到 `<point>860 944</point>`。
- 后续 Step 9 成功点击 `测试联系人 option in @ mention pop-up`。

## 结论

本次优化没有降低步数和耗时，耗时略增 7.95s，因为增加了预执行 VLM 校正调用。

但它捕获并修正了一次真实的密集工具栏坐标错误：模型原始点落在 plus button，而校正后点击 @ button。这说明优化对“避免误点相邻小图标”是有必要的。

保留建议：

- 不作为所有点击的默认开启项。
- 作为高风险点击的可选机制，优先用于 composer toolbar、emoji panel、mention picker、右键菜单、hover 工具条。
- 下一步应结合区域裁剪/放大，减少校正调用成本并提高一次定位质量。

## 0426-1648 追补

根据本次结论，`--grounding-check` 已从“全量点击校正”调整为默认高风险触发：

- 默认模式：`--grounding-check --grounding-check-mode high-risk`
- 复现实验全量模式：`--grounding-check --grounding-check-mode all`
- 未触发校正的点击会记录 `triggered: false` 和原因，不生成校验图、不额外调用 VLM。

新增过程质量诊断后，历史 IM-P2-006 报告被回填为 warning：虽然最终 PASS，但过程包含 3 次 enter 发送、3 次 plain `@` 文本输入，以及 1 次 grounding 坐标修正。这说明下一轮优化不仅要看最终通过率，也要看副作用路径是否减少。

Dry-run 验证：

```bash
python scripts/run_test.py \
  --round 0426-1648-high-risk-grounding-dryrun \
  --case IM-P2-001 \
  --max-steps 1 \
  --grounding-check \
  --static-screen results/0426-1627-grounding-check-im-p2-006-20260426-162715/cases/IM-P2-006__测试联系人并发送消息/01-before.png \
  --dry-run-response "<普通输入框点击响应>"
```

报告路径：

```text
results/0426-1648-high-risk-grounding-dryrun-20260426-164656/README.md
```

该 dry-run 预期失败于 `max steps reached: 1`，但验证了普通输入框点击在 high-risk 模式下记录 `triggered: false, reason: not_high_risk`，且不生成 `NN-grounding-check.png`。
