"""Skill Catalog - global index of all available skills."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any

from miniclaude.skills.base import BaseSkill, SkillMeta

logger = logging.getLogger(__name__)


class SkillCatalog:
    """Central catalog that indexes and manages all available skills.

    Responsibilities:
    - Register built-in and custom skills
    - Provide lookup by name
    - Auto-discover skills from the builtin/ and custom/ packages
    """

    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._tags_index: dict[str, list[str]] = {}  # tag -> [skill_names]

    def register(self, skill: BaseSkill) -> None:
        """Register a skill in the catalog."""
        if skill.name in self._skills:
            logger.warning("Skill '%s' already registered, overwriting.", skill.name)
        self._skills[skill.name] = skill

        # Update tag index
        for tag in skill.meta.tags:
            tag_lower = tag.lower()
            if tag_lower not in self._tags_index:
                self._tags_index[tag_lower] = []
            if skill.name not in self._tags_index[tag_lower]:
                self._tags_index[tag_lower].append(skill.name)

        logger.debug("Registered skill: %s (tags: %s)", skill.name, skill.meta.tags)

    def register_all_builtin(self) -> None:
        """Auto-discover and register all built-in skills from the builtin package."""
        import miniclaude.skills.builtin as builtin_pkg

        package_path = builtin_pkg.__path__
        for importer, module_name, is_pkg in pkgutil.iter_modules(package_path):
            if is_pkg or module_name.startswith("_"):
                continue
            try:
                module = importlib.import_module(f"miniclaude.skills.builtin.{module_name}")
                # Look for skill classes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseSkill)
                        and attr is not BaseSkill
                    ):
                        try:
                            instance = attr()
                            self.register(instance)
                        except Exception as e:
                            logger.error("Failed to instantiate skill %s: %s", attr_name, e)
            except Exception as e:
                logger.error("Failed to load skill module %s: %s", module_name, e)

        logger.info("Loaded %d built-in skills.", len(self._skills))

    def get(self, name: str) -> BaseSkill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def get_by_tag(self, tag: str) -> list[BaseSkill]:
        """Get all skills with a specific tag."""
        names = self._tags_index.get(tag.lower(), [])
        return [self._skills[n] for n in names if n in self._skills]

    def get_all(self) -> list[BaseSkill]:
        """Get all registered skills."""
        return list(self._skills.values())

    def get_all_meta(self) -> list[SkillMeta]:
        """Get metadata for all skills."""
        return [s.meta for s in self._skills.values()]

    def search_by_keywords(self, keywords: list[str]) -> list[BaseSkill]:
        """Search skills by keyword matching against tags, name, and description."""
        results: list[tuple[float, BaseSkill]] = []
        keywords_lower = [k.lower() for k in keywords]

        for skill in self._skills.values():
            score = 0.0
            for kw in keywords_lower:
                if kw in skill.name.lower():
                    score += 0.4
                if kw in skill.description.lower():
                    score += 0.3
                for tag in skill.meta.tags:
                    if kw in tag.lower():
                        score += 0.3
            if score > 0:
                results.append((score, skill))

        results.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in results]

    @property
    def skill_count(self) -> int:
        return len(self._skills)

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __repr__(self) -> str:
        names = list(self._skills.keys())
        return f"SkillCatalog({len(names)} skills: {', '.join(names[:5])}{'...' if len(names) > 5 else ''})"
