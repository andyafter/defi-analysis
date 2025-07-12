"""Configuration management with validation and type safety."""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class TokenConfig:
    """Token configuration."""
    address: str
    symbol: str
    decimals: int


@dataclass
class PoolConfig:
    """Pool configuration."""
    address: str
    name: str
    fee_tier: int
    token0: TokenConfig
    token1: TokenConfig


@dataclass
class PositionConfig:
    """Position configuration."""
    tick_lower: int
    tick_upper: int


@dataclass
class AnalysisConfig:
    """Analysis parameters configuration."""
    start_block: int
    end_block: int
    initial_portfolio_value: float
    portfolio_split: float
    position: PositionConfig


@dataclass
class EthereumConfig:
    """Ethereum connection configuration."""
    rpc_url: str
    retry_attempts: int = 3
    timeout: int = 30


@dataclass
class OutputConfig:
    """Output configuration."""
    directory: str
    formats: list = field(default_factory=list)
    save_raw_data: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


@dataclass
class CacheConfig:
    """Cache configuration."""
    enabled: bool = True
    directory: str = "cache"
    ttl: int = 3600


@dataclass
class Config:
    """Main configuration container."""
    ethereum: EthereumConfig
    pools: Dict[str, PoolConfig]
    analysis: Dict[str, AnalysisConfig]
    output: OutputConfig
    logging: LoggingConfig
    cache: CacheConfig


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. Defaults to config.yaml
        """
        self.config_path = Path(config_path or "config.yaml")
        self._config_data: Optional[Dict[str, Any]] = None
        self._config: Optional[Config] = None
        self.logger = logging.getLogger(__name__)
    
    def load(self) -> Config:
        """Load and parse configuration.
        
        Returns:
            Parsed configuration object
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        if self._config:
            return self._config
            
        # Load YAML file
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            self._config_data = yaml.safe_load(f)
            
        # Substitute environment variables
        self._substitute_env_vars()
        
        # Parse configuration
        self._config = self._parse_config(self._config_data)
        
        # Setup logging
        self._setup_logging(self._config.logging)
        
        return self._config
    
    def _substitute_env_vars(self):
        """Substitute environment variables in config."""
        def _substitute(obj):
            if isinstance(obj, str):
                # Look for ${VAR_NAME} pattern
                pattern = r'\$\{([^}]+)\}'
                matches = re.findall(pattern, obj)
                for var_name in matches:
                    env_value = os.getenv(var_name)
                    if env_value is None:
                        raise ValueError(f"Environment variable {var_name} not set")
                    obj = obj.replace(f"${{{var_name}}}", env_value)
                return obj
            elif isinstance(obj, dict):
                return {k: _substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_substitute(item) for item in obj]
            return obj
        
        self._config_data = _substitute(self._config_data)
    
    def _parse_config(self, data: Dict[str, Any]) -> Config:
        """Parse raw config data into typed configuration.
        
        Args:
            data: Raw configuration dictionary
            
        Returns:
            Parsed Config object
        """
        # Parse Ethereum config
        eth_data = data.get('ethereum', {})
        ethereum_config = EthereumConfig(
            rpc_url=eth_data['rpc_url'],
            retry_attempts=eth_data.get('retry_attempts', 3),
            timeout=eth_data.get('timeout', 30)
        )
        
        # Parse pools
        pools = {}
        for pool_name, pool_data in data.get('pools', {}).items():
            token0_data = pool_data['token0']
            token1_data = pool_data['token1']
            
            pools[pool_name] = PoolConfig(
                address=pool_data['address'],
                name=pool_data['name'],
                fee_tier=pool_data['fee_tier'],
                token0=TokenConfig(**token0_data),
                token1=TokenConfig(**token1_data)
            )
        
        # Parse analysis configs
        analysis_configs = {}
        for analysis_name, analysis_data in data.get('analysis', {}).items():
            position_data = analysis_data['position']
            
            analysis_configs[analysis_name] = AnalysisConfig(
                start_block=analysis_data['start_block'],
                end_block=analysis_data['end_block'],
                initial_portfolio_value=analysis_data['initial_portfolio_value'],
                portfolio_split=analysis_data['portfolio_split'],
                position=PositionConfig(**position_data)
            )
        
        # Parse output config
        output_data = data.get('output', {})
        output_config = OutputConfig(
            directory=output_data.get('directory', 'output'),
            formats=output_data.get('formats', ['html', 'png']),
            save_raw_data=output_data.get('save_raw_data', True)
        )
        
        # Parse logging config
        logging_data = data.get('logging', {})
        logging_config = LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file=logging_data.get('file')
        )
        
        # Parse cache config
        cache_data = data.get('cache', {})
        cache_config = CacheConfig(
            enabled=cache_data.get('enabled', True),
            directory=cache_data.get('directory', 'cache'),
            ttl=cache_data.get('ttl', 3600)
        )
        
        return Config(
            ethereum=ethereum_config,
            pools=pools,
            analysis=analysis_configs,
            output=output_config,
            logging=logging_config,
            cache=cache_config
        )
    
    def _setup_logging(self, logging_config: LoggingConfig):
        """Setup logging based on configuration."""
        handlers = [logging.StreamHandler()]
        
        if logging_config.file:
            handlers.append(logging.FileHandler(logging_config.file))
        
        logging.basicConfig(
            level=getattr(logging, logging_config.level),
            format=logging_config.format,
            handlers=handlers
        )
    
    def get_pool_config(self, pool_id: str) -> PoolConfig:
        """Get pool configuration by ID.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Pool configuration
            
        Raises:
            KeyError: If pool not found
        """
        if not self._config:
            self.load()
        
        if pool_id not in self._config.pools:
            raise KeyError(f"Pool '{pool_id}' not found in configuration")
            
        return self._config.pools[pool_id]
    
    def get_analysis_config(self, analysis_id: str = "default") -> AnalysisConfig:
        """Get analysis configuration by ID.
        
        Args:
            analysis_id: Analysis identifier
            
        Returns:
            Analysis configuration
            
        Raises:
            KeyError: If analysis config not found
        """
        if not self._config:
            self.load()
        
        if analysis_id not in self._config.analysis:
            raise KeyError(f"Analysis config '{analysis_id}' not found")
            
        return self._config.analysis[analysis_id] 