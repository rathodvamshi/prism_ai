"""
🎚️ ADAPTIVE QUALITY SERVICE - Smart Load Shedding

Automatically adjusts model parameters based on:
1. System load (active generations, queue depth)
2. Client responsiveness (slow readers)
3. Model performance (recent latencies)

Strategy: Users prefer FAST GOOD over SLOW PERFECT.
"""

import time
import asyncio
from typing import Dict, Optional, Literal, Tuple
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# QUALITY PRESETS - Tuned for different load conditions
# ============================================================================

@dataclass
class QualityPreset:
    """Model parameters for a quality tier"""
    name: str
    temperature: float
    top_p: float
    max_tokens: int
    description: str
    
    def to_dict(self) -> Dict:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens
        }


# Quality tiers from highest to lowest
QUALITY_PRESETS = {
    "premium": QualityPreset(
        name="premium",
        temperature=0.7,
        top_p=0.9,
        max_tokens=1500,
        description="Full quality - rich, detailed responses"
    ),
    "standard": QualityPreset(
        name="standard", 
        temperature=0.5,
        top_p=0.85,
        max_tokens=800,
        description="Balanced - good quality, faster responses"
    ),
    "fast": QualityPreset(
        name="fast",
        temperature=0.3,
        top_p=0.7,
        max_tokens=512,
        description="Speed priority - concise, quick responses"
    ),
    "turbo": QualityPreset(
        name="turbo",
        temperature=0.2,
        top_p=0.6,
        max_tokens=300,
        description="Maximum speed - minimal latency"
    )
}


# ============================================================================
# LOAD METRICS TRACKER
# ============================================================================

@dataclass
class LoadMetrics:
    """Real-time system load metrics"""
    active_generations: int = 0
    queue_depth: int = 0
    avg_latency_ms: float = 0.0
    slow_clients: int = 0
    error_rate: float = 0.0
    last_updated: float = field(default_factory=time.time)
    
    # Rolling windows for calculations
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=50))
    error_samples: deque = field(default_factory=lambda: deque(maxlen=100))


class AdaptiveQualityService:
    """
    🎚️ Intelligent quality adjustment based on system conditions.
    
    Monitors:
    - Active generation count
    - Client read speed (slow readers)
    - Recent latency trends
    - Error rates
    
    Outputs:
    - Recommended quality preset
    - Adjusted model parameters
    """
    
    def __init__(self):
        self.metrics = LoadMetrics()
        self._lock = asyncio.Lock()
        
        # Thresholds for quality degradation
        self.thresholds = {
            "premium": {  # Use premium when:
                "max_active_gens": 5,
                "max_avg_latency_ms": 500,
                "max_error_rate": 0.01
            },
            "standard": {  # Degrade to standard when:
                "max_active_gens": 15,
                "max_avg_latency_ms": 1500,
                "max_error_rate": 0.05
            },
            "fast": {  # Degrade to fast when:
                "max_active_gens": 30,
                "max_avg_latency_ms": 3000,
                "max_error_rate": 0.10
            }
            # Beyond these = turbo mode
        }
        
        # Per-user slow client tracking
        self._slow_clients: Dict[str, float] = {}  # user_id -> last_slow_time
        self._slow_client_ttl = 60.0  # Forget slow status after 60s
        
        logger.info("🎚️ Adaptive Quality Service initialized")
    
    # ========================================================================
    # METRICS COLLECTION
    # ========================================================================
    
    async def record_generation_start(self):
        """Called when a new generation starts"""
        async with self._lock:
            self.metrics.active_generations += 1
            self.metrics.last_updated = time.time()
    
    async def record_generation_end(self, latency_ms: float, success: bool = True):
        """Called when a generation completes"""
        async with self._lock:
            self.metrics.active_generations = max(0, self.metrics.active_generations - 1)
            self.metrics.latency_samples.append(latency_ms)
            self.metrics.error_samples.append(0 if success else 1)
            
            # Update rolling averages
            if self.metrics.latency_samples:
                self.metrics.avg_latency_ms = sum(self.metrics.latency_samples) / len(self.metrics.latency_samples)
            if self.metrics.error_samples:
                self.metrics.error_rate = sum(self.metrics.error_samples) / len(self.metrics.error_samples)
            
            self.metrics.last_updated = time.time()
    
    async def record_slow_client(self, user_id: str):
        """Called when a client is reading slowly (backpressure detected)"""
        async with self._lock:
            self._slow_clients[user_id] = time.time()
            self.metrics.slow_clients = len(self._slow_clients)
    
    async def record_client_recovered(self, user_id: str):
        """Called when a slow client catches up"""
        async with self._lock:
            self._slow_clients.pop(user_id, None)
            self.metrics.slow_clients = len(self._slow_clients)
    
    def _cleanup_stale_slow_clients(self):
        """Remove stale slow client entries"""
        now = time.time()
        stale = [uid for uid, ts in self._slow_clients.items() if now - ts > self._slow_client_ttl]
        for uid in stale:
            self._slow_clients.pop(uid, None)
        self.metrics.slow_clients = len(self._slow_clients)
    
    # ========================================================================
    # QUALITY DETERMINATION
    # ========================================================================
    
    def _calculate_load_score(self) -> float:
        """
        Calculate overall load score (0.0 = idle, 1.0+ = overloaded)
        """
        # Weighted factors
        gen_score = self.metrics.active_generations / 10.0  # 10 gens = score 1.0
        latency_score = self.metrics.avg_latency_ms / 2000.0  # 2000ms = score 1.0
        error_score = self.metrics.error_rate * 10  # 10% errors = score 1.0
        slow_client_score = self.metrics.slow_clients / 5.0  # 5 slow clients = score 1.0
        
        # Combined weighted score
        total_score = (
            gen_score * 0.4 +      # Active generations most important
            latency_score * 0.3 +  # Latency trends
            error_score * 0.2 +    # Error rate
            slow_client_score * 0.1  # Slow clients
        )
        
        return total_score
    
    def get_recommended_preset(self, user_id: Optional[str] = None) -> QualityPreset:
        """
        Get recommended quality preset based on current conditions.
        
        Args:
            user_id: Optional user ID to check for slow client status
            
        Returns:
            QualityPreset with recommended parameters
        """
        self._cleanup_stale_slow_clients()
        
        load_score = self._calculate_load_score()
        
        # Check if this specific user is a slow client
        is_slow_client = user_id and user_id in self._slow_clients
        
        # Determine quality tier
        if is_slow_client:
            # Slow clients always get turbo mode
            preset = QUALITY_PRESETS["turbo"]
            reason = "slow_client"
        elif load_score < 0.3:
            preset = QUALITY_PRESETS["premium"]
            reason = "low_load"
        elif load_score < 0.6:
            preset = QUALITY_PRESETS["standard"]
            reason = "moderate_load"
        elif load_score < 0.9:
            preset = QUALITY_PRESETS["fast"]
            reason = "high_load"
        else:
            preset = QUALITY_PRESETS["turbo"]
            reason = "overloaded"
        
        logger.debug(
            f"🎚️ Quality: {preset.name} (score={load_score:.2f}, reason={reason}, "
            f"active={self.metrics.active_generations}, latency={self.metrics.avg_latency_ms:.0f}ms)"
        )
        
        return preset
    
    def get_adaptive_params(
        self, 
        user_id: Optional[str] = None,
        base_max_tokens: Optional[int] = None,
        force_quality: Optional[Literal["premium", "standard", "fast", "turbo"]] = None
    ) -> Dict:
        """
        Get adaptive model parameters.
        
        Args:
            user_id: Optional user ID for per-user adjustments
            base_max_tokens: Optional base max_tokens to scale from
            force_quality: Force a specific quality level (overrides auto)
            
        Returns:
            Dict with temperature, top_p, max_tokens
        """
        if force_quality:
            preset = QUALITY_PRESETS.get(force_quality, QUALITY_PRESETS["standard"])
        else:
            preset = self.get_recommended_preset(user_id)
        
        params = preset.to_dict()
        
        # Scale max_tokens if base provided
        if base_max_tokens:
            # Scale proportionally to preset's ratio vs premium
            premium_tokens = QUALITY_PRESETS["premium"].max_tokens
            scale_factor = preset.max_tokens / premium_tokens
            params["max_tokens"] = min(int(base_max_tokens * scale_factor), preset.max_tokens)
        
        return params
    
    # ========================================================================
    # STATUS & DEBUGGING
    # ========================================================================
    
    def get_status(self) -> Dict:
        """Get current service status for monitoring"""
        self._cleanup_stale_slow_clients()
        load_score = self._calculate_load_score()
        preset = self.get_recommended_preset()
        
        return {
            "load_score": round(load_score, 3),
            "recommended_quality": preset.name,
            "metrics": {
                "active_generations": self.metrics.active_generations,
                "avg_latency_ms": round(self.metrics.avg_latency_ms, 1),
                "error_rate": round(self.metrics.error_rate, 4),
                "slow_clients": self.metrics.slow_clients
            },
            "thresholds": self.thresholds,
            "presets": {name: p.to_dict() for name, p in QUALITY_PRESETS.items()}
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

adaptive_quality = AdaptiveQualityService()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def get_adaptive_model_params(
    user_id: Optional[str] = None,
    prompt_length: Optional[int] = None
) -> Tuple[Dict, str]:
    """
    Quick helper to get adaptive parameters.
    
    Returns:
        Tuple of (params_dict, quality_tier_name)
    """
    preset = adaptive_quality.get_recommended_preset(user_id)
    params = preset.to_dict()
    
    # Additional adjustment based on prompt length
    if prompt_length:
        if prompt_length < 50:
            # Short prompts = shorter responses
            params["max_tokens"] = min(params["max_tokens"], 400)
        elif prompt_length > 500:
            # Long prompts might need longer responses
            params["max_tokens"] = min(int(params["max_tokens"] * 1.2), 2000)
    
    return params, preset.name


def record_generation_metrics(latency_ms: float, success: bool = True):
    """Fire-and-forget metric recording"""
    asyncio.create_task(adaptive_quality.record_generation_end(latency_ms, success))


def record_generation_start():
    """Fire-and-forget generation start"""
    asyncio.create_task(adaptive_quality.record_generation_start())
