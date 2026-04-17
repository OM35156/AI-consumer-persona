"""匿名化パイプライン — k-匿名性の確認とセル抑制."""

import hashlib
from collections import Counter
from dataclasses import dataclass

from digital_twin.data.schema import Consumer


@dataclass
class AnonymizationReport:
    """匿名化結果レポート."""

    total_consumers: int
    suppressed_consumers: int
    k_anonymity_achieved: int
    demographic_groups: int
    smallest_group_size: int
    warnings: list[str]

    @property
    def is_safe(self) -> bool:
        return self.k_anonymity_achieved >= 5 and self.suppressed_consumers == 0


def _demographic_key(c: Consumer) -> tuple:
    """k-匿名性判定用の quasi-identifier タプル.

    生活者版では age_group × gender × region × life_stage を準識別子とする。
    """
    return (
        c.demographics.age_group.value,
        c.demographics.gender.value,
        c.demographics.region.value,
        c.demographics.life_stage.value,
    )


def check_k_anonymity(
    consumers: list[Consumer],
    k: int = 5,
) -> AnonymizationReport:
    """k-匿名性を確認する."""
    groups = Counter(_demographic_key(c) for c in consumers)
    smallest = min(groups.values()) if groups else 0
    violations = {key: count for key, count in groups.items() if count < k}

    warnings = [
        f"k-anonymity violation: group {key} has only {count} (need {k})"
        for key, count in violations.items()
    ]

    return AnonymizationReport(
        total_consumers=len(consumers),
        suppressed_consumers=0,
        k_anonymity_achieved=smallest,
        demographic_groups=len(groups),
        smallest_group_size=smallest,
        warnings=warnings,
    )


def enforce_k_anonymity(
    consumers: list[Consumer],
    k: int = 5,
) -> tuple[list[Consumer], AnonymizationReport]:
    """k 未満のグループを抑制する."""
    groups = Counter(_demographic_key(c) for c in consumers)
    safe_keys = {key for key, count in groups.items() if count >= k}

    safe = [c for c in consumers if _demographic_key(c) in safe_keys]
    suppressed = len(consumers) - len(safe)

    report = check_k_anonymity(safe, k)
    report.suppressed_consumers = suppressed

    if suppressed > 0:
        report.warnings.append(f"Suppressed {suppressed} consumers from small groups")

    return safe, report


def strip_pii(consumer: Consumer) -> Consumer:
    """consumer_id をハッシュ化した匿名 ID に置換する."""
    hashed_id = hashlib.sha256(consumer.consumer_id.encode()).hexdigest()[:12]
    return consumer.model_copy(update={"consumer_id": f"ANON_{hashed_id}"})


def anonymize_dataset(
    consumers: list[Consumer],
    k: int = 5,
) -> tuple[list[Consumer], AnonymizationReport]:
    """PII 除去 + k-匿名性抑制を適用する."""
    stripped = [strip_pii(c) for c in consumers]
    safe, report = enforce_k_anonymity(stripped, k)
    return safe, report
