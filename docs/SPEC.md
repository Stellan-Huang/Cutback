# Cutback V0

## 1. 产品定义

Cutback 是一个 **Review-to-Edit Agent**。

它将视频审核意见转换为结构化、可执行的 Timeline 操作，经剪辑者确认后执行修改。

核心流程：

**Review → EditAction → Confirm → Execute → Preview**

---

## 2. V0 用户场景

用户已有一版视频，并收到带时间码的审核意见。

例如：

> 00:10–00:20 这段删掉。

Cutback 将其转换为：

```json
{
  "action": "DELETE_RANGE",
  "start_time": 10,
  "end_time": 20
}
```

用户确认后执行修改并生成新版本视频。

---

## 3. V0 目标

跑通一个最小真实闭环：

**视频 + Review
→ EditAction
→ 用户确认
→ 执行剪辑
→ Preview**

V0 只验证一个核心假设：

> **Review 能否可靠转化为实际视频编辑操作。**

---

## 4. 当前能力

### Phase 1｜视频执行

已实现：

**DELETE_RANGE**

执行链路：

**Python → FFmpeg → Output**

输入：

* `input.mp4`
* `start_time`
* `end_time`

输出：

* 删除指定区间后的新视频

---

### Phase 2｜结构化编辑动作

使用 `EditAction` 统一表达编辑操作。

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

执行链路：

**EditAction → Executor → FFmpeg**

---

### Phase 3｜审核意见解析

当前阶段：

**Review → LLM → EditAction**

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

* LLM 只负责理解自然语言并生成结构化动作。
* `EditAction` 负责校验模型输出。
* Executor 负责确定性执行。
* 无法明确转换的 Review 不猜测、不执行。

---

## 5. 后续阶段

### Phase 4｜最小产品界面

加入：

* 视频上传
* Review 输入
* EditAction 展示
* Accept / Reject
* 执行修改
* 修改前后视频 Preview

目标：

> 让非开发者能够完成 Cutback 的完整核心流程。

---

### Phase 5｜Evaluation

使用真实 Review 测试：

* Review 解析是否正确
* EditAction 是否正确
* Accept / Reject 情况
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

只有真实用户反馈证明必要时，才引入新的复杂度。

---

## 7. 成功标准

Cutback 能稳定完成：

**带时间码的 Review
→ 合法 EditAction
→ 用户确认
→ 实际修改视频
→ 输出可播放的新版本**

即认为 V0 核心闭环成立。
