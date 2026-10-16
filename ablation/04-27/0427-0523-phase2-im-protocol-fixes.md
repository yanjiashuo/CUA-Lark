# 0427-0523 Phase2 IM 执行协议修复 Ablation

## 目标

验证本轮协议优化是否修复以下假通过/卡死风险：

- `cmd+v` 被拆成裸 `v`。
- 回复任务退化为普通文字发送。
- 云文档分享退化为剪贴板链接粘贴或搜索弹窗循环。
- 富文本发送后重复输入。

## Baseline

主要 baseline 来自修复前真实失败/中止结果：

- `results/0427-0205-iter2-im-message-ops-20260427-020000/README.md`
  - 全阶段运行过长后中止，仅完成部分 case。
- `results/0427-0242-iter5-attachment-rest-20260427-024056/README.md`
  - IM-P2-010 failed，max steps reached，反复点击搜索结果。
- `results/0427-0305-iter5-search-doc-inline-share-im-p2-010-20260427-030426/`
  - 搜索结果行内图标后尝试 `command v` 粘贴不可见链接，中止。
- `results/0427-0325-iter6-im-cross-view-20260427-032035/`
  - IM-P2-023 曾在发送后继续点击输入框/重复输入，中止后单独修复。

## 优化变量

- executor：组合键显式 keyDown/keyUp。
- prompt：回复协议、附件分享协议、云文档搜索弹窗状态机、富文本完成协议。
- process quality：回复缺少引用操作、云文档分享出现 `command v` 时阻塞通过。

## 优化后结果

- 单测：29 passed。
- `results/0427-0424-iter7-search-doc-esc-popup-im-p2-010-20260427-042013/README.md`
  - IM-P2-010 passed，路径为搜索弹窗确认目标 -> Esc -> 底层列表更多菜单 -> 分享弹窗 -> 发送。
- `results/0427-0437-iter8-im-message-ops-20260427-043128/README.md`
  - 6/6 passed，quality clean。
- `results/0427-0500-iter8-im-conversation-ops-20260427-045913/README.md`
  - 3/3 passed。
- `results/0427-0335-iter6-rich-text-im-p2-023-20260427-032703/README.md`
  - IM-P2-023 passed。

## 指标对比

| 项目 | 修复前 | 修复后 |
| --- | --- | --- |
| 回复任务 | 有普通发送假通过风险 | message_ops 6/6 clean，回复 case 有真实引用路径 |
| 云文档搜索分享 | IM-P2-010 max steps / 剪贴板粘贴风险 | IM-P2-010 passed，且 `command v` 作为 blocking warning |
| 热键 | `cmd+v` 疑似打散为裸 `v` | 单测覆盖显式 keyDown/keyUp 顺序 |
| 富文本 | 发送后重复输入风险 | IM-P2-023 passed |

## 结论

保留本轮优化。它们不是 case-specific 坐标补丁，而是执行协议和过程质量层的通用约束，能显著降低假通过和无意义循环。

## 后续观察

- 完整 25 case 单轮回归还需要单独跑一次。
- IM-P2-009、IM-P2-023 的 grounding correction warning 说明小按钮定位仍需优化。
