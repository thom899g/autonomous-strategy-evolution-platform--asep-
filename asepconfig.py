"""
ASEP Configuration Management
Centralized configuration with environment-aware settings and validation.
"""
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import json
import logging
from pathlib import Path

# Firebase must be imported conditionally as it's not available in all environments
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase Admin SDK not available. Using local storage fallback.")

@dataclass
class ASEPConfig:
    """Main configuration container with validation and defaults."""
    
    # Genetic Algorithm Parameters
    population_size: int = 100
    generations: int = 50
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    elitism_count: int = 2
    tournament_size: int = 3
    
    # Reinforcement Learning Parameters
    rl_learning_rate: float = 0.001
    rl_discount_factor: float = 0.99
    rl_epsilon_start: float = 1.0
    rl_epsilon_end: float = 0.01
    rl_epsilon_decay: float = 0.995
    
    # Market Simulation Parameters
    initial_balance: float = 10000.0
    transaction_fee: float = 0.001  # 0.1%
    max_position_size: float = 0.1  # 10% of portfolio
    risk_free_rate: float = 0.02  # Annual risk-free rate
    
    # Evolution Loop Parameters
    evaluation_period_days: int = 30
    min_strategies_to_evolve: int = 10
    max_strategies_in_pool: int = 1000
    performance_threshold: float = 0.02  # 2% minimum Sharpe ratio
    
    # Firebase Configuration (Optional)
    firebase_config: Optional[Dict[str, Any]] = field(default_factory=lambda: {
        "credential_path": os.getenv("FIREBASE_CREDENTIAL_PATH", ""),
        "project_id": os.getenv("FIREBASE_PROJECT_ID", ""),
        "database_url": os.getenv("FIREBASE_DATABASE_URL", "")
    })
    
    # Data Configuration
    data_source: str = "ccxt"  # Options: ccxt, csv, api
    default_symbols: list = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    timeframe: str = "1h"
    max_data_points: int = 10000
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_parameters()
        
    def _validate_parameters(self):
        """Validate all configuration parameters with detailed error messages."""
        if self.population_size < 10:
            raise ValueError(f"Population size {self.population_size} too small. Minimum is 10.")
        if self.mutation_rate < 0 or self.mutation_rate > 1:
            raise ValueError(f"Mutation rate {self.mutation_rate} must be between 0 and 1.")
        if self.crossover_rate < 0 or self.crossover_rate > 1:
            raise ValueError(f"Crossover rate {self.crossover_rate} must be between 0 and 1.")
        if self.initial_balance <= 0:
            raise ValueError(f"Initial balance {self.initial_balance} must be positive.")
        if self.transaction_fee < 0 or self.transaction_fee > 0.1:
            raise ValueError(f"Transaction fee {self.transaction_fee} must be between 0 and 0.1 (10%).")
            
        # Validate Firebase config if provided
        if self.firebase_config and FIREBASE_AVAILABLE:
            if not self.firebase_config.get("project_id"):
                logging.warning("Firebase project_id not configured. Firebase features disabled.")
    
    @classmethod
    def from_env(cls) -> 'ASEPConfig':
        """Create configuration from environment variables with fallbacks."""
        return cls(
            population_size=int(os.getenv("ASEP_POPULATION_SIZE", "100")),
            mutation_rate=float(os.getenv("ASEP_MUTATION_RATE", "0.1")),
            initial_balance=float(os.getenv("ASEP_INITIAL_BALANCE", "10000.0")),
            # ... other parameters with env fallbacks
        )
    
    @classmethod
    def from_json(cls, config_path: str) -> 'ASEPConfig':
        """Load configuration from JSON file with validation."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            return cls(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except TypeError as e:
            raise ValueError(f"Invalid configuration parameters: {e}")

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure standardized logging for ASEP components."""
    logger = logging.getLogger("asep")
    
    if logger.hasHandlers():
        return logger
    
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # File handler (rotate logs)
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            "asep.log", maxBytes=10485760, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logging.warning(f"Could not set up file logging: {e}")
    
    logger.addHandler(console_handler)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    return logger

# Global configuration instance
_config_instance: Optional[ASEPConfig] = None

def get_config() -> ASEPConfig:
    """Get or create global configuration instance."""
    global _config_instance
    if _config_instance is None:
        # Try environment-based config first, then default
        try:
            _config_instance = ASEPConfig.from_env()
        except Exception as e:
            logging.warning(f"Failed to load env config: {e}. Using defaults.")