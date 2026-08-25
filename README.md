# Cutback

> Review → Editable Timeline

Cutback 是一个面向视频 Review → Revision 工作流的 AI Agent Demo，
将自然语言审核意见转换为可确认、可执行的 Timeline 编辑操作。

当前版本：v0.1 Beta

[在线体验](https://nymr3ccdfec8elxc6eqc6u.streamlit.app/)

---

## Why Cutback

视频修改通常经历：

Reviewer 提出意见
→ Creator / Editor 理解意图
→ 定位 Timeline
→ 转换为具体剪辑操作
→ 执行修改

其中大量工作并不是创作本身，而是把自然语言 Review
重新解释成具体的 Timeline 操作。

Cutback 尝试验证一个问题：

**AI 能否成为 Review 与 Editable Timeline 之间的中间层？**

---

## How It Works

Review
↓
LLM Decision
↓
ACTION / CLARIFY / NO_ACTION
↓
Structured EditAction
↓
Human Approval
↓
Timeline Planner
↓
FFmpeg Execution
↓
Revised Video

当前支持：

- DELETE_RANGE：删除指定 Timeline 区间
- MOVE_RANGE：将指定区间移动到新的 Timeline 位置
- Multiple Reviews：批量解析多条审核意见
- Conflict Validation：检测互相冲突的编辑操作
- Human-in-the-loop：所有编辑操作均需用户确认后执行

---



## Agent Decision Policy

Cutback 不将“理解用户意图”等同于“获得编辑权限”。

核心原则：

**Location ≠ Intent ≠ Permission**

例如：

“00:10-00:20 这里有点拖”

表示用户对这一片段不满意，但没有明确授权删除，因此返回：

CLARIFY

而：

“00:10-00:20 这段删掉”

包含明确编辑授权，因此返回：

ACTION → DELETE_RANGE

对于 Creator Workflow，错误执行的成本通常高于多确认一次，
因此 Cutback 在不确定情况下优先 Clarify。

---



## Evaluation

第一版 Evaluation：

- Dev Status Accuracy：16/18（88.9%）
- 主要 Bad Case：将负面评价错误解释为删除授权

迭代 Decision Policy 后：

- Dev：17/18（94.4%）
- Holdout：12/12
- DELETE_RANGE Action Test：通过
- MOVE_RANGE 新增测试：全部通过
- Regression Test：未观察到既有能力掉点

确立核心原则：**Location ≠ Intent ≠ Permission**

Evaluation 的目标不是追求测试集 100%，
而是识别可能导致 Agent 未经授权修改作品的 Over-execution。

---



## Product Status

Cutback 当前处于 Private Beta。

当前阶段重点不是继续增加 Timeline Action，
而是通过真实 Creator / Editor 的 Review 数据验证：

- 真实 Review 中有多少可以映射为结构化编辑操作？
- AI Proposal 有多少可以直接接受？
- 用户通常如何表达 Timeline Location？
- 当前最大的能力缺口来自 Action Space，还是 Semantic Grounding？

---



## Current Limitations

当前版本是用于验证 Review-to-Edit 工作流的 MVP，而非完整 NLE。

主要限制包括：

- 主要依赖明确 Timeline 信息
- 仅支持 DELETE_RANGE / MOVE_RANGE
- 尚不能理解“刚才那句话”“第二次出现产品时”等复杂语义引用
- 不处理复杂多轨编辑、B-roll、字幕和生成式视频操作

---



## Tech Stack

Python · Streamlit · LLM API · Pydantic · FFmpeg

---



## Roadmap

当前优先级：

**Real User Evaluation → Bad Case Analysis → Product Direction**

潜在下一阶段包括 Transcript / Shot / Multimodal Context Grounding，
但是否继续开发将由真实用户测试结果决定。