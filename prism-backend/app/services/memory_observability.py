"""
📊 MEMORY OBSERVABILITY - Logging, Metrics & Debugging
======================================================

This module provides comprehensive observability for the memory system
without exposing sensitive user data.

Key Features:
- Structured logging for memory operations
- Metrics tracking (latency, success rates, etc.)
- Debugging tools for memory inspection
- Audit trail for compliance
- Health checks and diagnostics

Usage:
    from app.services.memory_observability import MemoryObserver, memory_observer
    
    # Log memory operation
    memory_observer.log_operation("store", user_hash, success=True, latency_ms=45)
    
    # Get metrics
    metrics = memory_observer.get_metrics()
"""

import logging
import hashlib
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Memory operation types for tracking"""
    STORE = "store"
    FETCH = "fetch"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    MERGE = "merge"
    DEDUPE = "dedupe"
    VALIDATE = "validate"


class MetricType(Enum):
    """Types of metrics to track"""
    LATENCY = "latency"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    CACHE_HIT = "cache_hit"
    DUPLICATE_RATE = "duplicate_rate"


@dataclass
class OperationMetrics:
    """Metrics for a single operation type"""
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0
    latencies_ms: List[float] = field(default_factory=list)
    last_operation: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count
    
    @property
    def error_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.error_count / self.total_count
    
    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.mean(self.latencies_ms)
    
    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.median(self.latencies_ms)
    
    @property
    def p99_latency_ms(self) -> float:
        if len(self.latencies_ms) < 2:
            return self.avg_latency_ms
        sorted_latencies = sorted(self.latencies_ms)
        idx = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]


@dataclass
class AuditEntry:
    """Audit log entry for compliance"""
    timestamp: datetime
    operation: str
    user_hash: str  # Hashed user_id for privacy
    success: bool
    latency_ms: float
    details: Dict[str, Any]


class MemoryObserver:
    """
    📊 MEMORY OBSERVABILITY SYSTEM
    
    Provides comprehensive monitoring and debugging for the memory system.
    All user data is hashed/anonymized in logs for privacy.
    """
    
    def __init__(self, max_audit_entries: int = 10000, max_latency_samples: int = 1000):
        # Metrics storage
        self._metrics: Dict[OperationType, OperationMetrics] = {
            op: OperationMetrics() for op in OperationType
        }
        
        # Per-backend metrics
        self._backend_metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        
        # Audit log (ring buffer)
        self._audit_log: List[AuditEntry] = []
        self._max_audit_entries = max_audit_entries
        self._max_latency_samples = max_latency_samples
        
        # Error tracking
        self._recent_errors: List[Dict[str, Any]] = []
        self._max_errors = 100
        
        # Custom alert callbacks
        self._alert_callbacks: List[Callable] = []
        
        # Thresholds for alerts
        self.ALERT_THRESHOLDS = {
            "error_rate": 0.10,          # Alert if > 10% errors
            "latency_p99_ms": 500,       # Alert if p99 > 500ms
            "consecutive_errors": 5,      # Alert after 5 consecutive errors
        }
        
        self._consecutive_errors = 0
        self._initialized_at = datetime.utcnow()
        
        logger.info("📊 MemoryObserver initialized")
    
    def _hash_user_id(self, user_id: str) -> str:
        """Hash user_id for privacy in logs"""
        if not user_id:
            return "anonymous"
        return hashlib.sha256(user_id.encode()).hexdigest()[:12]
    
    def log_operation(
        self,
        operation: OperationType,
        user_id: str,
        success: bool,
        latency_ms: float,
        backend: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a memory operation with metrics
        
        Args:
            operation: Type of operation
            user_id: User ID (will be hashed)
            success: Whether operation succeeded
            latency_ms: Operation latency in milliseconds
            backend: Storage backend used (redis, mongodb, neo4j, pinecone)
            details: Additional details (sensitive data will be filtered)
        """
        user_hash = self._hash_user_id(user_id)
        now = datetime.utcnow()
        
        # Update operation metrics
        metrics = self._metrics[operation]
        metrics.total_count += 1
        metrics.last_operation = now
        
        if success:
            metrics.success_count += 1
            self._consecutive_errors = 0
        else:
            metrics.error_count += 1
            self._consecutive_errors += 1
        
        # Track latency (keep recent samples only)
        metrics.latencies_ms.append(latency_ms)
        if len(metrics.latencies_ms) > self._max_latency_samples:
            metrics.latencies_ms = metrics.latencies_ms[-self._max_latency_samples:]
        
        # Update backend metrics if specified
        if backend:
            backend_metrics = self._backend_metrics[backend]
            backend_metrics.total_count += 1
            backend_metrics.last_operation = now
            if success:
                backend_metrics.success_count += 1
            else:
                backend_metrics.error_count += 1
            backend_metrics.latencies_ms.append(latency_ms)
            if len(backend_metrics.latencies_ms) > self._max_latency_samples:
                backend_metrics.latencies_ms = backend_metrics.latencies_ms[-self._max_latency_samples:]
        
        # Create audit entry (filter sensitive data)
        safe_details = self._filter_sensitive_data(details or {})
        audit_entry = AuditEntry(
            timestamp=now,
            operation=operation.value,
            user_hash=user_hash,
            success=success,
            latency_ms=latency_ms,
            details=safe_details
        )
        
        # Add to audit log (ring buffer)
        self._audit_log.append(audit_entry)
        if len(self._audit_log) > self._max_audit_entries:
            self._audit_log = self._audit_log[-self._max_audit_entries:]
        
        # Log error details
        if not success:
            self._log_error(operation, user_hash, latency_ms, safe_details)
        
        # Check alert thresholds
        self._check_alerts(operation, metrics)
        
        # Structured logging
        log_level = logging.DEBUG if success else logging.WARNING
        logger.log(
            log_level,
            f"{'✅' if success else '❌'} Memory {operation.value}: "
            f"user={user_hash}, latency={latency_ms:.1f}ms, "
            f"backend={backend or 'default'}"
        )
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive data from details dict"""
        sensitive_keys = {
            "user_id", "email", "password", "token", "secret", "key",
            "phone", "address", "ssn", "credit_card", "content", "text",
            "message", "response"
        }
        
        filtered = {}
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                filtered[key] = "[REDACTED]"
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive_data(value)
            elif isinstance(value, str) and len(value) > 100:
                filtered[key] = f"{value[:50]}... [TRUNCATED]"
            else:
                filtered[key] = value
        
        return filtered
    
    def _log_error(
        self,
        operation: OperationType,
        user_hash: str,
        latency_ms: float,
        details: Dict[str, Any]
    ):
        """Track error for debugging"""
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation.value,
            "user_hash": user_hash,
            "latency_ms": latency_ms,
            "details": details
        }
        
        self._recent_errors.append(error_entry)
        if len(self._recent_errors) > self._max_errors:
            self._recent_errors = self._recent_errors[-self._max_errors:]
    
    def _check_alerts(self, operation: OperationType, metrics: OperationMetrics):
        """Check if any alert thresholds are exceeded"""
        alerts = []
        
        # Error rate alert
        if metrics.total_count >= 10 and metrics.error_rate > self.ALERT_THRESHOLDS["error_rate"]:
            alerts.append({
                "type": "high_error_rate",
                "operation": operation.value,
                "error_rate": metrics.error_rate,
                "threshold": self.ALERT_THRESHOLDS["error_rate"]
            })
        
        # Latency alert
        if metrics.p99_latency_ms > self.ALERT_THRESHOLDS["latency_p99_ms"]:
            alerts.append({
                "type": "high_latency",
                "operation": operation.value,
                "p99_latency_ms": metrics.p99_latency_ms,
                "threshold": self.ALERT_THRESHOLDS["latency_p99_ms"]
            })
        
        # Consecutive errors alert
        if self._consecutive_errors >= self.ALERT_THRESHOLDS["consecutive_errors"]:
            alerts.append({
                "type": "consecutive_errors",
                "count": self._consecutive_errors,
                "threshold": self.ALERT_THRESHOLDS["consecutive_errors"]
            })
        
        # Trigger alert callbacks
        for alert in alerts:
            logger.warning(f"🚨 ALERT: {alert['type']} - {alert}")
            for callback in self._alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """Register a callback for alerts"""
        self._alert_callbacks.append(callback)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics for all operations
        
        Returns:
            Dict with metrics by operation type and backend
        """
        operation_metrics = {}
        for op, metrics in self._metrics.items():
            operation_metrics[op.value] = {
                "total_count": metrics.total_count,
                "success_count": metrics.success_count,
                "error_count": metrics.error_count,
                "success_rate": round(metrics.success_rate, 4),
                "error_rate": round(metrics.error_rate, 4),
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "p50_latency_ms": round(metrics.p50_latency_ms, 2),
                "p99_latency_ms": round(metrics.p99_latency_ms, 2),
                "last_operation": metrics.last_operation.isoformat() if metrics.last_operation else None
            }
        
        backend_metrics = {}
        for backend, metrics in self._backend_metrics.items():
            backend_metrics[backend] = {
                "total_count": metrics.total_count,
                "success_rate": round(metrics.success_rate, 4),
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "p99_latency_ms": round(metrics.p99_latency_ms, 2),
            }
        
        return {
            "operations": operation_metrics,
            "backends": backend_metrics,
            "uptime_seconds": (datetime.utcnow() - self._initialized_at).total_seconds(),
            "total_operations": sum(m.total_count for m in self._metrics.values()),
            "overall_success_rate": self._calculate_overall_success_rate(),
            "recent_errors_count": len(self._recent_errors),
            "consecutive_errors": self._consecutive_errors
        }
    
    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all operations"""
        total = sum(m.total_count for m in self._metrics.values())
        successes = sum(m.success_count for m in self._metrics.values())
        
        if total == 0:
            return 1.0
        return round(successes / total, 4)
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent errors for debugging"""
        return self._recent_errors[-limit:]
    
    def get_audit_log(
        self,
        operation: Optional[OperationType] = None,
        user_hash: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit log with filters
        
        Args:
            operation: Filter by operation type
            user_hash: Filter by user hash
            since: Filter entries after this time
            limit: Maximum entries to return
        """
        filtered = []
        
        for entry in reversed(self._audit_log):
            # Apply filters
            if operation and entry.operation != operation.value:
                continue
            if user_hash and entry.user_hash != user_hash:
                continue
            if since and entry.timestamp < since:
                continue
            
            filtered.append({
                "timestamp": entry.timestamp.isoformat(),
                "operation": entry.operation,
                "user_hash": entry.user_hash,
                "success": entry.success,
                "latency_ms": entry.latency_ms,
                "details": entry.details
            })
            
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of the memory system
        
        Returns:
            Health status with component-level details
        """
        overall_success_rate = self._calculate_overall_success_rate()
        
        # Determine health status
        if overall_success_rate >= 0.99 and self._consecutive_errors == 0:
            status = "healthy"
        elif overall_success_rate >= 0.95:
            status = "degraded"
        else:
            status = "unhealthy"
        
        # Check backend health
        backend_health = {}
        for backend, metrics in self._backend_metrics.items():
            if metrics.total_count == 0:
                backend_health[backend] = "unknown"
            elif metrics.success_rate >= 0.99:
                backend_health[backend] = "healthy"
            elif metrics.success_rate >= 0.95:
                backend_health[backend] = "degraded"
            else:
                backend_health[backend] = "unhealthy"
        
        return {
            "status": status,
            "overall_success_rate": overall_success_rate,
            "consecutive_errors": self._consecutive_errors,
            "backends": backend_health,
            "uptime_seconds": (datetime.utcnow() - self._initialized_at).total_seconds(),
            "last_check": datetime.utcnow().isoformat()
        }
    
    def get_user_audit_trail(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Convenience method to get audit trail for a user
        
        Args:
            user_id: User ID (will be hashed internally)
            limit: Maximum entries to return
            
        Returns:
            List of audit entries for the user
        """
        user_hash = self._hash_user_id(user_id)
        return self.get_audit_log(user_hash=user_hash, limit=limit)
    
    def reset_metrics(self):
        """Reset all metrics (for testing or new period)"""
        self._metrics = {op: OperationMetrics() for op in OperationType}
        self._backend_metrics.clear()
        self._consecutive_errors = 0
        logger.info("📊 Metrics reset")
    
    def get_debug_snapshot(self, user_id: str) -> Dict[str, Any]:
        """
        Get a debug snapshot for a specific user (hashed)
        
        Useful for debugging user-specific issues.
        """
        user_hash = self._hash_user_id(user_id)
        
        # Get recent operations for this user
        user_operations = self.get_audit_log(
            user_hash=user_hash,
            limit=50
        )
        
        # Calculate user-specific stats
        if user_operations:
            user_success_rate = sum(1 for op in user_operations if op["success"]) / len(user_operations)
            user_avg_latency = statistics.mean(op["latency_ms"] for op in user_operations)
        else:
            user_success_rate = None
            user_avg_latency = None
        
        return {
            "user_hash": user_hash,
            "recent_operations": user_operations[:10],
            "operation_count": len(user_operations),
            "success_rate": user_success_rate,
            "avg_latency_ms": user_avg_latency,
            "snapshot_time": datetime.utcnow().isoformat()
        }


def observe_memory_operation(
    operation: OperationType,
    backend: Optional[str] = None
):
    """
    Decorator to automatically observe memory operations
    
    Usage:
        @observe_memory_operation(OperationType.STORE, backend="mongodb")
        async def store_memory(user_id: str, content: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id") or (args[0] if args else "unknown")
            start_time = time.time()
            success = True
            details = {}
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                details["error"] = str(e)[:100]
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                memory_observer.log_operation(
                    operation=operation,
                    user_id=user_id,
                    success=success,
                    latency_ms=latency_ms,
                    backend=backend,
                    details=details
                )
        
        return wrapper
    return decorator


# Global singleton instance
memory_observer = MemoryObserver()
