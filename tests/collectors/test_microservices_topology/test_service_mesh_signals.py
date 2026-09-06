from __future__ import annotations

from repo_analyser.collectors.microservices_topology.service_mesh import _service_mesh_signals


class TestServiceMeshSignals:
    def test_istio_virtualservice_crd_detected(self) -> None:
        docs = [{"kind": "VirtualService", "metadata": {"name": "x"}}]
        assert _service_mesh_signals(docs, "") == {"VirtualService"}

    def test_sidecar_inject_annotation_detected_via_text_grep(self) -> None:
        text = "metadata:\n  annotations:\n    sidecar.istio.io/inject: \"true\"\n"
        assert _service_mesh_signals([], text) == {"sidecar-injection-annotation"}

    def test_no_mesh_signal_is_empty_set(self) -> None:
        assert _service_mesh_signals([{"kind": "Deployment"}], "kind: Deployment\n") == set()

    def test_both_signals_present_are_both_recorded(self) -> None:
        docs = [{"kind": "PeerAuthentication"}]
        text = "sidecar.istio.io/inject: \"true\"\n"
        assert _service_mesh_signals(docs, text) == {"PeerAuthentication", "sidecar-injection-annotation"}
