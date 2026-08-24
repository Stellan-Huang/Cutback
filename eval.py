import json
import time
from pathlib import Path

from src.agent import parse_review
import argparse


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data",
        default="data/eval_cases.jsonl",
    )

    parser.add_argument(
        "--output",
        default="outputs/eval_results.jsonl",
    )

    return parser.parse_args()



def load_cases(data_path):
    with data_path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]



def action_correct(case, result):
    if case["expected_status"] != "ACTION":
        return None

    if result.status != "ACTION" or result.action is None:
        return False

    return (
        result.action.action == "DELETE_RANGE"
        and result.action.start_time == case["start_time"]
        and result.action.end_time == case["end_time"]
    )


def main():
    args = parse_args()

    data_path = Path(args.data)
    result_path = Path(args.output)

    cases = load_cases(data_path)


    status_correct_count = 0
    action_correct_count = 0
    action_total = 0
    latencies = []

    result_path.parent.mkdir(exist_ok=True)

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

            status_correct = (
                result is not None
                and result.status == case["expected_status"]
            )

            if status_correct:
                status_correct_count += 1

            current_action_correct = None

            if case["expected_status"] == "ACTION":
                action_total += 1

                if result is not None:
                    current_action_correct = action_correct(case, result)
                else:
                    current_action_correct = False

                if current_action_correct:
                    action_correct_count +=  1

            record = {
                "id": case["id"],
                "review": case["review"],
                "expected_status": case["expected_status"],
                "predicted_status": result.status if result else None,
                "status_correct": status_correct,
                "action_correct": current_action_correct,
                "latency": round(latency, 2),
                "error": error,
            }

            output.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

            mark = "PASS" if status_correct else "FAIL"

            print(
                f"{case['id']}  "
                f"{mark}  "
                f"expected={case['expected_status']}  "
                f"predicted={record['predicted_status']}  "
                f"{latency:.2f}s"
            )

    print()
    print("=== Cutback Evaluation v0 ===")
    print(
        f"Status Accuracy: "
        f"{status_correct_count}/{len(cases)} "
        f"({status_correct_count / len(cases):.1%})"
    )

    print(
        f"Action Accuracy: "
        f"{action_correct_count}/{action_total} "
        f"({action_correct_count / action_total:.1%})"
    )

    print(
        f"Average Latency: "
        f"{sum(latencies) / len(latencies):.2f}s"
    )

    print(f"Results: {result_path}")


if __name__ == "__main__":
    main()
