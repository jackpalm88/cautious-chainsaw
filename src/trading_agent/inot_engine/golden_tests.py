"""
Golden Test Framework for INoT Engine

Ensures deterministic behavior across versions:
- Fixed test scenarios (golden files)
- Deterministic execution (temp=0, fixed model)
- Diff detection for regressions
- Backtesting compatibility validation
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pytest
from orchestrator import Decision, INoTOrchestrator
from validator import INoTValidator


@dataclass
class GoldenScenario:
    """Test scenario with expected output"""
    id: str
    name: str
    description: str

    # Inputs
    context: dict  # Market context
    memory_summary: str

    # Expected outputs
    expected_action: str
    expected_confidence_range: tuple  # (min, max)
    expected_vetoed: bool

    # Full golden output (for exact matching)
    golden_agent_outputs: list[dict]

    # Metadata
    model_version: str
    created_at: str
    last_validated: str


class GoldenTestHarness:
    """
    Test harness for deterministic INoT validation.

    Usage:
    1. Create golden scenarios (once)
    2. Run tests against current implementation
    3. Detect regressions (output != golden)
    4. Update goldens when intentional changes made
    """

    def __init__(self, golden_dir: Path):
        self.golden_dir = golden_dir
        self.golden_dir.mkdir(parents=True, exist_ok=True)

        # Load all golden scenarios
        self.scenarios = self._load_scenarios()

    def _load_scenarios(self) -> list[GoldenScenario]:
        """Load all golden test scenarios from disk"""
        scenarios = []

        for json_file in self.golden_dir.glob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
                scenarios.append(GoldenScenario(**data))

        return scenarios

    def create_golden(
        self,
        scenario_id: str,
        name: str,
        context: dict,
        memory_summary: str,
        orchestrator: INoTOrchestrator,
        description: str = ""
    ) -> GoldenScenario:
        """
        Create new golden scenario by running current implementation.

        This captures the "correct" behavior for future regression detection.
        """
        # Execute INoT
        decision = orchestrator.reason(
            self._dict_to_context(context),
            self._string_to_memory(memory_summary)
        )

        # Create golden scenario
        golden = GoldenScenario(
            id=scenario_id,
            name=name,
            description=description,
            context=context,
            memory_summary=memory_summary,
            expected_action=decision.action,
            expected_confidence_range=(
                decision.confidence - 0.05,
                decision.confidence + 0.05
            ),
            expected_vetoed=decision.vetoed,
            golden_agent_outputs=decision.agent_outputs,
            model_version=orchestrator.model_version,
            created_at=datetime.now().isoformat(),
            last_validated=datetime.now().isoformat()
        )

        # Save to disk
        golden_path = self.golden_dir / f"{scenario_id}.json"
        with open(golden_path, 'w') as f:
            json.dump(asdict(golden), f, indent=2)

        self.scenarios.append(golden)

        return golden

    def test_scenario(
        self,
        scenario: GoldenScenario,
        orchestrator: INoTOrchestrator,
        strict: bool = False
    ) -> 'TestResult':
        """
        Test current implementation against golden scenario.

        Args:
            scenario: Golden test case
            orchestrator: INoT engine to test
            strict: If True, require exact agent output match
                   If False, only check action + confidence range

        Returns:
            TestResult with pass/fail and details
        """
        # Execute INoT with same inputs
        decision = orchestrator.reason(
            self._dict_to_context(scenario.context),
            self._string_to_memory(scenario.memory_summary)
        )

        # Check basic outputs
        action_match = decision.action == scenario.expected_action

        conf_in_range = (
            scenario.expected_confidence_range[0] <= decision.confidence <=
            scenario.expected_confidence_range[1]
        )

        veto_match = decision.vetoed == scenario.expected_vetoed

        basic_pass = action_match and conf_in_range and veto_match

        # Strict mode: check exact agent outputs
        exact_match = False
        if strict:
            current_hash = self._hash_agent_outputs(decision.agent_outputs)
            golden_hash = self._hash_agent_outputs(scenario.golden_agent_outputs)
            exact_match = (current_hash == golden_hash)

        result = TestResult(
            scenario_id=scenario.id,
            passed=basic_pass and (exact_match if strict else True),
            action_match=action_match,
            confidence_in_range=conf_in_range,
            veto_match=veto_match,
            exact_match=exact_match if strict else None,
            current_output=decision,
            golden_output=scenario
        )

        return result

    def run_all_tests(
        self,
        orchestrator: INoTOrchestrator,
        strict: bool = False
    ) -> list['TestResult']:
        """Run all golden tests and return results"""
        results = []

        for scenario in self.scenarios:
            result = self.test_scenario(scenario, orchestrator, strict)
            results.append(result)

        return results

    def _dict_to_context(self, context_dict: dict):
        """Convert dict to FusedContext object"""
        class MockContext:
            def __init__(self, d):
                for k, v in d.items():
                    setattr(self, k, v)

        return MockContext(context_dict)

    def _string_to_memory(self, summary: str):
        """Convert string to MemorySnapshot"""
        class MockMemory:
            def __init__(self, summary):
                self.summary = summary

            def to_summary(self, max_tokens):
                return self.summary

        return MockMemory(summary)

    def _hash_agent_outputs(self, agents: list[dict]) -> str:
        """Create deterministic hash of agent outputs"""
        # Remove timestamp fields that change
        normalized = []
        for agent in agents:
            agent_copy = agent.copy()
            agent_copy.pop("timestamp", None)
            normalized.append(agent_copy)

        # Hash
        json_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


@dataclass
class TestResult:
    """Result of golden test execution"""
    scenario_id: str
    passed: bool

    # Detailed checks
    action_match: bool
    confidence_in_range: bool
    veto_match: bool
    exact_match: bool | None = None

    # Full outputs for debugging
    current_output: Decision = None
    golden_output: GoldenScenario = None

    def summary(self) -> str:
        """Human-readable summary"""
        if self.passed:
            return f"✅ {self.scenario_id}: PASS"
        else:
            failures = []
            if not self.action_match:
                failures.append(
                    f"action ({self.current_output.action} != "
                    f"{self.golden_output.expected_action})"
                )
            if not self.confidence_in_range:
                failures.append(
                    f"confidence ({self.current_output.confidence:.2f} "
                    f"not in {self.golden_output.expected_confidence_range})"
                )
            if not self.veto_match:
                failures.append(
                    f"veto ({self.current_output.vetoed} != "
                    f"{self.golden_output.expected_vetoed})"
                )
            if self.exact_match is not None and not self.exact_match:
                failures.append("exact output mismatch")

            return f"❌ {self.scenario_id}: FAIL - {', '.join(failures)}"


# Pytest integration
@pytest.fixture
def golden_harness():
    """Pytest fixture for golden test harness"""
    return GoldenTestHarness(Path("tests/golden"))


@pytest.fixture
def inot_orchestrator():
    """Pytest fixture for INoT orchestrator"""
    from orchestrator import INoTOrchestrator
    from validator import INoTValidator

    validator = INoTValidator(Path("schemas/inot_agents.schema.json"))

    # Mock LLM for deterministic testing
    class DeterministicLLM:
        def complete(self, prompt, **kwargs):
            # Return consistent mock response
            class Response:
                content = """[
                  {"agent": "Signal", "action": "BUY", "confidence": 0.7, "reasoning": "RSI oversold at support", "key_factors": ["RSI oversold"]},
                  {"agent": "Risk", "approved": true, "confidence": 0.8, "position_size_adjustment": 1.0, "stop_loss_required": true, "reasoning": "Risk acceptable"},
                  {"agent": "Context", "regime": "ranging", "regime_confidence": 0.75, "signal_regime_fit": 0.8, "news_alignment": "neutral", "weight_adjustment": 1.0, "reasoning": "Ranging market"},
                  {"agent": "Synthesis", "final_decision": {"action": "BUY", "lots": 0.1, "stop_loss": 1.08, "confidence": 0.72}, "reasoning_synthesis": "Consensus buy with risk management", "agent_weights_applied": {"Signal": 0.7, "Risk": 0.8, "Context": 1.0}, "memory_update_intent": "RSI oversold in ranging regime"}
                ]"""
                usage = {"input_tokens": 3000, "output_tokens": 800}
            return Response()

    return INoTOrchestrator(
        llm_client=DeterministicLLM(),
        config={
            "model_version": "claude-sonnet-4-test",
            "temperature": 0.0
        },
        validator=validator
    )


def test_golden_scenarios(golden_harness, inot_orchestrator):
    """Run all golden tests"""
    results = golden_harness.run_all_tests(inot_orchestrator, strict=False)

    for result in results:
        print(result.summary())
        assert result.passed, f"Golden test {result.scenario_id} failed"


# Example: Creating golden scenarios
if __name__ == "__main__":
    from orchestrator import INoTOrchestrator
    from validator import INoTValidator

    # Setup
    validator = INoTValidator(Path("schemas/inot_agents.schema.json"))

    # Mock LLM
    class MockLLM:
        def complete(self, prompt, **kwargs):
            class Response:
                content = """[
                  {"agent": "Signal", "action": "BUY", "confidence": 0.75, "reasoning": "RSI oversold", "key_factors": ["RSI"]},
                  {"agent": "Risk", "approved": true, "confidence": 0.8, "position_size_adjustment": 1.0, "stop_loss_required": true, "reasoning": "Risk OK"},
                  {"agent": "Context", "regime": "ranging", "regime_confidence": 0.7, "signal_regime_fit": 0.8, "news_alignment": "neutral", "weight_adjustment": 1.0, "reasoning": "Range"},
                  {"agent": "Synthesis", "final_decision": {"action": "BUY", "lots": 0.1, "stop_loss": 1.08, "confidence": 0.72}, "reasoning_synthesis": "Buy", "agent_weights_applied": {"Signal": 0.75, "Risk": 0.8, "Context": 1.0}, "memory_update_intent": "RSI oversold"}
                ]"""
                usage = {"input_tokens": 3000, "output_tokens": 800}
            return Response()

    orchestrator = INoTOrchestrator(
        llm_client=MockLLM(),
        config={"temperature": 0.0},
        validator=validator
    )

    harness = GoldenTestHarness(Path("tests/golden"))

    # Create golden scenario 1: RSI oversold in ranging market
    scenario1 = harness.create_golden(
        scenario_id="rsi_oversold_ranging",
        name="RSI Oversold in Ranging Market",
        context={
            "symbol": "EURUSD",
            "price": 1.0850,
            "rsi": 28,
            "macd": -0.002,
            "atr": 0.0015,
            "sentiment": -0.2,
            "current_position": None,
            "timestamp": "2024-10-30T10:00:00Z"
        },
        memory_summary="Recent: 70% win rate in ranging markets. RSI<30 setups won 8/10 times.",
        orchestrator=orchestrator,
        description="Test mean-reversion signal in confirmed ranging regime"
    )

    print(f"✅ Created golden scenario: {scenario1.id}")

    # Create golden scenario 2: Risk veto due to drawdown
    # (Would need different mock LLM response - omitted for brevity)

    print(f"\nTotal golden scenarios: {len(harness.scenarios)}")
