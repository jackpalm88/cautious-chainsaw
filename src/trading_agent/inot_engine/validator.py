"""
INoT Agent Output Validator with Auto-Remediation

Validates LLM output against strict JSON schema and attempts automatic
correction if validation fails. Ensures production reliability.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import jsonschema
from jsonschema import ValidationError


@dataclass
class ValidationResult:
    """Result of validation attempt"""
    valid: bool
    agents: list[dict] | None = None
    errors: list[str] | None = None
    remediation_applied: bool = False
    remediation_attempts: int = 0


class INoTValidator:
    """
    Validates and auto-remediates INoT agent outputs.

    Validation chain:
    1. Parse JSON (strip markdown, handle malformed)
    2. Schema validation (4 agents, correct structure)
    3. Business rules (Risk veto logic, SL requirements)
    4. Auto-remediation if validation fails
    """

    def __init__(self, schema_path: Path):
        """Load JSON schema"""
        with open(schema_path) as f:
            self.schema = json.load(f)

        self.max_remediation_attempts = 2

    def validate(self, llm_output: str) -> ValidationResult:
        """
        Validate LLM output with auto-remediation.

        Args:
            llm_output: Raw string from LLM completion

        Returns:
            ValidationResult with parsed agents or error details
        """
        # Attempt 1: Parse and validate as-is
        result = self._try_parse_and_validate(llm_output)

        if result.valid:
            return result

        # Attempt 2-3: Auto-remediation
        for attempt in range(self.max_remediation_attempts):
            corrected_output = self._auto_remediate(
                llm_output,
                result.errors
            )

            result = self._try_parse_and_validate(corrected_output)
            result.remediation_applied = True
            result.remediation_attempts = attempt + 1

            if result.valid:
                return result

        # All attempts failed
        return ValidationResult(
            valid=False,
            errors=result.errors + ["Auto-remediation exhausted"]
        )

    def _try_parse_and_validate(self, output: str) -> ValidationResult:
        """Single validation attempt"""

        # Step 1: Parse JSON
        try:
            agents = self._parse_json(output)
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                errors=[f"JSON parse error: {e}"]
            )

        # Step 2: Schema validation
        try:
            jsonschema.validate(instance=agents, schema=self.schema)
        except ValidationError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Schema validation error: {e.message}"]
            )

        # Step 3: Business rules
        business_errors = self._validate_business_rules(agents)
        if business_errors:
            return ValidationResult(
                valid=False,
                agents=agents,
                errors=business_errors
            )

        # All checks passed
        return ValidationResult(valid=True, agents=agents)

    def _parse_json(self, output: str) -> list[dict]:
        """
        Extract and parse JSON from LLM output.
        Handles markdown code blocks and other formatting.
        """
        # Strip markdown code blocks
        output = re.sub(r'```json\s*', '', output)
        output = re.sub(r'```\s*', '', output)
        output = output.strip()

        # Try to find JSON array
        # Look for outermost [ ... ]
        match = re.search(r'\[.*\]', output, re.DOTALL)
        if match:
            output = match.group(0)

        # Parse
        agents = json.loads(output)

        if not isinstance(agents, list):
            raise json.JSONDecodeError(
                "Expected JSON array", output, 0
            )

        return agents

    def _validate_business_rules(self, agents: list[dict]) -> list[str]:
        """
        Validate business logic beyond JSON schema.

        Rules:
        1. Must have exactly 4 agents in order: Signal, Risk, Context, Synthesis
        2. If Risk.approved=false, must have veto_reason
        3. If Risk.stop_loss_required=true, Synthesis must provide stop_loss
        4. Agent order must be consistent
        """
        errors = []

        # Check agent count and names
        if len(agents) != 4:
            errors.append(f"Expected 4 agents, got {len(agents)}")
            return errors

        expected_agents = ["Signal", "Risk", "Context", "Synthesis"]
        actual_agents = [a.get("agent") for a in agents]

        if actual_agents != expected_agents:
            errors.append(
                f"Agent order incorrect. Expected {expected_agents}, "
                f"got {actual_agents}"
            )

        # Risk veto logic
        risk_agent = agents[1]  # Risk is second
        if not risk_agent.get("approved", True):
            if not risk_agent.get("veto_reason"):
                errors.append(
                    "Risk.approved=false but no veto_reason provided"
                )

        # Stop-loss requirement
        synthesis_agent = agents[3]  # Synthesis is fourth
        if risk_agent.get("stop_loss_required", False):
            final_decision = synthesis_agent.get("final_decision", {})
            if not final_decision.get("stop_loss"):
                errors.append(
                    "Risk requires stop-loss but Synthesis didn't provide one"
                )

        # Confidence bounds check (paranoid validation)
        for agent in agents:
            conf = agent.get("confidence")
            if conf is not None and (conf < 0 or conf > 1):
                errors.append(
                    f"{agent.get('agent')}: confidence {conf} outside [0,1]"
                )

        return errors

    def _auto_remediate(
        self,
        original_output: str,
        errors: list[str]
    ) -> str:
        """
        Attempt automatic correction of common errors.

        Strategies:
        1. Fix missing fields with defaults
        2. Correct agent order
        3. Add missing veto_reason if Risk.approved=false
        4. Clamp confidence values to [0,1]
        """
        try:
            agents = self._parse_json(original_output)
        except Exception:
            # Can't parse - can't remediate
            return original_output

        # Strategy 1: Fix agent order
        expected_order = ["Signal", "Risk", "Context", "Synthesis"]
        agents_by_name = {a.get("agent"): a for a in agents if "agent" in a}

        ordered_agents = []
        for name in expected_order:
            if name in agents_by_name:
                ordered_agents.append(agents_by_name[name])

        # Strategy 2: Add missing veto_reason
        if len(ordered_agents) >= 2:
            risk = ordered_agents[1]
            if not risk.get("approved", True) and not risk.get("veto_reason"):
                risk["veto_reason"] = "Risk threshold exceeded"

        # Strategy 3: Clamp confidence values
        for agent in ordered_agents:
            if "confidence" in agent:
                agent["confidence"] = max(0.0, min(1.0, agent["confidence"]))

        # Strategy 4: Add missing required fields with defaults
        # (This is aggressive - consider logging warnings)
        defaults = {
            "Signal": {
                "key_factors": ["technical_analysis"],
                "reasoning": "Technical signal identified"
            },
            "Risk": {
                "reasoning": "Risk assessment completed",
                "position_size_adjustment": 1.0,
                "stop_loss_required": True
            },
            "Context": {
                "reasoning": "Market context evaluated",
                "weight_adjustment": 1.0
            },
            "Synthesis": {
                "reasoning_synthesis": "Decision synthesized from agent inputs",
                "agent_weights_applied": {
                    "Signal": 1.0, "Risk": 1.0, "Context": 1.0
                }
            }
        }

        for agent in ordered_agents:
            agent_name = agent.get("agent")
            if agent_name in defaults:
                for key, default_val in defaults[agent_name].items():
                    if key not in agent:
                        agent[key] = default_val

        # Return corrected JSON
        return json.dumps(ordered_agents, indent=2)


# Auto-remediation prompt for LLM retry
AUTO_REMEDIATION_PROMPT = """
CRITICAL ERROR: Your previous response failed validation.

Errors detected:
{errors}

Previous output (first 500 chars):
{output_preview}

INSTRUCTIONS FOR CORRECTION:
1. Return ONLY valid JSON - no markdown, no explanation text
2. Must be JSON array with exactly 4 objects
3. Agent order: Signal, Risk, Context, Synthesis
4. If Risk.approved=false, MUST include veto_reason
5. If Risk.stop_loss_required=true, Synthesis.final_decision MUST have stop_loss
6. All confidence values must be 0.0-1.0

Return corrected JSON array NOW (no other text):
"""


def create_remediation_prompt(errors: list[str], output: str) -> str:
    """Generate prompt for LLM to self-correct"""
    return AUTO_REMEDIATION_PROMPT.format(
        errors="\n".join(f"- {e}" for e in errors),
        output_preview=output[:500] + "..." if len(output) > 500 else output
    )


# Example usage
if __name__ == "__main__":
    # Load validator
    schema_path = Path(__file__).parent / "schemas" / "inot_agents.schema.json"
    validator = INoTValidator(schema_path)

    # Test with sample output
    sample_output = """
    ```json
    [
      {
        "agent": "Signal",
        "action": "BUY",
        "confidence": 0.75,
        "reasoning": "RSI oversold at 28, support level holding",
        "key_factors": ["RSI oversold", "Support bounce"]
      },
      {
        "agent": "Risk",
        "approved": true,
        "confidence": 0.70,
        "position_size_adjustment": 0.5,
        "stop_loss_required": true,
        "reasoning": "Approve with reduced size due to news risk"
      },
      {
        "agent": "Context",
        "regime": "ranging",
        "regime_confidence": 0.75,
        "signal_regime_fit": 0.80,
        "news_alignment": "conflicting",
        "weight_adjustment": 1.1,
        "reasoning": "Ranging regime favors mean-reversion setups"
      },
      {
        "agent": "Synthesis",
        "final_decision": {
          "action": "BUY",
          "lots": 0.05,
          "stop_loss": 1.0835,
          "confidence": 0.68
        },
        "reasoning_synthesis": "Consensus BUY with reduced risk. Signal oversold (0.75), Risk approves 50% size, Context validates regime fit (0.80).",
        "agent_weights_applied": {"Signal": 0.75, "Risk": 0.5, "Context": 1.1},
        "memory_update_intent": "RSI<30 in ranging regime with news conflict → cautious long worked"
      }
    ]
    ```
    """

    result = validator.validate(sample_output)

    if result.valid:
        print("✅ Validation successful!")
        print(f"Remediation applied: {result.remediation_applied}")
        if result.agents:
            print(f"Parsed {len(result.agents)} agents")
    else:
        print("❌ Validation failed!")
        print(f"Errors: {result.errors}")
