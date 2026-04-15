"""De-identification and anonymization pipeline for physician data."""

import hashlib
from collections import Counter
from dataclasses import dataclass

from digital_twin.data.schema import Physician


@dataclass
class AnonymizationReport:
    total_physicians: int
    suppressed_physicians: int
    k_anonymity_achieved: int
    demographic_groups: int
    smallest_group_size: int
    warnings: list[str]

    @property
    def is_safe(self) -> bool:
        return self.k_anonymity_achieved >= 5 and self.suppressed_physicians == 0


def _demographic_key(p: Physician) -> tuple:
    """Quasi-identifier tuple for k-anonymity."""
    return (
        p.demographics.age_group.value,
        p.demographics.gender.value,
        p.demographics.region.value,
        p.demographics.specialty.value,
    )


def check_k_anonymity(
    physicians: list[Physician],
    k: int = 5,
) -> AnonymizationReport:
    groups = Counter(_demographic_key(p) for p in physicians)
    smallest = min(groups.values()) if groups else 0
    violations = {key: count for key, count in groups.items() if count < k}

    warnings = [
        f"k-anonymity violation: group {key} has only {count} (need {k})"
        for key, count in violations.items()
    ]

    return AnonymizationReport(
        total_physicians=len(physicians),
        suppressed_physicians=0,
        k_anonymity_achieved=smallest,
        demographic_groups=len(groups),
        smallest_group_size=smallest,
        warnings=warnings,
    )


def enforce_k_anonymity(
    physicians: list[Physician],
    k: int = 5,
) -> tuple[list[Physician], AnonymizationReport]:
    groups = Counter(_demographic_key(p) for p in physicians)
    safe_keys = {key for key, count in groups.items() if count >= k}

    safe = [p for p in physicians if _demographic_key(p) in safe_keys]
    suppressed = len(physicians) - len(safe)

    report = check_k_anonymity(safe, k)
    report.suppressed_physicians = suppressed

    if suppressed > 0:
        report.warnings.append(f"Suppressed {suppressed} physicians from small groups")

    return safe, report


def strip_pii(physician: Physician) -> Physician:
    hashed_id = hashlib.sha256(physician.physician_id.encode()).hexdigest()[:12]
    return physician.model_copy(update={"physician_id": f"ANON_{hashed_id}"})


def anonymize_dataset(
    physicians: list[Physician],
    k: int = 5,
) -> tuple[list[Physician], AnonymizationReport]:
    stripped = [strip_pii(p) for p in physicians]
    safe, report = enforce_k_anonymity(stripped, k)
    return safe, report
