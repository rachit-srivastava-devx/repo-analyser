from __future__ import annotations

from repo_analyser.collectors.microservices_topology.canary_rollout import _has_canary_rollout_config


class TestCanaryRolloutConfig:
    def test_flagger_canary_crd_detected(self) -> None:
        assert _has_canary_rollout_config([{"kind": "Canary"}]) is True

    def test_argo_rollout_crd_detected(self) -> None:
        assert _has_canary_rollout_config([{"kind": "Rollout"}]) is True

    def test_no_canary_config_is_false(self) -> None:
        assert _has_canary_rollout_config([{"kind": "Deployment"}]) is False
