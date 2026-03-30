"""
素材质量评分模块 - 智能质量评估与路由

评分维度：
1. 完整度 - 字段是否齐全
2. 唯一性 - 与已有素材去重
3. IP 契合度 - 与 IP 方向的匹配
4. 可执行性 - 是否具体可操作
5. 风险等级 - 内容安全性
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class QualityScore:
    """质量评分结果"""
    completeness: float  # 完整度 0-1
    uniqueness: float    # 唯一性 0-1
    ip_fit: float        # IP契合度 0-1
    actionable: float    # 可执行性 0-1
    risk_level: str      # 风险等级 safe/caution/warning/danger
    overall: float       # 综合得分 0-1

    def to_dict(self) -> Dict:
        return {
            "completeness": round(self.completeness, 3),
            "uniqueness": round(self.uniqueness, 3),
            "ip_fit": round(self.ip_fit, 3),
            "actionable": round(self.actionable, 3),
            "risk_level": self.risk_level,
            "overall": round(self.overall, 3)
        }


class MaterialQualityChecker:
    """素材质量检查器"""

    # IP 方向关键词映射（可扩展）
    IP_KEYWORDS = {
        "职场认知升级": [
            "职场", "工作", "职业", "升职", "加薪", "领导", "同事",
            "沟通", "汇报", "面试", "简历", "跳槽", "转行", "成长"
        ],
        "人性洞察": [
            "人性", "心理", "情绪", "关系", "社交", "影响力", "说服",
            "认知", "偏见", "行为", "动机", "需求", "欲望", "恐惧"
        ],
        "个人成长破局": [
            "成长", "突破", "改变", "习惯", "自律", "学习", "思考",
            "认知升级", "思维", "格局", "视野", "目标", "执行力"
        ]
    }

    # 风险关键词
    RISK_KEYWORDS = {
        "danger": [
            "政治", "共产党", "政府", "领导人", "敏感", "翻墙", "VPN",
            "色情", "暴力", "赌博", "毒品", "诈骗"
        ],
        "warning": [
            "死亡", "自杀", "抑郁", "焦虑", "压力", "失败", "失业",
            "离婚", "分手", "背叛", "欺骗", "阴谋"
        ],
        "caution": [
            "竞争", "斗争", "权谋", "算计", "利用", "操控", "套路"
        ]
    }

    def __init__(self, ip_direction: str = "职场认知升级 / 人性洞察 / 个人成长破局"):
        self.ip_direction = ip_direction
        self._existing_materials: List[Dict] = []  # 用于去重

    def set_existing_materials(self, materials: List[Dict]):
        """设置已有素材库，用于去重"""
        self._existing_materials = materials

    def check(self, material: Dict) -> Tuple[QualityScore, List[str]]:
        """
        对素材进行完整质量检查

        Args:
            material: 素材字典，包含 category, content, metadata 等

        Returns:
            (QualityScore, 改进建议列表)
        """
        suggestions = []

        # 1. 完整度检查
        completeness, comp_suggestions = self._check_completeness(material)
        suggestions.extend(comp_suggestions)

        # 2. 唯一性检查
        uniqueness, uni_suggestions = self._check_uniqueness(material)
        suggestions.extend(uni_suggestions)

        # 3. IP 契合度检查
        ip_fit, ip_suggestions = self._check_ip_fit(material)
        suggestions.extend(ip_suggestions)

        # 4. 可执行性检查
        actionable, act_suggestions = self._check_actionable(material)
        suggestions.extend(act_suggestions)

        # 5. 风险等级检查
        risk_level, risk_suggestions = self._check_risk(material)
        suggestions.extend(risk_suggestions)

        # 计算综合得分
        # 风险等级影响权重
        risk_weights = {
            "safe": 1.0,
            "caution": 0.9,
            "warning": 0.7,
            "danger": 0.0
        }
        risk_weight = risk_weights.get(risk_level, 0.5)

        overall = (
            completeness * 0.25 +
            uniqueness * 0.20 +
            ip_fit * 0.30 +
            actionable * 0.25
        ) * risk_weight

        score = QualityScore(
            completeness=completeness,
            uniqueness=uniqueness,
            ip_fit=ip_fit,
            actionable=actionable,
            risk_level=risk_level,
            overall=overall
        )

        return score, suggestions

    def _check_completeness(self, material: Dict) -> Tuple[float, List[str]]:
        """检查字段完整度"""
        suggestions = []
        score = 1.0

        category = material.get("category", "")
        content = material.get("content", "")
        metadata = material.get("metadata", {})

        # 检查内容长度
        if len(content) < 20:
            score -= 0.3
            suggestions.append("内容过短，建议补充细节")
        elif len(content) > 2000:
            score -= 0.1
            suggestions.append("内容过长，建议精简或拆分")

        # 检查元数据
        required_meta = {
            "quote": ["risk", "scene", "cost", "timeliness"],
            "case": ["risk", "timeliness"],
            "viewpoint": ["risk", "timeliness"],
            "action": ["cost"],
            "topic": []
        }

        required = required_meta.get(category, [])
        missing = [f for f in required if f not in metadata or not metadata[f]]

        if missing:
            score -= len(missing) * 0.1
            suggestions.append(f"缺少元数据字段: {', '.join(missing)}")

        # 检查内容质量
        if category == "quote":
            if not re.search(r'["""《]', content):
                score -= 0.1
                suggestions.append("金句建议包含引号或书名号标记")

        elif category == "case":
            if "冲突" not in content or "结果" not in content:
                score -= 0.15
                suggestions.append("案例建议包含'冲突'和'结果'要素")

        elif category == "viewpoint":
            if "依据" not in content and "证据" not in content:
                score -= 0.1
                suggestions.append("观点建议注明依据或证据")

        elif category == "action":
            if not re.search(r'\d+\.', content) and "步骤" not in content:
                score -= 0.1
                suggestions.append("行动建议包含具体步骤")

        return max(0, score), suggestions

    def _check_uniqueness(self, material: Dict) -> Tuple[float, List[str]]:
        """检查与已有素材的唯一性"""
        suggestions = []

        if not self._existing_materials:
            return 1.0, suggestions

        content = material.get("content", "")
        content_lower = content.lower()

        max_similarity = 0.0
        similar_material = None

        for existing in self._existing_materials:
            existing_content = existing.get("content", "")
            # 使用序列匹配计算相似度
            similarity = SequenceMatcher(
                None, content_lower, existing_content.lower()
            ).ratio()

            if similarity > max_similarity:
                max_similarity = similarity
                similar_material = existing

        # 相似度阈值
        if max_similarity > 0.8:
            suggestions.append(f"与已有素材高度相似({max_similarity:.1%})，建议去重")
            return 0.2, suggestions
        elif max_similarity > 0.6:
            suggestions.append(f"与已有素材中度相似({max_similarity:.1%})，建议检查")
            return 0.6, suggestions
        elif max_similarity > 0.4:
            suggestions.append(f"与已有素材轻度相似({max_similarity:.1%})")
            return 0.8, suggestions

        return 1.0, suggestions

    def _check_ip_fit(self, material: Dict) -> Tuple[float, List[str]]:
        """检查与 IP 方向的契合度"""
        suggestions = []
        content = material.get("content", "")
        content_lower = content.lower()

        # 统计关键词匹配
        matched_keywords = []
        total_keywords = 0

        for domain, keywords in self.IP_KEYWORDS.items():
            total_keywords += len(keywords)
            for kw in keywords:
                if kw.lower() in content_lower:
                    matched_keywords.append(kw)

        # 计算匹配度
        if not matched_keywords:
            suggestions.append("内容与 IP 方向关联度较低，建议补充相关角度")
            return 0.4, suggestions

        # 去重后的匹配词
        unique_matches = list(set(matched_keywords))
        match_ratio = len(unique_matches) / min(10, total_keywords)

        score = min(1.0, 0.3 + match_ratio * 0.7)

        if score < 0.5:
            suggestions.append(f"IP契合度较低，建议从 {self.ip_direction} 角度改写")

        return score, suggestions

    def _check_actionable(self, material: Dict) -> Tuple[float, List[str]]:
        """检查可执行性"""
        suggestions = []
        category = material.get("category", "")
        content = material.get("content", "")

        # 不同类别的可执行性标准
        if category == "quote":
            # 金句的可执行性：是否容易理解和传播
            if len(content) < 50:
                return 0.9, suggestions  # 短金句易传播
            return 0.7, suggestions

        elif category == "case":
            # 案例的可执行性：是否有明确的行动和结果
            has_action = "动作" in content or "行动" in content or "做了" in content
            has_result = "结果" in content or " outcome" in content.lower()

            if has_action and has_result:
                return 0.9, suggestions
            elif has_action or has_result:
                suggestions.append("案例建议同时包含行动和结果")
                return 0.7, suggestions
            else:
                suggestions.append("案例缺少行动或结果描述")
                return 0.5, suggestions

        elif category == "viewpoint":
            # 观点的可执行性：是否有应用指导
            has_application = "应用" in content or "可以" in content or "建议" in content
            return 0.8 if has_application else 0.6, suggestions

        elif category == "action":
            # 行动的可执行性：步骤是否清晰
            steps = re.findall(r'\d+\.', content)
            if len(steps) >= 3:
                return 0.95, suggestions
            elif len(steps) >= 1:
                suggestions.append("行动步骤可以更加详细")
                return 0.8, suggestions
            else:
                suggestions.append("行动缺少具体步骤")
                return 0.6, suggestions

        elif category == "topic":
            # 选题的可执行性：是否有明确的钩子
            has_hook = "开头" in content or "钩子" in content
            return 0.85 if has_hook else 0.7, suggestions

        return 0.7, suggestions

    def _check_risk(self, material: Dict) -> Tuple[str, List[str]]:
        """检查内容风险等级"""
        suggestions = []
        content = material.get("content", "")
        content_lower = content.lower()

        # 检查各类风险关键词
        for level, keywords in self.RISK_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    suggestions.append(f"检测到潜在风险内容: {kw}")
                    return level, suggestions

        # 检查元数据中的风险标记
        metadata = material.get("metadata", {})
        risk_meta = metadata.get("risk", "safe")

        if risk_meta == "forbidden":
            return "danger", suggestions + ["元数据标记为禁用"]
        elif risk_meta == "context":
            return "caution", suggestions + ["需要语境理解，谨慎使用"]

        return "safe", suggestions


class MaterialRouter:
    """素材路由 - 根据质量评分决定处理方式"""

    # 阈值配置
    THRESHOLDS = {
        "auto_approve": 0.80,    # 自动入库
        "human_review": 0.55,    # 人工审核
        "auto_discard": 0.30     # 自动丢弃
    }

    def __init__(self, thresholds: Optional[Dict] = None):
        if thresholds:
            self.THRESHOLDS.update(thresholds)

    def route(self, material: Dict, quality_score: QualityScore) -> Tuple[str, str]:
        """
        路由决策

        Args:
            material: 素材
            quality_score: 质量评分

        Returns:
            (决策: approve/review/discard, 原因)
        """
        overall = quality_score.overall

        # 高风险直接丢弃
        if quality_score.risk_level == "danger":
            return "discard", "内容存在高风险"

        # 根据得分路由
        if overall >= self.THRESHOLDS["auto_approve"]:
            return "approve", f"质量优秀({overall:.2f})，自动入库"

        elif overall >= self.THRESHOLDS["human_review"]:
            reasons = []
            if quality_score.completeness < 0.7:
                reasons.append("完整度不足")
            if quality_score.ip_fit < 0.6:
                reasons.append("IP契合度低")
            if quality_score.uniqueness < 0.6:
                reasons.append("可能重复")
            reason = "; ".join(reasons) if reasons else "质量中等，建议审核"
            return "review", reason

        elif overall >= self.THRESHOLDS["auto_discard"]:
            return "review", f"质量较低({overall:.2f})，建议优化"

        else:
            return "discard", f"质量不合格({overall:.2f})"


class QualityControlPipeline:
    """质量控制完整流程"""

    def __init__(
        self,
        ip_direction: str = "职场认知升级 / 人性洞察 / 个人成长破局",
        thresholds: Optional[Dict] = None
    ):
        self.checker = MaterialQualityChecker(ip_direction)
        self.router = MaterialRouter(thresholds)

    def process(
        self,
        materials: List[Dict],
        existing_materials: Optional[List[Dict]] = None
    ) -> Dict:
        """
        批量处理素材质量控制

        Args:
            materials: 待检查的新素材列表
            existing_materials: 已有素材库（用于去重）

        Returns:
            分类结果
        """
        if existing_materials:
            self.checker.set_existing_materials(existing_materials)

        results = {
            "approved": [],
            "review": [],
            "discarded": [],
            "stats": {
                "total": len(materials),
                "approved": 0,
                "review": 0,
                "discarded": 0,
                "avg_score": 0.0
            }
        }

        total_score = 0.0

        for material in materials:
            # 质量检查
            score, suggestions = self.checker.check(material)

            # 路由决策
            decision, reason = self.router.route(material, score)

            # 补充信息
            material["quality_score"] = score.to_dict()
            material["quality_suggestions"] = suggestions
            material["routing_decision"] = decision
            material["routing_reason"] = reason

            # 分类
            if decision == "approve":
                results["approved"].append(material)
            elif decision == "review":
                results["review"].append(material)
            else:
                results["discarded"].append(material)

            total_score += score.overall

        # 统计
        results["stats"]["approved"] = len(results["approved"])
        results["stats"]["review"] = len(results["review"])
        results["stats"]["discarded"] = len(results["discarded"])
        results["stats"]["avg_score"] = round(
            total_score / max(1, len(materials)), 3
        )

        return results


# 便捷函数
def check_material_quality(
    material: Dict,
    existing_materials: Optional[List[Dict]] = None,
    ip_direction: str = "职场认知升级 / 人性洞察 / 个人成长破局"
) -> Tuple[QualityScore, List[str], str]:
    """
    便捷函数：检查单个素材质量

    Returns:
        (质量评分, 改进建议, 路由决策)
    """
    checker = MaterialQualityChecker(ip_direction)
    if existing_materials:
        checker.set_existing_materials(existing_materials)

    score, suggestions = checker.check(material)

    router = MaterialRouter()
    decision, reason = router.route(material, score)

    return score, suggestions + [reason], decision
