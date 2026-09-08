"""
模块名称: Medical Imaging Analysis (影像医疗诊断)

功能描述:
    融合 torchxrayvision 预训练模型，提供胸部X光影像的AI辅助诊断。
    支持18种病理检测，涵盖肺炎、心脏增大、肺结节、气胸等常见胸部病变。

设计理念:
    1.  **本地推理**: 使用预训练 DenseNet121 模型，无需联网，保护患者隐私。
    2.  **流式反馈**: 采用生成器模式，与 MDT 诊断/体检分析保持一致的 UI 体验。
    3.  **LLM 增强**: 影像分析结果交由 LLM 生成专业解读报告。

线程安全性:
    - 模型单例加载，推理过程无状态。

依赖关系:
    - `torchxrayvision`: 胸部X光预训练模型。
    - `torchvision`: 图像预处理。
    - `src.services.llm`: 统一模型工厂。

来源:
    - https://github.com/mlmed/torchxrayvision
"""

import io
import logging
from typing import Generator, Optional, Tuple

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# ---- 模型单例缓存 ----
_model_cache: dict = {}


def _get_model(model_name: str = "densenet121-res224-all"):
    """懒加载并缓存预训练模型（首次加载约需下载 ~100MB 权重）。"""
    if model_name in _model_cache:
        return _model_cache[model_name]

    try:
        import torchxrayvision as xrv
        import torch

        logger.info("首次加载影像模型 %s ...", model_name)
        model = xrv.models.DenseNet(weights=model_name)
        model.eval()
        _model_cache[model_name] = model
        logger.info("模型 %s 加载完成", model_name)
        return model
    except Exception as e:
        logger.error("加载影像模型失败: %s", e)
        raise RuntimeError(f"无法加载影像模型: {e}") from e


def _preprocess_image(image_bytes: bytes) -> "np.ndarray":
    """
    将上传的图片字节预处理为模型输入张量。
    
    流程:
        1. PIL 读取 → 灰度
        2. 归一化到 [-1024, 1024]
        3. CenterCrop + Resize(224)
    """
    import torch
    import torchvision.transforms as T
    import torchxrayvision as xrv

    # PIL 读取并转灰度
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img_np = np.array(img).astype(np.float32)

    # 归一化到 [-1024, 1024]（torchxrayvision 标准）
    img_np = xrv.datasets.normalize(img_np, 255)

    # 添加通道维度 [1, H, W]
    img_np = img_np[None, ...]

    # CenterCrop + Resize(224)
    transform = T.Compose([
        xrv.datasets.XRayCenterCrop(),
        xrv.datasets.XRayResizer(224),
    ])
    img_np = transform(img_np)

    return torch.from_numpy(img_np).float()


# ---- 病理中英文映射 ----
PATHOLOGY_CN = {
    "Atelectasis": "肺不张",
    "Consolidation": "肺实变",
    "Infiltration": "浸润",
    "Pneumothorax": "气胸",
    "Edema": "水肿",
    "Emphysema": "肺气肿",
    "Fibrosis": "纤维化",
    "Effusion": "胸腔积液",
    "Pneumonia": "肺炎",
    "Pleural_Thickening": "胸膜增厚",
    "Cardiomegaly": "心脏增大",
    "Nodule": "肺结节",
    "Mass": "肿块",
    "Hernia": "疝",
    "Lung Lesion": "肺部病变",
    "Fracture": "骨折",
    "Lung Opacity": "肺部混浊",
    "Enlarged Cardiomediastinum": "纵隔增宽",
}


def analyze_xray(
    image_bytes: bytes,
    model_name: str = "densenet121-res224-all",
    threshold: float = 0.5,
) -> Generator[dict, None, None]:
    """
    对胸部X光影像进行AI分析，以流式字典逐步返回结果。

    Args:
        image_bytes: 图片原始字节。
        model_name: torchxrayvision 模型权重名。
        threshold: 阳性判定阈值（概率 > threshold 视为阳性）。

    Yields:
        {"type": "progress", "message": str}
        {"type": "result", "pathologies": list[dict], "summary": str}
        {"type": "error", "message": str}
    """
    try:
        yield {"type": "progress", "message": "🔍 正在加载影像分析模型..."}
        model = _get_model(model_name)

        yield {"type": "progress", "message": "📷 正在预处理影像..."}
        img_tensor = _preprocess_image(image_bytes)

        yield {"type": "progress", "message": "🧠 正在进行AI推理分析..."}
        import torch
        with torch.no_grad():
            outputs = model(img_tensor[None, ...])

        # 解析结果
        probs = outputs[0].detach().numpy()
        pathologies = []
        for i, (name, prob) in enumerate(zip(model.pathologies, probs)):
            pathologies.append({
                "name_en": name,
                "name_cn": PATHOLOGY_CN.get(name, name),
                "probability": float(prob),
                "is_positive": float(prob) > threshold,
            })

        # 按概率降序排列
        pathologies.sort(key=lambda x: x["probability"], reverse=True)

        # 生成摘要
        positive = [p for p in pathologies if p["is_positive"]]
        if positive:
            summary = "AI 检测到以下阳性发现：" + "、".join(
                [f"{p['name_cn']}({p['probability']:.1%})" for p in positive]
            )
        else:
            summary = "AI 未检测到明显阳性病变（所有指标均低于阈值 {:.0%}）。".format(threshold)

        yield {
            "type": "result",
            "pathologies": pathologies,
            "summary": summary,
            "model_name": model_name,
        }

    except Exception as e:
        logger.exception("影像分析失败")
        yield {"type": "error", "message": f"影像分析失败: {str(e)}"}


def generate_imaging_report(
    pathologies: list,
    patient_info: Optional[str] = None,
) -> str:
    """
    根据影像分析结果生成 Markdown 格式的诊断报告。

    Args:
        pathologies: analyze_xray 返回的病理列表。
        patient_info: 可选的患者基本信息。

    Returns:
        Markdown 格式报告。
    """
    lines = ["## 🏥 胸部X光 AI 影像分析报告\n"]

    if patient_info:
        lines.append(f"**患者信息**: {patient_info}\n")

    # 阳性发现表格
    positive = [p for p in pathologies if p["is_positive"]]
    if positive:
        lines.append("### ⚠️ 阳性发现\n")
        lines.append("| 病理 | 中文名 | 概率 | 风险等级 |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for p in positive:
            prob = p["probability"]
            if prob > 0.8:
                level = "🔴 高"
            elif prob > 0.6:
                level = "🟠 中"
            else:
                level = "🟡 低"
            lines.append(f"| {p['name_en']} | {p['name_cn']} | {prob:.1%} | {level} |")
        lines.append("")

    # 全部指标
    lines.append("### 📊 全部指标\n")
    lines.append("| 病理 | 概率 | 状态 |")
    lines.append("| :--- | :--- | :--- |")
    for p in pathologies:
        status = "✅ 正常" if not p["is_positive"] else "⚠️ 阳性"
        lines.append(f"| {p['name_cn']} ({p['name_en']}) | {p['probability']:.1%} | {status} |")
    lines.append("")

    # 建议
    lines.append("### 💡 建议\n")
    if positive:
        lines.append("- 以上阳性发现需要结合临床症状进一步评估")
        lines.append("- 建议由专业放射科医师复核 AI 分析结果")
        lines.append("- 如有疑问，请进行进一步检查（CT、MRI 等）")
    else:
        lines.append("- AI 未检测到明显异常，建议定期复查")
        lines.append("- 如有临床症状，请结合症状进一步评估")
    lines.append("")
    lines.append("> ⚠️ **免责声明**: 本报告由 AI 模型生成，仅供参考。所有影像诊断应由专业放射科医师确认。")

    return "\n".join(lines)
