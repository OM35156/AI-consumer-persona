"""Configuration loader using OmegaConf."""

from pathlib import Path

from omegaconf import OmegaConf, DictConfig


_CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs"


def load_config(profile: str = "poc") -> DictConfig:
    """Load configuration with base + profile overlay.

    Args:
        profile: Configuration profile name (e.g., "poc", "prod").

    Returns:
        Merged configuration.
    """
    base = OmegaConf.load(_CONFIG_DIR / "base.yaml")
    profile_path = _CONFIG_DIR / f"{profile}.yaml"
    if profile_path.exists():
        overlay = OmegaConf.load(profile_path)
        return OmegaConf.merge(base, overlay)
    return base
