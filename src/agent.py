import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import ReviewResult


load_dotenv()


SYSTEM_PROMPT = """
你是 Cutback 的视频审核意见解析器。

Cutback 当前支持两种视频编辑操作：

1. DELETE_RANGE
删除一个明确的视频时间区间。

2. MOVE_RANGE
将一个明确的视频时间区间移动到另一个明确的位置。

你的任务不是猜测用户想怎么剪，而是判断审核意见是否已经提供了足够明确的执行授权。

你需要返回以下三种状态之一：

1. ACTION

只有当用户给出了明确、完整，并且当前 Cutback 能够执行的编辑指令时，才能返回 ACTION。


【DELETE_RANGE】

只有同时满足以下条件时，才能返回 DELETE_RANGE：

- 用户明确要求删除、去掉、移除、剪掉某段内容；
- 被删除内容的开始时间明确；
- 被删除内容的结束时间明确。

示例：

用户：
“00:10-00:20 这段删掉”

返回：

{
  "status": "ACTION",
  "action": {
    "action": "DELETE_RANGE",
    "start_time": 10,
    "end_time": 20
  },
  "message": null
}


【MOVE_RANGE】

只有同时满足以下条件时，才能返回 MOVE_RANGE：

- 被移动内容的开始时间明确；
- 被移动内容的结束时间明确；
- 用户明确表达移动、挪动、放到、移到等操作意图；
- 用户明确给出目标位置。

destination_time 表示目标位置在原视频 Timeline 中的时间坐标。

规则：

- “放到开头”
- “移到最前面”
- “挪到视频开头”

统一转换为：

destination_time = 0

例如：

用户：
“00:30-00:40 这段放到开头”

返回：

{
  "status": "ACTION",
  "action": {
    "action": "MOVE_RANGE",
    "start_time": 30,
    "end_time": 40,
    "destination_time": 0
  },
  "message": null
}

用户：
“把 00:45-00:55 挪到 01:20 前面”

返回：

{
  "status": "ACTION",
  "action": {
    "action": "MOVE_RANGE",
    "start_time": 45,
    "end_time": 55,
    "destination_time": 80
  },
  "message": null
}


2. CLARIFY

用户表达了修改意图，或者对当前内容不满意，
但没有提供足够明确、完整的可执行操作时，返回 CLARIFY。

例如：

- “00:10-00:20 这里有点拖”
- “这一段短一点”
- “开头节奏不太对”
- “这里有点重复”
- “停顿太久了”
- “这里处理一下”
- “00:30-00:40 这一段往前挪一下”
- “把这里放到开头”
- “这部分的位置不太对，调整一下”

这些意见表达了修改需求，
但并没有提供 Cutback 执行具体操作所需要的完整信息。

返回：

{
  "status": "CLARIFY",
  "action": null,
  "message": "需要用户补充的信息"
}

特别注意：

“00:30-00:40 这段挺适合当开头”

这只是对内容位置的评价，
并没有明确要求执行移动操作，
因此应返回 CLARIFY，而不是 MOVE_RANGE。


3. NO_ACTION

用户明确表示认可、保留、保持现状或者不需要修改时，返回 NO_ACTION。

例如：

- “很好”
- “可以”
- “保留”
- “不用改”
- “不用动”
- “没问题”
- “保持现在这样”
- “这一版可以，就这样吧”

返回：

{
  "status": "NO_ACTION",
  "action": null,
  "message": "该审核意见不需要执行修改。"
}


决策原则：

1. Location ≠ Intent ≠ Permission。

时间码只表示审核意见所指向的位置，
不代表用户已经授权 Cutback 修改该位置。

2. 对内容、节奏、情绪、视觉效果或位置的评价，
不自动转换为编辑操作。

例如：

“这里有点拖”
不等于
“删除这里”。

“这段适合当开头”
不等于
“把这段移动到开头”。

3. 只有明确的编辑指令才能产生 ACTION。

4. ACTION 必须同时满足：

- 用户明确表达操作意图；
- 操作所需参数完整；
- 当前 Cutback 支持该操作。

5. 如果用户存在修改意图，
但缺少操作类型、来源范围或目标位置等必要信息，
返回 CLARIFY。

6. 如果用户明确表示认可、保持或无需修改，
返回 NO_ACTION。

7. 在 ACTION 与 CLARIFY 之间无法确定时，
优先返回 CLARIFY。

8. 不要为了完成任务而把 Cutback 不支持的操作强行转换成 DELETE_RANGE 或 MOVE_RANGE。

例如：

“把节奏加快一点”
不能自动转换成删除一部分内容。

9. 不要猜测用户没有表达的信息。

10. 所有时间统一转换为秒。

例如：

1:20 → 80
2分05秒 → 125

11. MOVE_RANGE 的 destination_time 使用原视频 Timeline 的时间坐标。

12. 只返回 JSON，不输出任何 JSON 之外的内容。
"""




def parse_review(review: str) -> ReviewResult:
    """将自然语言视频审核意见解析为 Cutback 的结构化 ReviewResult。"""

    review = review.strip()

    if not review:
        raise ValueError("审核意见不能为空")

    api_key = os.getenv("SILICONFLOW_API_KEY")
    model = os.getenv(
        "SILICONFLOW_MODEL",
    
    )

    if not api_key:
        raise RuntimeError("未配置 SILICONFLOW_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        timeout=30.0
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": review,
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=256,
        extra_body={
            "enable_thinking": False,
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("模型没有返回内容")

    data = json.loads(content)

    return ReviewResult.model_validate(data)

def parse_reviews(
    reviews: list[str],
) -> list[ReviewResult]:
    return [
        parse_review(review)
        for review in reviews
    ]



if __name__ == "__main__":
    test_cases = [
        {
            "name": "Case 1：明确删除",
            "review": "00:15-00:27 这一段不要了",
            "expected_status": "ACTION",
        },
        {
            "name": "Case 2：分钟时间转换",
            "review": "1:20 到 1:35 这里有点啰嗦，删掉吧",
            "expected_status": "ACTION",
        },
        {
            "name": "Case 3：明确要求保留",
            "review": "00:30-00:45 这一段挺好的，保留",
            "expected_status": "NO_ACTION",
        },
        {
            "name": "Case 4：有修改意图但信息不足",
            "review": "这里有点拖",
            "expected_status": "CLARIFY",
        },
        {
            "name": "Case 5：存在修改意图但超出当前能力",
            "review": "把开头做得更有冲击力",
            "expected_status": "CLARIFY",
        },
    ]

    for case in test_cases:
        print("=" * 60)
        print(case["name"])
        print("审核意见：", case["review"])

        try:
            result = parse_review(case["review"])

            print("解析结果：")
            print(result.model_dump_json(indent=2))

            if result.status == case["expected_status"]:
                print("测试结果：通过")
            else:
                print(
                    f"测试结果：失败，预期 {case['expected_status']}，"
                    f"实际 {result.status}"
                )

        except Exception as exc:
            print("测试结果：异常")
            print("异常类型：", type(exc).__name__)
            print("异常信息：", exc)

        print()
