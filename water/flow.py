from typing import Any, List, Optional, Tuple, Dict
import inspect
import uuid

from water.execution_engine import ExecutionEngine, NodeType
from water.types import (
    InputData, 
    OutputData, 
    ConditionFunction,
    ExecutionNode
)

class Flow:
    def __init__(self, id: Optional[str] = None, description: Optional[str] = None) -> None:
        self.id: str = id if id else f"flow_{uuid.uuid4().hex[:8]}"
        self.description: str = description if description else f"Flow {self.id}"
        self._tasks: List[ExecutionNode] = []
        self._registered: bool = False
        self.metadata: Dict[str, Any] = {}

    def set_metadata(self, key: str, value: Any) -> 'Flow':
        """Set metadata for this flow."""
        self.metadata[key] = value
        return self

    def then(self, task: Any) -> 'Flow':  # Task type - will fix when we get to Task class
        """Add a task to execute sequentially."""
        if self._registered:
            raise RuntimeError("Cannot add tasks after registration")
        if task is None:
            raise ValueError("Task cannot be None")
        
        node: ExecutionNode = {"type": NodeType.SEQUENTIAL.value, "task": task}
        self._tasks.append(node)
        return self

    def parallel(self, tasks: List[Any]) -> 'Flow':  # List[Task] type
        """Add tasks to execute in parallel."""
        if self._registered:
            raise RuntimeError("Cannot add tasks after registration")
        if not tasks:
            raise ValueError("Parallel task list cannot be empty")
        
        for task in tasks:
            if task is None:
                raise ValueError("Task cannot be None")
        
        node: ExecutionNode = {
            "type": NodeType.PARALLEL.value,
            "tasks": list(tasks)
        }
        self._tasks.append(node)
        return self

    def branch(self, branches: List[Tuple[ConditionFunction, Any]]) -> 'Flow':  # Tuple[ConditionFunction, Task]
        """Add conditional branching."""
        if self._registered:
            raise RuntimeError("Cannot add tasks after registration")
        if not branches:
            raise ValueError("Branch list cannot be empty")
        
        for condition, task in branches:
            if task is None:
                raise ValueError("Task cannot be None")
            if inspect.iscoroutinefunction(condition):
                raise ValueError("Branch conditions cannot be async functions")
        
        node: ExecutionNode = {
            "type": NodeType.BRANCH.value,
            "branches": [{"condition": cond, "task": task} for cond, task in branches]
        }
        self._tasks.append(node)
        return self

    def loop(
        self, 
        condition: ConditionFunction, 
        task: Any,  # Task type
        max_iterations: int = 100
    ) -> 'Flow':
        """
        Execute a task repeatedly while a condition is true.
        
        Args:
            condition: A callable that takes the current data and returns a boolean
            task: The task to execute in each iteration
            max_iterations: Maximum number of iterations to prevent infinite loops
            
        Returns:
            self: For method chaining
        """
        if self._registered:
            raise RuntimeError("Cannot add tasks after registration")
        if task is None:
            raise ValueError("Task cannot be None")
        if inspect.iscoroutinefunction(condition):
            raise ValueError("Loop conditions cannot be async functions")
        
        node: ExecutionNode = {
            "type": NodeType.LOOP.value,
            "condition": condition,
            "task": task,
            "max_iterations": max_iterations
        }
        self._tasks.append(node)
        return self

    def register(self) -> 'Flow':
        """Register the flow for execution."""
        if not self._tasks:
            raise ValueError("Flow must have at least one task")
        self._registered = True
        return self

    async def run(self, input_data: InputData) -> OutputData:
        """Execute the registered flow."""
        if not self._registered:
            raise RuntimeError("Flow must be registered before running")
        return await ExecutionEngine.run(
            self._tasks, 
            input_data, 
            flow_id=self.id,
            flow_metadata=self.metadata
        )
