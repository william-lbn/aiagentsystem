import pytest
from agentlab.course_scenarios import SCENARIOS, run_scenario


@pytest.mark.parametrize("fault", [False, True], ids=["normal", "fault"])
@pytest.mark.parametrize("slug", sorted(SCENARIOS))
def test_each_scenario_has_explicit_evidence_semantics(slug, fault):
    result = run_scenario(slug, fault)
    assert result.passed, (slug, fault, result.observation)
    assert result.fault is fault
    assert result.invariant
    assert result.evidence_level.startswith("L")
    if fault:
        assert result.fault_injected is True
        assert result.oracle_detected is True
        # L2_ORACLE_ONLY is deliberately not allowed to masquerade as system containment.
        if result.evidence_level == "L2_ORACLE_ONLY":
            assert result.system_detected is False
            assert result.contained is False
            assert result.recovered is False
            assert result.invariant_holds is False
        if result.evidence_level == "L3_CONTAINED":
            assert result.system_detected and result.contained and result.invariant_holds
        if result.evidence_level == "L4_RECOVERED":
            assert result.system_detected and result.contained and result.recovered and result.invariant_holds
    else:
        assert result.fault_injected is False
        assert result.invariant_holds is True
