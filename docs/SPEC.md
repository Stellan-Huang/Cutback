# Cutback V0

## 1. 产品定义

Cutback 是一个 Review-to-Edit Agent。

它将视频审核意见转换为可执行的 Timeline 操作，让剪辑者确认后执行修改。

核心流程：

Review → EditAction → Confirm → Execute → Preview


## 2. V0 用户场景

用户已经有一版视频，并收到带时间码的审核意见。

例如：

> 00:10–00:20 这段删掉。

Cutback 将其转换为：

> DELETE_RANGE 10–20s

用户确认后，系统执行修改并生成新视频。


## 3. V0 目标

跑通一个真实闭环：

输入视频 + Review
→ 生成 EditAction
→ 用户确认
→ 执行剪辑
→ 输出新视频


## 4. 当前里程碑

Phase 1 只实现：

DELETE_RANGE

输入：

- input.mp4
- start_time
- end_time

输出：

- output.mp4


## 5. 非目标

V0 暂不实现：

- 完整 NLE
- Premiere / Resolve 插件
- Frame.io
- 多人协作
- 多轨编辑
- AI 视频生成
- 用户系统
- 云端部署


## 6. 成功标准

给定一个视频和合法的 DELETE_RANGE：

系统能够正确删除指定时间段并生成可正常播放的新视频。
