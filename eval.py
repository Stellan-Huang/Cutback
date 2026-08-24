import argparse
import json
import time
from pathlib import Path

from src.agent import parse_review


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        default="data/eval_cases.jsonl",
        help="评测数据集路径",
    )

    parser.add_argument(
        "--output",
        default="outputs/eval_results.jsonl",
        help="评测结果输出路径",
    )

    return parser.parse_args()


def load_cases(data_path: Path):
    with data_path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def action_correct(case, result):
    """
    判断 ACTION 的具体编辑参数是否正确。

    老测试数据未提供 expected_action 时，
    默认视为 DELETE_RANGE。
    """

    if case["expected_status"] != "ACTION":
        return None

    if result.status != "ACTION" or result.action is None:
        return False

    expected_action = case.get(
        "expected_action",
        "DELETE_RANGE",
    )

    action = result.action

    # 动作类型必须一致
    if action.action != expected_action:
        return False

    # 来源区间必须一致
    if action.start_time != case["start_time"]:
        return False

    if action.end_time != case["end_time"]:
        return False

    # MOVE_RANGE 额外检查目标位置
    if expected_action == "MOVE_RANGE":
        return (
            action.destination_time
            == case["destination_time"]
        )

    return True


def main():
    args = parse_args()

    data_path = Path(args.data)
    result_path = Path(args.output)

    cases = load_cases(data_path)

    if not cases:
        raise ValueError(f"评测数据为空：{data_path}")

    status_correct_count = 0
    action_correct_count = 0
    action_total = 0
    latencies = []

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with result_path.open("w", encoding="utf-8") as output:
        for case in cases:
            start = time.perf_counter()

            try:
                result = parse_review(case["review"])
                error = None
            except Exception as e:
                result = None
                error = str(e)

            latency = time.perf_counter() - start
            latencies.append(latency)

            predicted_status = (
                result.status
                if result is not None
                else None
            )

            status_correct = (
                predicted_status
                == case["expected_status"]
            )

            if status_correct:
                status_correct_count += 1

            current_action_correct = None

            if case["expected_status"] == "ACTION":
                action_total += 1

                if result is not None:
                    current_action_correct = action_correct(
                        case,
                        result,
                    )
                else:
                    current_action_correct = False

                if current_action_correct:
                    action_correct_count += 1

            predicted_action = None

            if (
                result is not None
                and result.status == "ACTION"
                and result.action is not None
            ):
                predicted_action = result.action.model_dump()

            record = {
                "id": case["id"],
                "review": case["review"],

                "expected_status": case["expected_status"],
                "predicted_status": predicted_status,
                "status_correct": status_correct,

                "expected_action": case.get(
                    "expected_action",
                    "DELETE_RANGE"
                    if case["expected_status"] == "ACTION"
                    else None,
                ),

                "predicted_action": predicted_action,
                "action_correct": current_action_correct,

                "latency": round(latency, 2),
                "error": error,
            }

            output.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

            mark = "PASS" if status_correct else "FAIL"

            print(
                f"{case['id']}  "
                f"{mark}  "
                f"expected={case['expected_status']}  "
                f"predicted={predicted_status}  "
                f"{latency:.2f}s"
            )

    status_accuracy = (
        status_correct_count / len(cases)
    )

    if action_total > 0:
        action_accuracy = (
            action_correct_count / action_total
        )
    else:
        action_accuracy = None

    average_latency = (
        sum(latencies) / len(latencies)
    )

    print()
    print("=== Cutback Evaluation ===")

    print(
        f"Status Accuracy: "
        f"{status_correct_count}/{len(cases)} "
        f"({status_accuracy:.1%})"
    )

    if action_accuracy is not None:
        print(
            f"Action Accuracy: "
            f"{action_correct_count}/{action_total} "
            f"({action_accuracy:.1%})"
        )
    else:
        print("Action Accuracy: N/A")

    print(
        f"Average Latency: "
        f"{average_latency:.2f}s"
    )

    print(
        f"Results: {result_path}"
    )


if __name__ == "__main__":
    main()
