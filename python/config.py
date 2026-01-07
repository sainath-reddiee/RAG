"""
Configuration Management Module

Purpose:
- Load and validate configuration from config.yaml or environment variables
- Provide typed access to configuration values
- Handle missing or invalid configuration gracefully
- Support .env files for secure credential storage

Design Decisions:
- Singleton pattern: Configuration loaded once and reused
- Fail-fast: Invalid configuration raises exceptions at startup
- Type safety: Use dataclasses for structured configuration
- Security: Support environment variables for credentials
"""

import os
import yaml
from typing import Dict, Any, List
from dataclasses import dataclass
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration"""
    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: str = None


@dataclass
class RetrievalConfig:
    """Retrieval configuration (Cortex Search Service)"""
    top_k: int = 5


@dataclass
class GenerationConfig:
    """Text generation configuration"""
    model: str = "mistral-large"
    max_tokens: int = 512
    temperature: float = 0.1


@dataclass
class UploadConfig:
    """File upload configuration"""
    max_file_size_mb: int = 10
    allowed_extensions: List[str] = None
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = [".txt"]


@dataclass
class RetryConfig:
    """Retry logic configuration"""
    max_attempts: int = 3
    backoff_factor: int = 2
    initial_delay: int = 1


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class AppConfig:
    """Application configuration"""
    retrieval: RetrievalConfig
    generation: GenerationConfig
    upload: UploadConfig
    retry: RetryConfig
    logging: LoggingConfig


@dataclass
class Config:
    """Root configuration object"""
    snowflake: SnowflakeConfig
    app: AppConfig


class ConfigLoader:
    """
    Configuration loader with singleton pattern.
    
    Why singleton?
    - Configuration is loaded once at startup
    - Prevents multiple file reads
    - Ensures consistency across the application
    """
    
    _instance = None
    _config: Config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def load(self, config_path: str = "config.yaml") -> Config:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to config.yaml file
            
        Returns:
            Config object
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        if self._config is not None:
            return self._config
        
        # Check if config file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                f"Please copy config.yaml.template to config.yaml and fill in your credentials."
            )
        
        # Load YAML
        try:
            with open(config_path, 'r') as f:
                config_dict = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
        
        # Validate and parse configuration
        try:
            # Load Snowflake config with environment variable fallback
            sf_dict = config_dict.get('snowflake', {})
            snowflake_config = SnowflakeConfig(
                account=sf_dict.get('account') or os.getenv('SNOWFLAKE_ACCOUNT', ''),
                user=sf_dict.get('user') or os.getenv('SNOWFLAKE_USER', ''),
                password=sf_dict.get('password') or os.getenv('SNOWFLAKE_PASSWORD', ''),
                warehouse=sf_dict.get('warehouse') or os.getenv('SNOWFLAKE_WAREHOUSE', ''),
                database=sf_dict.get('database') or os.getenv('SNOWFLAKE_DATABASE', ''),
                schema=sf_dict.get('schema') or os.getenv('SNOWFLAKE_SCHEMA', ''),
                role=sf_dict.get('role') or os.getenv('SNOWFLAKE_ROLE')
            )
            
            # Validate required fields
            if not all([snowflake_config.account, snowflake_config.user, 
                       snowflake_config.password, snowflake_config.warehouse,
                       snowflake_config.database, snowflake_config.schema]):
                raise ValueError(
                    "Missing required Snowflake credentials. "
                    "Provide them in config.yaml or set environment variables:\n"
                    "SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, "
                    "SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA"
                )
            
            app_dict = config_dict['app']
            app_config = AppConfig(
                retrieval=RetrievalConfig(**app_dict.get('retrieval', {})),
                generation=GenerationConfig(**app_dict.get('generation', {})),
                upload=UploadConfig(**app_dict.get('upload', {})),
                retry=RetryConfig(**app_dict.get('retry', {})),
                logging=LoggingConfig(**app_dict.get('logging', {}))
            )
            
            self._config = Config(snowflake=snowflake_config, app=app_config)
            
            # Configure logging
            logging.basicConfig(
                level=getattr(logging, app_config.logging.level),
                format=app_config.logging.format
            )
            
            logger.info("Configuration loaded successfully")
            return self._config
            
        except KeyError as e:
            raise ValueError(f"Missing required configuration key: {e}")
        except TypeError as e:
            raise ValueError(f"Invalid configuration value: {e}")
    
    def get_config(self) -> Config:
        """
        Get the loaded configuration.
        
        Returns:
            Config object
            
        Raises:
            RuntimeError: If configuration hasn't been loaded yet
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config


# Convenience function for getting configuration
def get_config() -> Config:
    """
    Get the application configuration.
    
    Returns:
        Config object
        
    Usage:
        from python.config import get_config
        config = get_config()
        print(config.snowflake.account)
    """
    loader = ConfigLoader()
    try:
        return loader.get_config()
    except RuntimeError:
        # Auto-load if not loaded yet
        return loader.load()
