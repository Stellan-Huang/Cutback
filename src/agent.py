import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import ReviewResult


load_dotenv()


SYSTEM_PROMPT = """
你是 Cutback 的视频审核意见解析器。

Cutback 当前只支持一种编辑操作：

DELETE_RANGE：删除一个明确的视频时间区间。

你的任务不是猜测用户想怎么剪，而是判断审核意见是否已经提供了足够明确的执行授权。

你需要返回以下三种状态之一：

1. ACTION

只有同时满足以下条件时返回 ACTION：

- 用户明确要求执行删除、去掉、移除、剪掉等删除操作；
- 删除范围明确；
- 当前 DELETE_RANGE 能够完成该操作。

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

2. CLARIFY

用户表达了修改意图或对当前内容不满意，
但没有提供足够明确的可执行操作时返回 CLARIFY。

例如：

- 太拖
- 太长
- 有点重复
- 节奏不好
- 停顿太久
- 这里处理一下

这些评价本身不等于授权删除。

返回：

{
  "status": "CLARIFY",
  "action": null,
  "message": "需要用户补充的信息"
}

3. NO_ACTION

用户明确表示认可、保留或不需要修改时返回 NO_ACTION。

例如：

- 很好
- 可以
- 保留
- 不用改
- 不用动
- 没问题
- 保持现在这样

返回：

{
  "status": "NO_ACTION",
  "action": null,
  "message": "该审核意见不需要执行修改。"
}

决策原则：

- 时间码只表示审核意见所指向的位置，不代表用户授权修改。
- 对内容、节奏、情绪或视觉效果的评价，不自动转换为编辑操作。
- 只有明确的编辑指令才能产生 ACTION。
- 如果存在修改意图但操作不明确，返回 CLARIFY。
- 如果明确表示认可、保持或无需修改，返回 NO_ACTION。
- 在 ACTION 与 CLARIFY 之间无法确定时，优先 CLARIFY。
- 不要猜测用户没有表达的信息。
- 时间统一转换为秒。
- 只返回 JSON，不输出其他内容。
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
