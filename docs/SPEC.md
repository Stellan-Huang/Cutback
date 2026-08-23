# Cutback V0

## 1. 产品定义

Cutback 是一个 **Review-to-Edit Agent**。

它将视频审核意见理解为结构化编辑决策，并在用户确认后执行实际视频修改。

核心流程：

**Review → Interpret → Confirm → Execute → Preview**

---

## 2. 用户场景

用户已有一版视频，并收到审核意见。

例如：

> 00:10–00:20 这段删掉。

Cutback 将其理解为：

```json
{
  "status": "ACTION",
  "action": {
    "action": "DELETE_RANGE",
    "start_time": 10,
    "end_time": 20
  },
  "message": null
}
```

用户可以直接接受、修改时间范围或拒绝建议。

只有经过确认的操作才会真正修改视频。

---

## 3. 核心假设

V0 只验证一个问题：

> **Review 能否被可靠地理解并转化为用户愿意执行的视频编辑操作。**

不验证完整自动剪辑，也不构建完整 NLE。

---

## 4. 当前能力

### 4.1 ReviewResult

Cutback 将审核意见分为三种状态：

* `ACTION`：信息充分，可以生成明确编辑操作。
* `CLARIFY`：存在修改意图，但信息不足，需要用户补充。
* `NO_ACTION`：无需执行修改。

原则：

> **信息不足时不猜测。**

---

### 4.2 EditAction

当前仅支持：

```json
{
  "action": "DELETE_RANGE",
  "start_time": 10,
  "end_time": 20
}
```

约束：

* `start_time >= 0`
* `end_time > start_time`
* 当前仅允许 `DELETE_RANGE`

LLM 负责理解 Review，Pydantic 负责校验结构化结果。

---

### 4.3 执行

合法 `EditAction` 经用户确认后，由 Executor 转换为确定性 FFmpeg 操作：

**EditAction → Executor → FFmpeg → Output**

AI 不直接操作视频。

---

### 4.4 Human-in-the-loop

对于 `ACTION`：

* 直接执行 AI 建议 → **Accept**
* 修改时间范围后执行 → **Modify**
* 拒绝执行 → **Reject**

对于 `CLARIFY`：

* 不执行；
* 请求用户补充信息。

对于 `NO_ACTION`：

* 不执行。

核心原则：

> **AI proposes, human controls.**

---

## 5. 当前产品流程

**上传视频
→ 输入 Review
→ AI 生成 ReviewResult
→ ACTION / CLARIFY / NO_ACTION
→ 用户确认或补充
→ 执行 EditAction
→ 对比原视频与新版本**

---

## 6. 下一阶段：Evaluation

暂不优先增加新的编辑能力。

首先使用真实 Review 测试当前闭环，并记录：

* Review 状态判断是否正确
* EditAction 是否正确
* Accept / Modify / Reject
* 典型 Bad Case
* 完成修改所需时间

根据真实失败案例决定下一项能力。

---

## 7. 非目标

V0 暂不实现：

* 完整 NLE
* Premiere / Resolve 插件
* Frame.io
* 多轨编辑
* 多人协作
* AI 视频生成
* Model Routing
* Style Memory
* 用户系统
* 云端部署

> **只有真实需求证明必要时，才引入新的复杂度。**

---

## 8. 成功标准

Cutback 能稳定完成：

**Review
→ 正确判断 ACTION / CLARIFY / NO_ACTION
→ 合法 EditAction
→ 用户确认或修改
→ 实际修改视频
→ 输出可播放的新版本**

即认为 V0 核心闭环成立。
