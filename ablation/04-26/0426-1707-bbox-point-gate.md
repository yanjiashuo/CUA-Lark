# BBox / Point 自洽 Gate

## 目标

减少无意义的 grounding-check VLM 调用，同时保留对小目标、密集 UI、低置信和定位不自洽点击的保护。

## 改动变量

`--grounding-check` 的默认 `high-risk` 模式新增本地几何 gate：

- 如果 `point` 不在 VLM 自己给出的 `bbox` 内，触发 VLM 校验。
- 如果 bbox 很小，触发 VLM 校验。
- 如果 confidence 低，触发 VLM 校验。
- 如果命中 @、mention、toolbar、emoji、plus、popup、picker、menu、option 等密集 UI 词，触发 VLM 校验。
- 如果 point 在 bbox 内、bbox 不小、confidence 高且没有密集 UI 词，跳过 VLM 校验并记录 `self_consistent_large_target`。

同时增强 `Grounding` parser：

- 支持 `<box>...</box>`
- 支持 `<bbox>...</bbox>`
- 兼容 `bbox='<point>x1 y1 x2 y2</point>'`

## 对比结果

| 指标 | 0426-1653 mention protocol | 0426-1703 bbox gate | 0426-1707 parser + gate |
| --- | ---: | ---: | ---: |
| 状态 | passed | passed | passed |
| 过程质量 | clean | clean | clean |
| 步数 | 8 | 8 | 6 |
| 耗时 | 184.89s | 185.78s | 115.87s |
| grounding checks | 4 | 3 | 3 |
| grounding skipped | 1 | 1 | 1 |
| grounding corrections | 0 | 0 | 0 |
| plain @ 输入 | 0 | 0 | 0 |

## 报告路径

```text
results/0426-1653-universal-mention-protocol-im-p2-006-20260426-165349/README.md
results/0426-1703-bbox-point-gate-im-p2-006-20260426-170318/README.md
results/0426-1707-bbox-parser-gate-im-p2-006-20260426-170729/README.md
```

## 关键观察

最终版 `0426-1707` 中：

- Step 1 输入框点击被本地 gate 跳过，原因是 `self_consistent_large_target`，bbox 大小 `[543, 40]`，point 在 bbox 内，confidence 1.0。
- Step 3 mention picker 选项触发校验，原因是 `matched_high_risk_terms`，这是期望行为。
- Step 5 蓝色发送按钮触发校验，原因是 `small_grounding_box`，bbox 大小 `[22, 21]`，这是期望行为。

## 结论

保留。该优化没有降低成功率和过程质量，减少了普通大目标的无意义校验，并让报告中的触发原因更可解释。真正的耗时下降还受 VLM 决策路径波动影响，但最终版已经达到 6 步、115.87s，是目前 IM-P2-006 上最干净的一轮。
