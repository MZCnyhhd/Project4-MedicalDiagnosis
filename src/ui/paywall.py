"""
收费解锁模块（微信收款）。

功能说明:
    - 采用「个人微信收款码 + 支付后确认」的软校验模式：个人收款码没有支付回调，
      无法自动核销，因此由用户扫码支付后勾选确认来解锁。
    - 解锁状态保存在 st.session_state.paywall_paid，仅当前浏览器会话有效，
      重新登录/刷新会话后需重新支付。
    - 管理员（admin）默认免费直通，便于自测与内部使用。

配置方式（环境变量，均可不配）:
    - PAYWALL_ENABLED: 置为 false/0/no 可整体关闭收费拦截（默认开启）。
    - PAYWALL_PRICE: 解锁金额，默认 9.9（元）。
    - PAYWALL_FREE_ROLES: 免费角色白名单，逗号分隔，默认 admin。

依赖关系:
    - 标准库 `os`。
    - `streamlit`: 界面渲染。
    - `src.services.auth`: 读取当前登录用户角色。
"""

# [导入模块] ############################################################################################################
# [标准库 | Standard Libraries] =========================================================================================
import os                                                              # 操作系统接口：读取环境变量与拼接收款码路径
# [第三方库 | Third-party Libraries] ====================================================================================
import streamlit as st                                                 # Web 界面框架：渲染收款码与确认按钮
# [内部模块 | Internal Modules] =========================================================================================
from src.services.auth import get_user_role                            # 认证服务：读取当前用户角色

# [全局变量] ############################################################################################################
# 收款码图片路径（相对项目根目录的 assets/ 目录）
QR_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "wechat_pay_qr.png")

# session_state 中标记「本次会话已解锁」的键名
PAID_STATE_KEY = "paywall_paid"

# 支付确认后置位，用于让主流程在解锁后自动继续执行
PENDING_EXEC_KEY = "paywall_pending_execute"

# 默认解锁金额（元）
DEFAULT_PRICE = "9.9"

# 默认免费角色（管理员自测直通）
DEFAULT_FREE_ROLES = "admin"

# [定义函数] ############################################################################################################
# [配置读取] ============================================================================================================
def is_paywall_enabled() -> bool:
    """
    判断收费拦截是否启用。

    :return: 启用返回 True；环境变量 PAYWALL_ENABLED 为 false/0/no/off 时返回 False
    """
    raw = os.getenv("PAYWALL_ENABLED", "true").strip().lower()
    return raw not in ("false", "0", "no", "off")

# [配置读取-金额] =======================================================================================================
def get_price() -> str:
    """
    获取解锁金额（字符串，便于直接展示）。

    :return: 形如 "9.9" 的金额文本
    """
    return os.getenv("PAYWALL_PRICE", DEFAULT_PRICE).strip() or DEFAULT_PRICE

# [配置读取-免费角色] ===================================================================================================
def get_free_roles() -> set:
    """
    获取免费直通角色白名单。

    :return: 角色名集合，例如 {"admin"}
    """
    raw = os.getenv("PAYWALL_FREE_ROLES", DEFAULT_FREE_ROLES)
    return {role.strip() for role in raw.split(",") if role.strip()}

# [内部-当前用户角色] ===================================================================================================
def _current_role() -> str:
    """
    读取当前登录用户的角色。

    :return: 角色名；未登录或读取失败时返回空字符串
    """
    username = st.session_state.get("username")
    if not username:
        return ""
    try:
        return get_user_role(username) or ""
    except Exception:
        return ""

# [外部-是否已解锁] =====================================================================================================
def is_unlocked() -> bool:
    """
    判断当前会话是否已通过收费拦截。

    管理员的判定顺序在前：管理员永远视为已解锁，不显示收款码。

    :return: 可直接执行业务返回 True
    """
    # [step1] 收费功能整体关闭 → 放行
    if not is_paywall_enabled():
        return True
    # [step2] 免费角色（默认 admin）→ 放行
    if _current_role() in get_free_roles():
        return True
    # [step3] 本次会话已完成支付确认 → 放行
    return bool(st.session_state.get(PAID_STATE_KEY, False))

# [外部-渲染锁定提示] ===================================================================================================
def render_lock_notice(mode_label: str) -> None:
    """
    在主操作按钮上方渲染付费提示（仅对需付费的用户显示）。

    :param mode_label: 模式名称，用于提示文案（如“开始诊断”）
    """
    if is_unlocked():
        return
    st.caption(f"🔒 「{mode_label}」为付费功能：微信扫码支付 ¥{get_price()} 后解锁，当前会话内不限次数。")

# [外部-渲染收款码] =====================================================================================================
def render_paywall(mode_label: str) -> None:
    """
    渲染微信收款码与支付确认区。

    个人收款码无支付回调，采用「扫码支付 → 勾选确认 → 解锁」的软校验流程；
    解锁后写入 session_state 并触发重跑，让主流程自动继续执行。

    :param mode_label: 模式名称，用于展示与日志（如“开始诊断”）
    """
    price = get_price()

    # [step1] 标题与说明
    st.markdown("---")
    st.markdown(f"#### 💳 解锁「{mode_label}」 · 微信支付 ¥{price}")
    st.caption("本平台为付费服务，扫码支付后即可解锁；管理员账号免费。")

    # [step2] 左右分栏：左收款码，右操作说明
    col_qr, col_tip = st.columns([1, 1])

    with col_qr:
        if os.path.exists(QR_IMAGE_PATH):
            st.image(QR_IMAGE_PATH, caption=f"微信扫码支付 ¥{price}")
        else:
            st.error("未找到收款码图片 `assets/wechat_pay_qr.png`，请检查文件是否随项目一起部署。")

    with col_tip:
        st.markdown(
            f"""
1. 打开微信 → 扫一扫，扫描左侧收款码；
2. 支付金额 **¥{price}**（金额可随意，本功能不做自动核销）；
3. 支付完成后勾选下方确认，点击「确认支付并解锁」。
"""
        )
        st.info("提示：如需**对公 / 批量采购**或**发票**，请联系项目维护者。")

        # [step3] 确认与解锁
        confirmed = st.checkbox("我已完成支付", key="paywall_confirm")
        if st.button(
            "✅ 确认支付并解锁",
            type="primary",
            use_container_width=True,
            disabled=not confirmed,
            key="paywall_unlock_btn",
        ):
            st.session_state[PAID_STATE_KEY] = True
            st.session_state[PENDING_EXEC_KEY] = True
            # 注意：此处不可再改写 paywall_confirm（该控件本轮已实例化，
            # Streamlit 会抛 StreamlitWidgetAlreadyInstantiatedError）。
            st.rerun()

# [外部-消费解锁后的待执行标记] =========================================================================================
def consume_pending_execute() -> bool:
    """
    读取并清除「支付后待自动执行」标记。

    用于让用户完成支付确认后无需再次点击主按钮，直接继续本次分析。

    :return: 存在待执行标记返回 True（读取后即清除）
    """
    return bool(st.session_state.pop(PENDING_EXEC_KEY, False))
