from typing import Any, Dict, Optional, List
from datetime import datetime
import uuid

from water.types import InputData, OutputData

class ExecutionContext:
    """
    Context passed to every task execution containing execution metadata.
    """
    
    def __init__(
        self,
        flow_id: str,
        execution_id: Optional[str] = None,
        task_id: Optional[str] = None,
        step_number: int = 0,
        attempt_number: int = 1,
        flow_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self.flow_id = flow_id
        self.execution_id = execution_id or f"exec_{uuid.uuid4().hex[:8]}"
        self.task_id = task_id
        self.step_number = step_number
        self.attempt_number = attempt_number
        self.flow_metadata = flow_metadata or {}
        
        # Timing information
        self.execution_start_time = datetime.utcnow()
        self.step_start_time = datetime.utcnow()
        
        # Task outputs history
        self._task_outputs: Dict[str, OutputData] = {}
        self._step_history: List[Dict[str, Any]] = []
    
    def add_task_output(self, task_id: str, output: OutputData) -> None:
        """Record the output of a completed task."""
        self._task_outputs[task_id] = output
        
        step_info = {
            "step_number": self.step_number,
            "task_id": task_id,
            "output": output,
            "timestamp": datetime.utcnow().isoformat(),
            "attempt_number": self.attempt_number
        }
        self._step_history.append(step_info)
    
    def get_task_output(self, task_id: str) -> Optional[OutputData]:
        """Get the output from a previously executed task."""
        return self._task_outputs.get(task_id)
    
    def get_all_task_outputs(self) -> Dict[str, OutputData]:
        """Get all task outputs from this execution."""
        return self._task_outputs.copy()
    
    def get_step_history(self) -> List[Dict[str, Any]]:
        """Get the complete step execution history."""
        return self._step_history.copy()
    
    def create_child_context(
        self, 
        task_id: str, 
        step_number: Optional[int] = None,
        attempt_number: int = 1
    ) -> 'ExecutionContext':
        """Create a new context for a child task execution."""
        child_context = ExecutionContext(
            flow_id=self.flow_id,
            execution_id=self.execution_id,
            task_id=task_id,
            step_number=step_number or (self.step_number + 1),
            attempt_number=attempt_number,
            flow_metadata=self.flow_metadata
        )
        
        # Copy task outputs and history to child
        child_context._task_outputs = self._task_outputs.copy()
        child_context._step_history = self._step_history.copy()
        child_context.execution_start_time = self.execution_start_time
        
        return child_context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "flow_id": self.flow_id,
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "step_number": self.step_number,
            "attempt_number": self.attempt_number,
            "flow_metadata": self.flow_metadata,
            "execution_start_time": self.execution_start_time.isoformat(),
            "step_start_time": self.step_start_time.isoformat(),
            "task_outputs": self._task_outputs,
            "step_history": self._step_history
        }
    
    def __repr__(self) -> str:
        return (
            f"ExecutionContext(flow_id='{self.flow_id}', "
            f"execution_id='{self.execution_id}', "
            f"task_id='{self.task_id}', "
            f"step={self.step_number}, "
            f"attempt={self.attempt_number})"
        ) 