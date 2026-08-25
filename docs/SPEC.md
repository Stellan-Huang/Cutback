# Cutback V0

## 1. 产品定义

Cutback 是一个 **Review-to-Edit Agent**。

它将视频审核意见理解为结构化编辑决策，并在用户确认后转换为实际 Timeline 操作。

核心流程：

**Review → Interpret → Confirm → Plan → Execute → Preview**

---

## 2. 用户场景

用户已有一版视频，并收到一条或多条审核意见，例如：

> 00:10–00:20 这段删掉。  
> 00:30–00:40 这段放到开头。  
> 00:50–01:00 这里有点拖。  
> 01:10–01:20 这段挺好，保留。

Cutback 分别判断为：

- `DELETE_RANGE`
- `MOVE_RANGE`
- `CLARIFY`
- `NO_ACTION`

用户只批准需要执行的操作，Cutback 再统一生成修改后版本。

---

## 3. 核心假设

V0 只验证一个问题：

> **Review 能否被可靠地理解，并转化为用户愿意执行的视频编辑操作。**

不验证完整自动剪辑，也不构建完整 NLE。

---

## 4. Review 决策

Cutback 将每条 Review 判断为三种状态：

### ACTION

信息充分，且当前系统具备对应执行能力。

### CLARIFY

存在修改意图，但信息不足或操作不明确，需要用户补充。

### NO_ACTION

用户明确认可、保留或表示无需修改。

核心原则：

> **Location ≠ Intent ≠ Permission**

时间码只表示 Review 指向的位置，不代表修改授权。

只有明确且当前系统可执行的编辑指令才能产生 `ACTION`。

信息不足时优先 `CLARIFY`，不猜测用户意图。

---



## 5. EditAction

当前支持两种 Timeline 操作。

### DELETE_RANGE

删除指定时间区间。

```json
{
  "action": "DELETE_RANGE",
  "start_time": 10,
  "end_time": 20
}
```



### MOVE_RANGE

将指定时间区间移动到目标位置。

```json
{
  "action": "MOVE_RANGE",
  "start_time": 30,
  "end_time": 40,
  "destination_time": 0
}
```

`destination_time` 使用**原始视频 Timeline 坐标**。

基本约束：

- `start_time >= 0`
- `end_time > start_time`
- `MOVE_RANGE` 必须提供合法 `destination_time`
- 目标位置不能位于自身移动区间内部

LLM 负责理解 Review，Pydantic 负责约束结构化结果。

---



## 6. Multiple Reviews

Cutback 支持一次处理多条 Review。

每条 Review 独立解析为：

**ACTION / CLARIFY / NO_ACTION**

用户可以逐条：

- 接受 AI 建议；
- 修改操作参数后接受；
- 拒绝操作。

只有被批准的 `ACTION` 才进入最终 Timeline Planning。

所有 Review 时间码均基于**原始视频 Timeline**，避免前序修改导致后续时间坐标漂移。

---



## 7. Timeline Planning

多条已批准 EditAction 不按顺序直接修改视频，而是先统一转换为最终 Timeline。

例如：

```text
DELETE 10–20
MOVE 30–40 → 0
```

原始 Timeline：

```text
0–10 → 10–20 → 20–30 → 30–40 → 40–End
```

最终 Timeline：

```text
30–40 → 0–10 → 20–30 → 40–End
```

对于以下冲突，V0 不自动推断执行顺序：

- 多个操作源范围重叠；
- MOVE 目标落入其他待编辑范围；
- 多个 MOVE 使用冲突目标位置。

发生冲突时拒绝自动执行，由用户修改或取消相关操作。

---



## 8. 执行

最终 Timeline 经确认后，由确定性执行层完成实际视频修改：

**Approved Actions → Timeline Planner → Executor → FFmpeg → Output**

AI 不直接操作视频。

---



## 9. Human-in-the-loop

对于 `ACTION`：

- 直接执行 AI 建议 → **Accept**
- 修改参数后执行 → **Modify**
- 不批准 → **Reject**

对于 `CLARIFY`：

- 不执行；
- 请求用户补充信息。

对于 `NO_ACTION`：

- 不执行。

核心原则：

> **AI proposes, human controls.**

错误执行的成本高于多确认一次，因此 Cutback 优先避免未经授权的修改。

---



## 10. Evaluation

当前 Evaluation 覆盖：

- Review Status Accuracy
- EditAction Accuracy
- Holdout Validation
- Regression Test
- Response Latency
- Bad Case Analysis

已通过 Bad Case 分析迭代 Review Decision Policy，并使用未参与 Prompt 调整的 Holdout 验证泛化能力。

新增 EditAction 后继续运行原有 Evaluation Set，确保既有能力不发生回归。

下一阶段重点转向真实用户测试，记录：

- Accept
- Modify
- Reject
- 实际 Bad Case
- Review-to-Revision 完成时间
- 用户对 Agent 决策边界的反馈

---



## 11. 当前产品流程

```text
上传视频
↓
输入多条 Review
↓
逐条生成 ReviewResult
↓
ACTION / CLARIFY / NO_ACTION
↓
用户确认、修改或拒绝
↓
Approved EditActions
↓
Timeline Planning
↓
Conflict Validation
↓
FFmpeg 执行
↓
Original / Revised 对比
```

---



## 12. 非目标

V0 暂不实现：

- 完整 NLE
- Premiere / Resolve 插件
- Frame.io 集成
- 多轨编辑
- 多人协作
- AI 视频生成
- Model Routing
- Style Memory
- 无时间码语义定位
- 用户系统
- 云端部署

> **只有真实需求证明必要时，才引入新的复杂度。**

---



## 13. 成功标准

Cutback 能稳定完成：

**Multiple Reviews
→ 正确判断 ACTION / CLARIFY / NO_ACTION
→ 合法 DELETE_RANGE / MOVE_RANGE
→ Human Approval
→ Timeline Planning
→ Conflict Validation
→ 实际修改视频
→ 输出可播放的新版本**

并通过 Evaluation 与真实用户行为持续验证：

> **Agent 是否真正降低了从 Review 到 Revision 的操作成本。**

即认为 V0 核心闭环成立。