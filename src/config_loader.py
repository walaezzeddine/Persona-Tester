import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml


class Config:
   
    
    def __init__(self, config_path: Optional[str] = None):
        
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            print(f"⚠ Config file not found: {self.config_path}")
            return self._default_config()
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration if file not found."""
        return {
            "llm": {
                "provider": "github",
                "model": "openai/gpt-4.1-mini",
                "temperature": 0.2,
                "max_tokens": 500,
                "base_url": "https://models.inference.ai.azure.com"
            },
            "navigation": {
                "max_steps": 15,
                "action_delay": 2,
                "action_timeout": 5000,
                "page_timeout": 30000,
                "page_content_limit": 1500
            },
            "browser": {
                "headless": False,
                "viewport": {"width": 1280, "height": 800},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            "logging": {
                "verbosity": "normal",
                "opentelemetry_enabled": False,
                "screenshots_enabled": False,
                "screenshots_dir": "screenshots"
            },
            "personas": {
                "parallel_count": 1,
                "history_limit": 10
            }
        }
    
    # ═══════════════════════════════════════════════════════════════
    # LLM Configuration
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def llm_provider(self) -> str:
        return self._config.get("llm", {}).get("provider", "github")
    
    @property
    def llm_model(self) -> str:
        return self._config.get("llm", {}).get("model", "gpt-4.1-mini")
    
    @property
    def llm_temperature(self) -> float:
        return self._config.get("llm", {}).get("temperature", 0.2)
    
    @property
    def llm_max_tokens(self) -> int:
        return self._config.get("llm", {}).get("max_tokens", 500)
    
    @property
    def llm_base_url(self) -> str:
        return self._config.get("llm", {}).get("base_url", "https://models.inference.ai.azure.com")
    
    # ═══════════════════════════════════════════════════════════════
    # Navigation Configuration
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def max_steps(self) -> int:
        return self._config.get("navigation", {}).get("max_steps", 15)
    
    @property
    def action_delay(self) -> int:
        return self._config.get("navigation", {}).get("action_delay", 2)
    
    @property
    def action_timeout(self) -> int:
        return self._config.get("navigation", {}).get("action_timeout", 5000)
    
    @property
    def page_timeout(self) -> int:
        return self._config.get("navigation", {}).get("page_timeout", 30000)
    
    @property
    def page_content_limit(self) -> int:
        return self._config.get("navigation", {}).get("page_content_limit", 1500)
    
    # ═══════════════════════════════════════════════════════════════
    # Browser Configuration
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def headless(self) -> bool:
        return self._config.get("browser", {}).get("headless", False)
    
    @property
    def viewport(self) -> Dict[str, int]:
        return self._config.get("browser", {}).get("viewport", {"width": 1280, "height": 800})
    
    @property
    def user_agent(self) -> str:
        return self._config.get("browser", {}).get("user_agent", "Mozilla/5.0")
    
    # ═══════════════════════════════════════════════════════════════
    # Logging Configuration
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def verbosity(self) -> str:
        return self._config.get("logging", {}).get("verbosity", "normal")
    
    @property
    def opentelemetry_enabled(self) -> bool:
        return self._config.get("logging", {}).get("opentelemetry_enabled", False)
    
    @property
    def screenshots_enabled(self) -> bool:
        return self._config.get("logging", {}).get("screenshots_enabled", False)
    
    @property
    def screenshots_dir(self) -> str:
        return self._config.get("logging", {}).get("screenshots_dir", "screenshots")
    
    # ═══════════════════════════════════════════════════════════════
    # Personas Configuration
    # ═══════════════════════════════════════════════════════════════
    
    @property
    def parallel_count(self) -> int:
        return self._config.get("personas", {}).get("parallel_count", 1)
    
    @property
    def history_limit(self) -> int:
        return self._config.get("personas", {}).get("history_limit", 10)
    
    @property
    def persona_file(self) -> str:
        return self._config.get("persona", {}).get("file", "acheteur_prudent")


def load_scenario(scenario_path: str) -> Dict[str, Any]:
    """
    Load a scenario from YAML file.
    
    Args:
        scenario_path: Path to scenario YAML file
        
    Returns:
        Dictionary containing scenario configuration
    """
    with open(scenario_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_persona(persona_path: str) -> Dict[str, Any]:
    """
    Load a persona from JSON file.
    
    Args:
        persona_path: Path to persona JSON file
        
    Returns:
        Dictionary containing persona attributes
    """
    import json
    with open(persona_path, 'r', encoding='utf-8') as f:
        return json.load(f)
