from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class IntentSpec:
    required_slots: List[str]
    memory_read: List[str]
    memory_write: List[str]
    requires_confirmation: bool = False


INTENTS: Dict[str, IntentSpec] = {
    # Category A: Task System (Strict Path)
    "task_create": IntentSpec(
        required_slots=["task_name", "target_time"],
        memory_read=["redis_history"],
        memory_write=["mongo_tasks_collection"],
        requires_confirmation=True,
    ),
    "task_update": IntentSpec(
        required_slots=["task_id", "new_value"],
        memory_read=["redis_history", "mongo_tasks_collection"],
        memory_write=["mongo_tasks_collection"],
        requires_confirmation=True,
    ),
    "task_cancel": IntentSpec(
        required_slots=["task_id"],
        memory_read=["redis_history", "mongo_tasks_collection"],
        memory_write=["mongo_tasks_collection"],
        requires_confirmation=True,
    ),
    "task_list": IntentSpec(
        required_slots=["status"],
        memory_read=[],
        memory_write=[],
        requires_confirmation=False,
    ),

    # Category B: Knowledge & Chat (Fast Path)
    "casual_chat": IntentSpec(
        required_slots=[],
        memory_read=[],
        memory_write=[],
    ),
    "recall_memory": IntentSpec(
        required_slots=["query"],
        memory_read=["pinecone_vector"],
        memory_write=[],
    ),
    "web_search": IntentSpec(
        required_slots=["query"],
        memory_read=[],
        memory_write=[],
    ),
    "deep_research": IntentSpec(
        required_slots=["query"],
        memory_read=["pinecone_vector"],
        memory_write=[],
        requires_confirmation=True,
    ),

    # Category C: System & Meta
    "correction": IntentSpec(
        required_slots=["slot_name", "slot_value"],
        memory_read=["redis_context_stack"],
        memory_write=["redis_context_stack"],
    ),
    "stop": IntentSpec(
        required_slots=[],
        memory_read=["redis_context_stack"],
        memory_write=["redis_context_stack"],
    ),
}
