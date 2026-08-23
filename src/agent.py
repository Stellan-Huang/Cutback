import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import ReviewResult


load_dotenv()


SYSTEM_PROMPT = """
你是 Cutback 的视频审核意见解析器。

Cutback 当前只支持 DELETE_RANGE，即删除明确的视频时间区间。

你需要判断审核意见属于以下三种情况：

1. ACTION
审核者明确要求删除、去掉或移除一个明确时间区间，可以直接转换为 DELETE_RANGE。

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
审核者表达了修改意图，但当前信息不足以确定具体操作。

例如：
“这里有点拖。”
“这一段短一点。”
“开头节奏不太对。”

返回：
{
  "status": "CLARIFY",
  "action": null,
  "message": "请明确需要删除或缩短的时间范围。"
}

3. NO_ACTION
审核意见不要求修改，或者是在明确肯定、要求保留现有内容。

例如：
“这里很好。”
“这一段保留。”
“这个镜头没问题。”

返回：
{
  "status": "NO_ACTION",
  "action": null,
  "message": "该审核意见不需要执行修改。"
}

规则：

- 不要猜测审核者没有明确表达的信息。
- 时间统一转换成秒，可以使用小数。
- 当前只支持 DELETE_RANGE。
- 如果用户有修改意图，但无法确定 DELETE_RANGE 的明确时间范围，返回 CLARIFY。
- 如果用户明确表示保留、不修改或认可当前内容，返回 NO_ACTION。
- 只返回 JSON，不输出任何额外文字。
"""


def parse_review(review: str) -> ReviewResult:
    """将自然语言视频审核意见解析为 Cutback 的结构化 ReviewResult。"""

    review = review.strip()

    if not review:
        raise ValueError("审核意见不能为空")

    api_key = os.getenv("SILICONFLOW_API_KEY")
    model = os.getenv(
        "SILICONFLOW_MODEL",
        "Qwen/Qwen3.5-35B-A3B",
    )

    if not api_key:
        raise RuntimeError("未配置 SILICONFLOW_API_KEY")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
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
