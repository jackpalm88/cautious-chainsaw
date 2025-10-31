"""
Confidence Calibration Framework

Monitors and corrects confidence score accuracy:
- Tracks predicted confidence vs actual win rate
- Applies Platt/Isotonic scaling for calibration
- Alerts on confidence drift
- Weekly recalibration jobs
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


@dataclass
class CalibrationSample:
    """Single decision for calibration analysis"""
    timestamp: datetime
    predicted_confidence: float  # What INoT said (0-1)
    actual_outcome: bool  # True=win, False=loss
    action: str  # BUY, SELL, HOLD
    pnl: float  # Profit/loss in pips


class ConfidenceCalibrator:
    """
    Monitors and calibrates INoT confidence scores.

    Problem: LLM confidence ≠ actual win rate
    - Model might output 0.7 confidence but actual win rate is 0.55
    - Or always outputs 0.6-0.8 (poor discrimination)

    Solution: Collect actual outcomes, apply calibration transform
    """

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.samples: list[CalibrationSample] = []

        # Calibration models
        self.platt_scaler = None  # Logistic regression
        self.isotonic_scaler = None  # Isotonic regression

        # Thresholds
        self.min_samples_for_calibration = 100
        self.calibration_tolerance = 0.10  # ±10% acceptable

        # Load existing samples
        self._load_samples()

    def record_decision(
        self,
        timestamp: datetime,
        predicted_confidence: float,
        action: str
    ) -> str:
        """
        Record new decision (outcome unknown yet).
        Returns tracking ID for later outcome update.
        """
        sample = CalibrationSample(
            timestamp=timestamp,
            predicted_confidence=predicted_confidence,
            actual_outcome=None,  # Filled in later
            action=action,
            pnl=None
        )

        self.samples.append(sample)
        self._save_samples()

        # Return ID for tracking
        return f"{timestamp.isoformat()}_{action}"

    def update_outcome(
        self,
        tracking_id: str,
        actual_outcome: bool,
        pnl: float
    ):
        """Update sample with actual outcome when position closes"""
        # Find sample by tracking ID
        timestamp_str, action = tracking_id.rsplit("_", 1)
        timestamp = datetime.fromisoformat(timestamp_str)

        for sample in self.samples:
            if (sample.timestamp == timestamp and
                sample.action == action and
                sample.actual_outcome is None):

                sample.actual_outcome = actual_outcome
                sample.pnl = pnl
                break

        self._save_samples()

    def analyze_calibration(self) -> dict:
        """
        Analyze current calibration quality.

        Returns metrics:
        - Overall accuracy (win rate)
        - Calibration error (ECE - Expected Calibration Error)
        - Per-decile analysis
        - Brier score
        """
        # Filter to samples with known outcomes
        completed = [s for s in self.samples if s.actual_outcome is not None]

        if len(completed) < 10:
            return {
                "status": "insufficient_data",
                "sample_count": len(completed),
                "message": f"Need {self.min_samples_for_calibration - len(completed)} more samples"
            }

        # Extract arrays
        confidences = np.array([s.predicted_confidence for s in completed])
        outcomes = np.array([1.0 if s.actual_outcome else 0.0 for s in completed])

        # Metrics
        overall_accuracy = outcomes.mean()

        # Expected Calibration Error (ECE)
        ece = self._compute_ece(confidences, outcomes, n_bins=10)

        # Brier score (lower is better)
        brier = np.mean((confidences - outcomes) ** 2)

        # Per-decile breakdown
        deciles = self._compute_decile_calibration(confidences, outcomes)

        # Check if recalibration needed
        needs_calibration = ece > self.calibration_tolerance

        return {
            "status": "analyzed",
            "sample_count": len(completed),
            "overall_accuracy": overall_accuracy,
            "ece": ece,
            "brier_score": brier,
            "deciles": deciles,
            "needs_calibration": needs_calibration,
            "calibration_threshold": self.calibration_tolerance
        }

    def calibrate(self, method: str = "isotonic") -> dict:
        """
        Train calibration model on collected samples.

        Methods:
        - "platt": Platt scaling (logistic regression)
        - "isotonic": Isotonic regression (non-parametric)

        Returns calibration performance metrics.
        """
        completed = [s for s in self.samples if s.actual_outcome is not None]

        if len(completed) < self.min_samples_for_calibration:
            return {
                "status": "insufficient_data",
                "message": f"Need {self.min_samples_for_calibration} samples, have {len(completed)}"
            }

        # Prepare data
        X = np.array([s.predicted_confidence for s in completed]).reshape(-1, 1)
        y = np.array([1 if s.actual_outcome else 0 for s in completed])

        # Train calibrator
        if method == "platt":
            self.platt_scaler = LogisticRegression()
            self.platt_scaler.fit(X, y)
            calibrated = self.platt_scaler.predict_proba(X)[:, 1]

        elif method == "isotonic":
            self.isotonic_scaler = IsotonicRegression(out_of_bounds='clip')
            self.isotonic_scaler.fit(X.ravel(), y)
            calibrated = self.isotonic_scaler.predict(X.ravel())

        else:
            raise ValueError(f"Unknown calibration method: {method}")

        # Evaluate calibration improvement
        ece_before = self._compute_ece(X.ravel(), y)
        ece_after = self._compute_ece(calibrated, y)

        improvement = ece_before - ece_after

        return {
            "status": "calibrated",
            "method": method,
            "samples": len(completed),
            "ece_before": ece_before,
            "ece_after": ece_after,
            "improvement": improvement,
            "timestamp": datetime.now().isoformat()
        }

    def apply_calibration(self, raw_confidence: float) -> float:
        """
        Apply trained calibration to new confidence score.

        Args:
            raw_confidence: Uncalibrated confidence from INoT

        Returns:
            Calibrated confidence (closer to true win probability)
        """
        if self.isotonic_scaler is not None:
            return float(self.isotonic_scaler.predict([raw_confidence])[0])

        elif self.platt_scaler is not None:
            return float(self.platt_scaler.predict_proba([[raw_confidence]])[0, 1])

        else:
            # No calibration trained yet
            return raw_confidence

    def _compute_ece(
        self,
        confidences: np.ndarray,
        outcomes: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """
        Compute Expected Calibration Error.

        ECE measures average absolute difference between confidence
        and actual accuracy across confidence bins.

        Perfect calibration: ECE = 0
        Poor calibration: ECE > 0.1
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0

        for i in range(n_bins):
            # Find samples in this confidence bin
            in_bin = (confidences >= bin_boundaries[i]) & \
                     (confidences < bin_boundaries[i + 1])

            if np.sum(in_bin) == 0:
                continue

            # Average confidence and accuracy in bin
            bin_confidence = confidences[in_bin].mean()
            bin_accuracy = outcomes[in_bin].mean()

            # Weighted contribution to ECE
            bin_weight = np.sum(in_bin) / len(confidences)
            ece += bin_weight * abs(bin_confidence - bin_accuracy)

        return ece

    def _compute_decile_calibration(
        self,
        confidences: np.ndarray,
        outcomes: np.ndarray
    ) -> list[dict]:
        """
        Compute calibration metrics per confidence decile.

        Returns list of decile stats for visualization.
        """
        deciles = []

        for i in range(10):
            lower = i / 10
            upper = (i + 1) / 10

            in_decile = (confidences >= lower) & (confidences < upper)

            if np.sum(in_decile) == 0:
                continue

            deciles.append({
                "decile": i + 1,
                "confidence_range": (lower, upper),
                "avg_confidence": confidences[in_decile].mean(),
                "actual_accuracy": outcomes[in_decile].mean(),
                "sample_count": int(np.sum(in_decile)),
                "calibration_error": abs(
                    confidences[in_decile].mean() - outcomes[in_decile].mean()
                )
            })

        return deciles

    def _load_samples(self):
        """Load existing calibration samples from disk"""
        if not self.storage_path.exists():
            return

        with open(self.storage_path) as f:
            data = json.load(f)

            for item in data:
                self.samples.append(CalibrationSample(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    predicted_confidence=item["predicted_confidence"],
                    actual_outcome=item.get("actual_outcome"),
                    action=item["action"],
                    pnl=item.get("pnl")
                ))

    def _save_samples(self):
        """Save calibration samples to disk"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = []
        for sample in self.samples:
            data.append({
                "timestamp": sample.timestamp.isoformat(),
                "predicted_confidence": sample.predicted_confidence,
                "actual_outcome": sample.actual_outcome,
                "action": sample.action,
                "pnl": sample.pnl
            })

        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)


# Weekly calibration job
def run_calibration_job(calibrator: ConfidenceCalibrator):
    """
    Weekly batch job to recalibrate confidence scores.

    Workflow:
    1. Analyze current calibration
    2. If ECE > threshold, retrain calibrator
    3. Alert if calibration degraded significantly
    """
    print("🔧 Running weekly calibration job...")

    # Analyze
    analysis = calibrator.analyze_calibration()

    print(f"Samples: {analysis.get('sample_count', 0)}")

    if analysis["status"] == "insufficient_data":
        print(analysis["message"])
        return

    print(f"Overall accuracy: {analysis['overall_accuracy']:.2%}")
    print(f"ECE: {analysis['ece']:.3f}")
    print(f"Brier score: {analysis['brier_score']:.3f}")

    # Calibrate if needed
    if analysis["needs_calibration"]:
        print("\n⚠️  Calibration error exceeds threshold!")
        print("Retraining calibrator...")

        result = calibrator.calibrate(method="isotonic")

        print("✅ Calibration complete")
        print(f"ECE improvement: {result['ece_before']:.3f} → {result['ece_after']:.3f}")
        print(f"Improvement: {result['improvement']:.3f}")

    else:
        print("\n✅ Calibration within acceptable range")

    # Decile breakdown
    print("\n📊 Decile Calibration:")
    for decile in analysis["deciles"]:
        print(
            f"  Decile {decile['decile']}: "
            f"Conf {decile['avg_confidence']:.2f} → "
            f"Actual {decile['actual_accuracy']:.2f} "
            f"(n={decile['sample_count']}, "
            f"error={decile['calibration_error']:.3f})"
        )


# Example usage
if __name__ == "__main__":
    calibrator = ConfidenceCalibrator(Path("data/calibration_samples.json"))

    # Simulate recording decisions
    for i in range(150):
        # Mock decisions with intentionally miscalibrated confidence
        # (Model overconfident)
        raw_conf = 0.7 + np.random.uniform(-0.1, 0.1)
        actual_outcome = np.random.random() < 0.55  # True win rate lower

        tracking_id = calibrator.record_decision(
            timestamp=datetime.now() - timedelta(days=150 - i),
            predicted_confidence=raw_conf,
            action="BUY"
        )

        # Update outcome
        calibrator.update_outcome(
            tracking_id=tracking_id,
            actual_outcome=actual_outcome,
            pnl=10.0 if actual_outcome else -10.0
        )

    # Run calibration job
    run_calibration_job(calibrator)

    # Test calibration
    print("\n🔬 Testing calibration effect:")
    for raw_conf in [0.5, 0.6, 0.7, 0.8, 0.9]:
        calibrated = calibrator.apply_calibration(raw_conf)
        print(f"  Raw {raw_conf:.2f} → Calibrated {calibrated:.2f}")
