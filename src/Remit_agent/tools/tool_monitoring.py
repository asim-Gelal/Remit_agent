"""Tool monitoring and tracking functionality."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from ..logger import get_logger

logger = get_logger(__name__)

@dataclass
class ToolInvocation:
    """Record of a tool invocation."""
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Any
    timestamp: datetime
    duration: float

class ToolMonitor:
    """Monitor and store tool invocations."""

    def __init__(self):
        self.invocations: List[ToolInvocation] = []
        self._start_time: float = 0

    def start_invocation(self, tool_name: str, inputs: Dict[str, Any]):
        """Start monitoring a tool invocation."""
        self._start_time = datetime.now().timestamp()
        logger.debug(f"Starting tool invocation: {tool_name}")

    def end_invocation(self, tool_name: str, inputs: Dict[str, Any], outputs: Any):
        """End monitoring a tool invocation and record it."""
        end_time = datetime.now().timestamp()
        duration = end_time - self._start_time

        invocation = ToolInvocation(
            tool_name=tool_name,
            inputs=inputs,
            outputs=outputs,
            timestamp=datetime.fromtimestamp(self._start_time),
            duration=duration
        )
        self.invocations.append(invocation)
        logger.debug(f"Completed tool invocation: {tool_name} (duration: {duration:.2f}s)")

    def clear(self):
        """Clear all recorded invocations."""
        self.invocations = []
        logger.debug("Cleared all tool invocations")

    def get_invocations(self) -> List[ToolInvocation]:
        """Get all recorded invocations."""
        return self.invocations

    def __call__(self, func):
        """Make the ToolMonitor instance callable as a decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.start_invocation(func.__name__, kwargs)
            try:
                outputs = func(*args, **kwargs)
                self.end_invocation(func.__name__, kwargs, outputs)
                return outputs
            except Exception as e:
                self.end_invocation(func.__name__, kwargs, f"Error: {str(e)}")
                raise e
        return wrapper

# Create a global instance for tool monitoring
tool_monitor = ToolMonitor()