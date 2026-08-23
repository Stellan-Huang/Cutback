import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.models import EditAction


load_dotenv()


SYSTEM_PROMPT = """
你是 Cutback 的视频审核意见解析器。

当前 V0 只支持一种编辑操作：DELETE_RANGE。

你的任务是把用户的视频审核意见转换成结构化 JSON。

规则：

1. 只有当审核意见明确要求删除、去掉或移除某个明确时间区间时，才支持。
2. 必须存在明确的开始时间和结束时间。
3. 时间统一转换成秒，可以使用小数。
4. 不要猜测用户没有表达的信息。
5. 不要输出 JSON 之外的任何内容。

支持时返回：

{
  "action": "DELETE_RANGE",
  "start_time": 10,
  "end_time": 20
}

如果无法明确转换成 DELETE_RANGE，则返回：

{
  "error": "UNSUPPORTED"
}
"""


def parse_review(review: str) -> EditAction:
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

    if data.get("error") == "UNSUPPORTED":
        raise ValueError("当前 V0 无法处理这条审核意见")

    return EditAction.model_validate(data)


if __name__ == "__main__":
    test_cases = [
        {
            "name": "Case 1：明确删除",
            "review": "00:15-00:27 这一段不要了",
            "expected": "DELETE_RANGE",
        },
        {
            "name": "Case 2：分钟时间转换",
            "review": "1:20 到 1:35 这里有点啰嗦，删掉吧",
            "expected": "DELETE_RANGE",
        },
        {
            "name": "Case 3：明确要求保留",
            "review": "00:30-00:45 这一段挺好的，保留",
            "expected": "UNSUPPORTED",
        },
        {
            "name": "Case 4：没有明确时间范围",
            "review": "这里有点拖",
            "expected": "UNSUPPORTED",
        },
        {
            "name": "Case 5：超出当前 V0 能力",
            "review": "把开头做得更有冲击力",
            "expected": "UNSUPPORTED",
        },
    ]

    for case in test_cases:
        print("=" * 60)
        print(case["name"])
        print("审核意见：", case["review"])

        try:
            action = parse_review(case["review"])

            print("解析结果：")
            print(action.model_dump_json(indent=2))

            if case["expected"] == "DELETE_RANGE":
                print("测试结果：通过")
            else:
                print("测试结果：失败，本应拒绝该审核意见")

        except ValueError as exc:
            print("解析结果：UNSUPPORTED")
            print("原因：", exc)

            if case["expected"] == "UNSUPPORTED":
                print("测试结果：通过")
            else:
                print("测试结果：失败，本应生成 EditAction")

        except Exception as exc:
            print("测试结果：异常")
            print("异常类型：", type(exc).__name__)
            print("异常信息：", exc)

        print()
