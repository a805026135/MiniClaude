"""Skill Router - two-stage recall + fine ranking for skill selection."""

from __future__ import annotations

import logging
import re
from typing import Any

from miniclaude.skills.base import BaseSkill, SkillContext, SkillResult
from miniclaude.skills.catalog import SkillCatalog

logger = logging.getLogger(__name__)


class SkillRouter:
    """Two-stage skill router: Coarse Recall → Fine Ranking.

    Stage 1 (Recall): Fast keyword + tag matching to find candidate skills.
    Stage 2 (Rank): Score candidates using semantic relevance and select top-k.
    """

    def __init__(self, catalog: SkillCatalog, recall_top_k: int = 10, rank_top_k: int = 3) -> None:
        self.catalog = catalog
        self.recall_top_k = recall_top_k
        self.rank_top_k = rank_top_k

    async def route(self, user_input: str) -> list[BaseSkill]:
        """Route user input to the most relevant skills.

        Args:
            user_input: The user's query text.

        Returns:
            List of ranked skills (most relevant first), up to rank_top_k.
        """
        if not self.catalog.skill_count:
            return []

        # Stage 1: Coarse Recall
        candidates = self._recall(user_input)

        if not candidates:
            logger.debug("No skill candidates found for: %s", user_input[:100])
            return []

        # Stage 2: Fine Ranking
        ranked = self._rank(user_input, candidates)

        logger.info(
            "Skill routing: '%s' → %d candidates → top %d: %s",
            user_input[:50],
            len(candidates),
            len(ranked),
            [s.name for s in ranked],
        )
        return ranked

    def _recall(self, user_input: str) -> list[BaseSkill]:
        """Stage 1: Coarse recall using keyword and tag matching.

        Returns a broad set of potentially relevant skills.
        """
        # Extract keywords from user input
        keywords = self._extract_keywords(user_input)

        # Get candidates from keyword search
        candidates = self.catalog.search_by_keywords(keywords)

        # Also check each skill's can_handle score
        for skill in self.catalog.get_all():
            if skill not in candidates:
                score = skill.can_handle(user_input)
                if score > 0.1:
                    candidates.append(skill)

        # Deduplicate and limit
        seen: set[str] = set()
        unique: list[BaseSkill] = []
        for skill in candidates:
            if skill.name not in seen:
                seen.add(skill.name)
                unique.append(skill)

        return unique[:self.recall_top_k]

    def _rank(self, user_input: str, candidates: list[BaseSkill]) -> list[BaseSkill]:
        """Stage 2: Fine ranking using composite scoring.

        Considers:
        - Keyword relevance score
        - can_handle() score
        - Tag overlap
        - Example similarity
        """
        scored: list[tuple[float, BaseSkill]] = []

        for skill in candidates:
            # Base score from can_handle
            base_score = skill.can_handle(user_input)

            # Tag bonus: direct tag mention in query
            tag_bonus = 0.0
            query_lower = user_input.lower()
            for tag in skill.meta.tags:
                if tag.lower() in query_lower:
                    tag_bonus += 0.2

            # Example word overlap bonus
            example_bonus = 0.0
            query_words = set(query_lower.split())
            for example in skill.meta.examples[:3]:
                example_words = set(example.lower().split())
                overlap = len(query_words & example_words)
                if overlap >= 2:
                    example_bonus = max(example_bonus, 0.3)

            # Intent keyword bonus
            intent_bonus = 0.0
            intent_keywords = {
                "review": ["review", "审查", "检查", "check"],
                "refactor": ["refactor", "重构", "重写", "rewrite"],
                "debug": ["debug", "调试", "fix", "bug", "error", "错误"],
                "test": ["test", "测试", "spec", "单元测试"],
                "explain": ["explain", "解释", "what does", "how does", "说明"],
                "code_gen": ["generate", "create", "write", "implement", "生成", "创建", "编写", "实现", "开发", "编程", "coding"],
                "code_analysis": ["analyze", "analysis", "complexity", "quality", "metrics", "inspect", "examine", "audit", "assess", "分析", "复杂度", "质量", "检查", "评估", "审查"],
                "code_document": ["document", "documentation", "docstring", "comment", "readme", "docs", "文档", "注释", "说明"],
                "security_scan": ["security", "vulnerability", "scan", "audit", "penetration", "injection", "xss", "csrf", "安全", "漏洞", "扫描", "审计", "注入"],
            }
            for skill_intent, keywords in intent_keywords.items():
                if skill_intent in skill.name.lower() or skill_intent in skill.meta.tags:
                    for kw in keywords:
                        if kw in query_lower:
                            intent_bonus += 0.3
                            break

            total_score = base_score + tag_bonus + example_bonus + intent_bonus
            scored.append((total_score, skill))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Filter out very low scores and return top-k
        return [skill for score, skill in scored[:self.rank_top_k] if score > 0.1]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords from user input."""
        # Remove common stop words and short tokens
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "not", "no", "nor",
            "so", "yet", "both", "either", "neither", "each", "every",
            "all", "any", "few", "more", "most", "other", "some", "such",
            "than", "too", "very", "just", "i", "me", "my", "we", "our",
            "you", "your", "he", "she", "it", "they", "them", "this",
            "that", "these", "those", "what", "which", "who", "whom",
            "how", "when", "where", "why", "please", "help", "want",
            "的", "了", "在", "是", "我", "你", "他", "她", "它",
            "们", "这", "那", "有", "和", "与", "把", "被", "从",
            "给", "用", "请", "帮", "能", "要", "会",
        }

        # Split on whitespace and punctuation
        words = re.findall(r'[\w一-鿿]+', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        return keywords

    async def execute_skill(
        self,
        skill: BaseSkill,
        context: SkillContext,
    ) -> SkillResult:
        """Execute a matched skill and return its result."""
        try:
            logger.info("Executing skill: %s", skill.name)
            result = await skill.execute(context)
            logger.info("Skill %s completed: success=%s", skill.name, result.success)
            return result
        except Exception as e:
            logger.error("Skill %s failed: %s", skill.name, e, exc_info=True)
            return SkillResult(
                skill_name=skill.name,
                success=False,
                instructions=f"Skill execution failed: {e}",
            )
