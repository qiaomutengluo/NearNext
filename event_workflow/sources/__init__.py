from event_workflow.sources.base import EventSource
from event_workflow.sources.concordia import ConcordiaEventSource
from event_workflow.sources.mcgill import McGillEventSource

__all__ = ["EventSource", "ConcordiaEventSource", "McGillEventSource"]
