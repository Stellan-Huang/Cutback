# Cutback V0

## 1. 产品定义

Cutback 是一个 **Review-to-Edit Agent**。

它将视频审核意见转换为结构化、可执行的 Timeline 操作，经用户确认后修改视频。

核心流程：

**Review → EditAction → Confirm → Execute → Preview**

---

## 2. V0 用户场景

用户已有一版视频，并收到带时间码的审核意见。

例如：

> 00:10–00:20 这段删掉。

Cutback 转换为：

```json
{
  "action": "DELETE_RANGE",
  "start_time": 10,
  "end_time": 20
}
```

用户确认后，系统执行修改并生成新版本。

---

## 3. V0 核心假设

V0 只验证一个问题：

> **Review 能否可靠转化为实际视频编辑操作。**

不验证完整自动剪辑，也不验证完整 NLE。

---

## 4. 当前能力

### 4.1 EditAction

Cutback 使用结构化 `EditAction` 表达编辑操作。

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

---

### 4.2 Review 解析

使用 LLM 将自然语言审核意见转换为 `EditAction`。

例如：

> 00:10–00:20 这段删掉。

↓

```json
{
  "action": "DELETE_RANGE",
  "start_time": 10,
  "end_time": 20
}
```

原则：

* LLM 负责理解 Review。
* `EditAction` 负责校验模型输出。
* 无法明确转换的 Review 不猜测、不执行。

---

### 4.3 视频执行

Executor 将合法 `EditAction` 转换为确定性 FFmpeg 操作。

执行链路：

**EditAction → Executor → FFmpeg → Output**

当前支持：

**DELETE_RANGE**

---

### 4.4 产品交互

当前核心交互：

**上传视频
→ 输入 Review
→ AI 生成 EditAction
→ 展示编辑建议
→ 用户确认
→ 执行修改
→ 对比原视频与新版本**

原则：

> **AI 不得在用户确认前修改视频。**

---

## 5. 下一阶段：Evaluation

下一阶段不优先增加新功能，而是使用真实 Review 测试当前闭环。

记录：

* Review 是否被正确理解
* EditAction 是否正确
* 用户接受 / 拒绝情况
* 典型 Bad Case
* 完成修改所需时间

根据真实失败案例决定下一项能力。

---

## 6. 非目标

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

## 7. 成功标准

Cutback 能稳定完成：

**带时间码的 Review
→ 合法 EditAction
→ 用户确认
→ 实际修改视频
→ 输出可播放的新版本**

即认为 V0 核心闭环成立。
