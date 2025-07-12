"""Core interfaces for the analysis framework."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PoolState:
    """Generic pool state representation."""
    pool_address: str
    block_number: int
    timestamp: Optional[datetime] = None
    data: Dict[str, Any] = None


@dataclass
class Position:
    """Generic position representation."""
    pool_address: str
    owner: Optional[str] = None
    data: Dict[str, Any] = None


@dataclass
class SwapEvent:
    """Generic swap event representation."""
    pool_address: str
    block_number: int
    transaction_hash: str
    sender: str
    recipient: str
    data: Dict[str, Any] = None


@dataclass
class AnalysisResult:
    """Generic analysis result container."""
    position: Position
    metrics: Dict[str, float]
    data: Dict[str, Any] = None
    metadata: Dict[str, Any] = None


class IDataProvider(ABC):
    """Interface for blockchain data providers."""
    
    @abstractmethod
    async def get_pool_state(self, pool_address: str, block_number: int) -> PoolState:
        """Fetch pool state at specific block."""
        pass
    
    @abstractmethod
    async def get_swap_events(
        self, 
        pool_address: str, 
        start_block: int, 
        end_block: int
    ) -> List[SwapEvent]:
        """Fetch swap events between blocks."""
        pass
    
    @abstractmethod
    async def get_block_timestamp(self, block_number: int) -> datetime:
        """Get timestamp for a block."""
        pass


class ILiquidityCalculator(ABC):
    """Interface for liquidity calculations."""
    
    @abstractmethod
    def calculate_position(
        self,
        pool_state: PoolState,
        amount0: float,
        amount1: float,
        tick_lower: int,
        tick_upper: int
    ) -> Position:
        """Calculate liquidity position."""
        pass
    
    @abstractmethod
    def get_position_amounts(
        self,
        position: Position,
        pool_state: PoolState
    ) -> Tuple[float, float]:
        """Get current token amounts for position."""
        pass


class IAnalysisStrategy(ABC):
    """Interface for analysis strategies."""
    
    @abstractmethod
    async def analyze(
        self,
        position: Position,
        start_state: PoolState,
        end_state: PoolState,
        events: List[SwapEvent],
        **kwargs
    ) -> AnalysisResult:
        """Perform analysis on position."""
        pass
    
    @abstractmethod
    def get_required_metrics(self) -> List[str]:
        """Get list of metrics this strategy calculates."""
        pass


class IVisualizationRenderer(ABC):
    """Interface for visualization rendering."""
    
    @abstractmethod
    def render(
        self,
        analysis_result: AnalysisResult,
        output_path: str,
        **kwargs
    ) -> str:
        """Render visualization to file."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        pass


class ICacheProvider(ABC):
    """Interface for caching providers."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str):
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear(self):
        """Clear all cache entries."""
        pass 