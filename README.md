# Cutback

> Review → Editable Timeline

Cutback 是一个面向视频 **Review → Revision** 工作流的 AI Agent Demo，用来把自然语言审核意见转换成可确认、可执行的时间线编辑操作。

当前版本：**v0.1 Beta**

[在线体验](https://nymr3ccdfec8elxc6eqc6u.streamlit.app/)

---

## Why Cutback

一版视频完成后，修改通常要经过：

**Reviewer 提出意见 → Creator / Editor 理解意图 → 定位时间线 → 转换成具体剪辑操作 → 执行修改**

这里有相当一部分工作并不是创作本身，而是在反复把“人说的话”重新翻译成“时间线要怎么改”。

Cutback 想验证的是一个更具体的问题：

> **AI 能否成为 Review 和 Editable Timeline 之间的中间层，在不夺走用户控制权的前提下，把修改意见更快地变成真实编辑操作？**

它不是自动剪辑器，也不试图替代 Premiere、Resolve 或 CapCut。当前版本只关注 Review-to-Edit 这一段链路。

---

## How It Works

```text
Review
↓
ACTION / CLARIFY / NO_ACTION
↓
结构化 EditAction
↓
用户确认
↓
时间线规划
↓
冲突检查
↓
FFmpeg 执行
↓
修改后视频
```

当前支持 `DELETE_RANGE` 和 `MOVE_RANGE` 两种时间线操作，可以一次解析多条 Review，并在执行前检查操作冲突。所有真正修改视频的动作都需要用户确认，AI 负责理解和提出建议，确定性程序负责执行。

---



## Agent Decision Policy

Cutback 不把“理解了用户在说什么”等同于“获得了修改权限”。

核心原则是：

> **Location ≠ Intent ≠ Permission**

例如：

> “00:10–00:20 这里有点拖。”

系统知道用户在评论哪一段，也知道用户并不满意，但不知道用户究竟想删除、缩短还是加速，更没有获得删除授权，因此应该返回 `CLARIFY`。

而：

> “00:10–00:20 这段删掉。”

同时包含明确位置、编辑动作和授权，因此可以返回：

`ACTION → DELETE_RANGE`

这个原则来自实际 Bad Case。第一版测试中，模型曾把“负面评价”直接理解成删除指令。对于创作工作流来说，一次错误修改带来的返工和信任损失，通常比一次必要的确认成本更高。

但安全也不能变成无意义的保守。后续自测中，系统一度大量返回 `CLARIFY`，调整后又出现 `NO_ACTION` 使用过度的问题，因此目前三个状态的边界被明确为：

- 信息充分且当前能力支持 → `ACTION`
- 补充信息或调整表达后可以执行 → `CLARIFY`
- 意图已经明确，但操作超出当前能力 → `NO_ACTION`

`CLARIFY` 和 `NO_ACTION` 都需要告诉用户为什么当前不能执行，以及下一步可以怎么做。

---



## Evaluation

第一版内部 Evaluation 使用 18 条 Dev Case：

- Status Accuracy：**16/18（88.9%）**
- Action Accuracy：**6/6（100%）**
- 主要 Bad Case：将负面评价错误解释为删除授权

收紧 Decision Policy、明确 `Location ≠ Intent ≠ Permission` 后：

- Dev：**17/18（94.4%）**
- Holdout：**12/12**
- `DELETE_RANGE` Action Test：通过
- 新增 `MOVE_RANGE` 后相关测试全部通过
- Regression Test：未观察到明显能力回退

这里的目标不是把一个小测试集刷到 100%，而是尽早发现会真正伤害产品体验的错误，尤其是 **Over-execution**：Agent 在没有充分授权的情况下修改用户作品。

这些结果只能说明当前决策边界在既定测试范围内更稳定，不能证明真实用户的 Review-to-Edit 效率已经提升。

---



## Product Status

Cutback 当前处于 **v0.1 Beta**。

发布后的持续自测，以及一位有剪辑经验的业余剪辑师反馈，都指向了同一个问题：当前最明显的瓶颈已经不是三状态策略，而是**基础能力覆盖不足**。

真实 Review 很少始终使用“精确时间码 + 单一动作”的形式。用户更自然地说“刚才那句话删掉”“第二次提到价格的时候”“这里字幕换一下”“这一段加速”，一条自然语言里也可能同时包含多个修改要求。

因此现阶段继续扩大用户测试的价值有限。大量 `CLARIFY / NO_ACTION` 很可能只是功能缺失造成的，无法有效判断三状态机制究竟提高了效率，还是增加了额外交互成本。

下一步优先补齐两个最小能力：

> **视频语义理解 / 内容定位 + Multi-action Parsing**

之后再用真实用户行为验证：

**Accept / Modify / Reject、Unauthorized Execution、Clarify 次数、修改耗时和真实 Bad Case。**

---



## Current Limitations

当前版本是用于验证 Review-to-Edit 核心链路的 MVP，而不是完整剪辑软件。

目前主要依赖明确的时间线信息，只支持 `DELETE_RANGE / MOVE_RANGE`，尚不能稳定理解“刚才那句话”“第二次出现产品时”等语义引用，也不能把一句复杂 Review 拆成多个编辑动作。

字幕、音轨、倍速、B-roll、多轨编辑和生成式视频等能力暂未加入。它们不是长期不重要，而是不属于 V0 已经验证的最小闭环。

---



## Tech Stack

**Python · Streamlit · LLM API · Pydantic · FFmpeg**

LLM 负责理解自然语言和生成结构化决策，Pydantic 负责约束输出，时间线规划和 FFmpeg 负责确定性执行。AI 不直接修改视频。

---



## Roadmap

当前优先级：

> **Semantic Grounding → Multi-action Parsing → Real User Evaluation → Bad Case Analysis → Product Direction**

下一阶段不会直接扩成完整 NLE，而是先补最小的视频语义定位能力和多动作解析，让真实 Review 有基本的可执行覆盖率。

只有在这之后，真实用户测试的数据才有意义：它需要回答的不是“AI 能不能跑起来”，而是更关键的问题——

> **Cutback 是否真的在不增加越权修改和额外交互成本的前提下，降低了 Review → Revision 的实际成本。**

