import hmac
import os
import uuid
from pathlib import Path

import streamlit as st

from src.agent import parse_review
from src.executor import execute_actions
from src.models import EditAction, ReviewResult


# ============================================================
# 基础配置
# ============================================================

st.set_page_config(
    page_title="Cutback",
    page_icon="✂️",
    layout="wide",
)


MAX_UPLOAD_MB = 100


# ============================================================
# 配置读取
# 本地优先读取环境变量 / .env
# Streamlit Cloud 可读取 Secrets
# ============================================================

def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)

    if value:
        return value

    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


# 确保 agent.py 中通过 os.getenv() 也能读取 Streamlit Cloud Secrets
siliconflow_api_key = get_setting("SILICONFLOW_API_KEY")

if siliconflow_api_key:
    os.environ["SILICONFLOW_API_KEY"] = siliconflow_api_key

siliconflow_model = get_setting("SILICONFLOW_MODEL")

if siliconflow_model:
    os.environ["SILICONFLOW_MODEL"] = siliconflow_model


# ============================================================
# Beta 访问控制
# ============================================================

def check_access() -> None:
    expected_code = get_setting("CUTBACK_ACCESS_CODE")

    # 未配置访问码时直接开放
    if not expected_code:
        return

    if st.session_state.get("authenticated"):
        return

    st.title("Cutback")
    st.caption("Review-to-Edit Agent · Private Beta")

    code = st.text_input(
        "Beta 访问码",
        type="password",
        placeholder="请输入邀请访问码",
    )

    if st.button(
        "进入 Cutback",
        type="primary",
    ):
        if hmac.compare_digest(
            code,
            expected_code,
        ):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("访问码错误。")

    st.stop()


check_access()


# ============================================================
# 每个用户使用独立运行目录
# ============================================================

if "session_id" not in st.session_state:
    st.session_state["session_id"] = uuid.uuid4().hex


SESSION_DIR = (
    Path("runtime")
    / st.session_state["session_id"]
)

SESSION_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

INPUT_PATH = SESSION_DIR / "input.mp4"
OUTPUT_PATH = SESSION_DIR / "output.mp4"


# ============================================================
# 页面标题
# ============================================================

st.title("Cutback")

with st.expander("Beta 使用说明"):
    st.markdown("""
Cutback 当前为邀请测试版本。

**建议素材**
- MP4 视频
- 建议时长 ≤ 3 分钟
- 建议文件 ≤ 30 MB

**当前能力**
- 删除指定片段
- 移动指定片段
- 批量处理多条 Review
- 模糊意见会要求进一步确认

**测试建议**
请按照你平时真实提出视频修改意见的方式输入，
不需要为了适应 Cutback 特意改变表达方式。

**数据提示**
请勿上传包含敏感、保密或无权处理的视频内容。
    """)

st.caption(
    "Review-to-Edit Agent · "
    "将视频审核意见转换为可确认、可执行的 Timeline 操作"
)

st.caption(
    "Beta 建议：MP4 · ≤100MB · "
    "请勿上传敏感或未经授权的视频素材"
)


# ============================================================
# 上传视频
# ============================================================

uploaded_file = st.file_uploader(
    "上传视频",
    type=["mp4"],
)


if uploaded_file is not None:
    file_size_mb = (
        uploaded_file.size
        / 1024
        / 1024
    )

    st.caption(
        f"文件大小：{file_size_mb:.1f} MB"
    )

    if file_size_mb > MAX_UPLOAD_MB:
        st.error(
            f"当前 Beta 最大支持 "
            f"{MAX_UPLOAD_MB}MB 视频。"
        )
        st.stop()


# ============================================================
# 输入 Review
# ============================================================

reviews_text = st.text_area(
    "审核意见",
    placeholder=(
        "每行输入一条审核意见，例如：\n"
        "00:10-00:20 这段删掉\n"
        "00:30-00:40 这段放到开头\n"
        "00:50-01:00 这里有点拖\n"
        "01:10-01:20 这段挺好的，保留"
    ),
    height=180,
)


reviews = [
    line.strip()
    for line in reviews_text.splitlines()
    if line.strip()
]


# ============================================================
# 清除上一轮动态控件状态
# ============================================================

def clear_dynamic_state() -> None:
    prefixes = (
        "approve_",
        "start_",
        "end_",
        "destination_",
    )

    for key in list(
        st.session_state.keys()
    ):
        if key.startswith(prefixes):
            del st.session_state[key]


# ============================================================
# 分析全部 Review
# ============================================================

if st.button(
    "分析全部意见",
    type="primary",
):
    if uploaded_file is None:
        st.error("请先上传视频。")

    elif not reviews:
        st.error(
            "请输入至少一条审核意见。"
        )

    else:
        INPUT_PATH.write_bytes(
            uploaded_file.getbuffer()
        )

        # 新一轮分析时清除旧结果
        clear_dynamic_state()

        st.session_state.pop(
            "output_ready",
            None,
        )

        if OUTPUT_PATH.exists():
            OUTPUT_PATH.unlink()

        items = []

        with st.spinner(
            f"正在分析 {len(reviews)} 条审核意见..."
        ):
            for review in reviews:
                try:
                    result = parse_review(
                        review
                    )

                    items.append(
                        {
                            "review": review,
                            "result": result.model_dump(),
                            "error": None,
                        }
                    )

                except Exception as e:
                    items.append(
                        {
                            "review": review,
                            "result": None,
                            "error": str(e),
                        }
                    )

        st.session_state[
            "review_items"
        ] = items

        st.session_state[
            "input_ready"
        ] = True


# ============================================================
# 展示 Review Queue
# ============================================================

approved_actions: list[EditAction] = []


if "review_items" in st.session_state:
    st.divider()
    st.subheader("Review 分析结果")

    items = st.session_state[
        "review_items"
    ]

    for index, item in enumerate(items):
        with st.container(border=True):

            st.markdown(
                f"**Review {index + 1}**"
            )

            st.write(
                item["review"]
            )

            # --------------------------------------------
            # API / 解析错误
            # --------------------------------------------

            if item["error"]:
                st.error(
                    f"解析失败：{item['error']}"
                )
                continue

            result = ReviewResult.model_validate(
                item["result"]
            )

            # --------------------------------------------
            # ACTION
            # --------------------------------------------

            if result.status == "ACTION":
                action = result.action

                st.success(
                    f"ACTION · {action.action}"
                )

                if (
                    action.action
                    == "DELETE_RANGE"
                ):
                    st.write(
                        "建议删除 "
                        f"**{action.start_time:.1f}s "
                        f"– {action.end_time:.1f}s**"
                    )

                elif (
                    action.action
                    == "MOVE_RANGE"
                ):
                    st.write(
                        "建议将 "
                        f"**{action.start_time:.1f}s "
                        f"– {action.end_time:.1f}s** "
                        "移动到 "
                        f"**{action.destination_time:.1f}s**"
                    )

                st.caption(
                    "执行前可以修改参数。"
                )

                start_time = st.number_input(
                    "开始时间（秒）",
                    min_value=0.0,
                    value=float(
                        action.start_time
                    ),
                    step=0.1,
                    key=f"start_{index}",
                )

                end_time = st.number_input(
                    "结束时间（秒）",
                    min_value=0.0,
                    value=float(
                        action.end_time
                    ),
                    step=0.1,
                    key=f"end_{index}",
                )

                destination_time = None

                if (
                    action.action
                    == "MOVE_RANGE"
                ):
                    destination_time = (
                        st.number_input(
                            "目标位置（秒）",
                            min_value=0.0,
                            value=float(
                                action.destination_time
                            ),
                            step=0.1,
                            key=(
                                f"destination_"
                                f"{index}"
                            ),
                        )
                    )

                approved = st.checkbox(
                    "批准执行",
                    key=f"approve_{index}",
                )

                if approved:
                    try:
                        if (
                            action.action
                            == "DELETE_RANGE"
                        ):
                            final_action = (
                                EditAction(
                                    action=(
                                        "DELETE_RANGE"
                                    ),
                                    start_time=(
                                        start_time
                                    ),
                                    end_time=(
                                        end_time
                                    ),
                                )
                            )

                        else:
                            final_action = (
                                EditAction(
                                    action=(
                                        "MOVE_RANGE"
                                    ),
                                    start_time=(
                                        start_time
                                    ),
                                    end_time=(
                                        end_time
                                    ),
                                    destination_time=(
                                        destination_time
                                    ),
                                )
                            )

                        approved_actions.append(
                            final_action
                        )

                    except Exception as e:
                        st.error(
                            f"参数无效：{e}"
                        )

            # --------------------------------------------
            # CLARIFY
            # --------------------------------------------

            elif (
                result.status
                == "CLARIFY"
            ):
                st.warning(
                    "CLARIFY · 需要进一步确认"
                )

                if result.message:
                    st.write(
                        result.message
                    )

            # --------------------------------------------
            # NO_ACTION
            # --------------------------------------------

            elif (
                result.status
                == "NO_ACTION"
            ):
                st.info(
                    "NO_ACTION · 无需修改"
                )

                if result.message:
                    st.write(
                        result.message
                    )


# ============================================================
# 执行批准的 Actions
# ============================================================

if "review_items" in st.session_state:
    st.divider()

    st.write(
        "已批准 "
        f"**{len(approved_actions)}** "
        "个编辑操作"
    )

    if st.button(
        "执行已批准操作",
        type="primary",
    ):
        if not approved_actions:
            st.warning(
                "请至少批准一个编辑操作。"
            )

        elif not INPUT_PATH.exists():
            st.error(
                "原视频文件不存在，请重新上传。"
            )

        else:
            try:
                with st.spinner(
                    "正在生成修改后视频..."
                ):
                    execute_actions(
                        approved_actions,
                        str(INPUT_PATH),
                        str(OUTPUT_PATH),
                    )

                st.session_state[
                    "output_ready"
                ] = True

                st.success(
                    "编辑完成。"
                )

            except Exception as e:
                st.error(
                    f"无法执行：{e}"
                )


# ============================================================
# Original / Revised 对比
# ============================================================

if (
    st.session_state.get(
        "input_ready"
    )
    and INPUT_PATH.exists()
):
    st.divider()

    if (
        st.session_state.get(
            "output_ready"
        )
        and OUTPUT_PATH.exists()
    ):
        left, right = st.columns(2)

        with left:
            st.subheader("Original")

            st.video(
                str(INPUT_PATH)
            )

        with right:
            st.subheader("Revised")

            st.video(
                str(OUTPUT_PATH)
            )

    else:
        st.subheader("Original")

        st.video(
            str(INPUT_PATH)
        )
