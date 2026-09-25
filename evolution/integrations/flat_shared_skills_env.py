"""SkillFlow environment adapter for flat shared skill namespaces."""

from __future__ import annotations

from pathlib import Path

import yaml

from libs.terminus_env.environments.shared_skills_env import SharedSkillsDockerEnvironment


class FlatSharedSkillsDockerEnvironment(SharedSkillsDockerEnvironment):
    """Mount ``<job_dir>/shared_skills`` directly, without a group subdirectory.

    Uses host networking for legacy host-local gateways. OpenAI profiles instead
    join the shared adapter network configured by ``SharedSkillsDockerEnvironment``.
    """

    @property
    def _shared_skills_dir(self) -> Path:
        return self.trial_paths.trial_dir.parent / self._shared_skills_root

    def _write_shared_skills_override(self, target_compose_path: Path) -> None:
        super()._write_shared_skills_override(target_compose_path)
        if self._llm_adapter_network:
            return
        data = yaml.safe_load(target_compose_path.read_text(encoding="utf-8"))
        data["services"]["main"]["network_mode"] = "host"
        target_compose_path.write_text(yaml.safe_dump(data, sort_keys=False))
