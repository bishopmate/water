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
    """
    A workflow orchestrator that allows building and executing complex data processing pipelines.
    
    Flows support sequential execution, parallel processing, conditional branching, and loops.
    All flows must be registered before execution.
    """
    
    def __init__(
        self, 
        id: Optional[str] = None, 
        description: Optional[str] = None
    ) -> None:
        """
        Initialize a new Flow.
        
        Args:
            id: Unique identifier for the flow. Auto-generated if not provided.
            description: Human-readable description of the flow's purpose.
        """
        self.id: str = id if id else f"flow_{uuid.uuid4().hex[:8]}"
        self.description: str = description if description else f"Flow {self.id}"
        self._tasks: List[ExecutionNode] = []
        self._registered: bool = False
        self.metadata: Dict[str, Any] = {}
    
    def _validate_registration_state(self) -> None:
        """Ensure flow is not registered when adding tasks."""
        if self._registered:
            raise RuntimeError("Cannot add tasks after registration")
    
    def _validate_task(self, task: Any) -> None:
        """Validate that a task is not None."""
        if task is None:
            raise ValueError("Task cannot be None")
    
    def _validate_condition(self, condition: ConditionFunction) -> None:
        """Validate that a condition function is not async."""
        if inspect.iscoroutinefunction(condition):
            raise ValueError("Branch conditions cannot be async functions")
    
    def _validate_loop_condition(self, condition: ConditionFunction) -> None:
        """Validate that a loop condition function is not async."""
        if inspect.iscoroutinefunction(condition):
            raise ValueError("Loop conditions cannot be async functions")

    def set_metadata(self, key: str, value: Any) -> 'Flow':
        """
        Set metadata for this flow.
        
        Args:
            key: The metadata key
            value: The metadata value
            
        Returns:
            Self for method chaining
        """
        self.metadata[key] = value
        return self

    def then(self, task: Any) -> 'Flow':
        """
        Add a task to execute sequentially.
        
        Args:
            task: The task to execute
            
        Returns:
            Self for method chaining
            
        Raises:
            RuntimeError: If flow is already registered
            ValueError: If task is None
        """
        self._validate_registration_state()
        self._validate_task(task)
        
        node: ExecutionNode = {"type": NodeType.SEQUENTIAL.value, "task": task}
        self._tasks.append(node)
        return self

    def parallel(self, tasks: List[Any]) -> 'Flow':
        """
        Add tasks to execute in parallel.
        
        Args:
            tasks: List of tasks to execute concurrently
            
        Returns:
            Self for method chaining
            
        Raises:
            RuntimeError: If flow is already registered
            ValueError: If task list is empty or contains None values
        """
        self._validate_registration_state()
        if not tasks:
            raise ValueError("Parallel task list cannot be empty")
        
        for task in tasks:
            self._validate_task(task)
        
        node: ExecutionNode = {
            "type": NodeType.PARALLEL.value,
            "tasks": list(tasks)
        }
        self._tasks.append(node)
        return self

    def branch(self, branches: List[Tuple[ConditionFunction, Any]]) -> 'Flow':
        """
        Add conditional branching logic.
        
        Executes the first task whose condition returns True.
        If no conditions match, data passes through unchanged.
        
        Args:
            branches: List of (condition_function, task) tuples
            
        Returns:
            Self for method chaining
            
        Raises:
            RuntimeError: If flow is already registered
            ValueError: If branch list is empty, task is None, or condition is async
        """
        self._validate_registration_state()
        if not branches:
            raise ValueError("Branch list cannot be empty")
        
        for condition, task in branches:
            self._validate_task(task)
            self._validate_condition(condition)
        
        node: ExecutionNode = {
            "type": NodeType.BRANCH.value,
            "branches": [{"condition": cond, "task": task} for cond, task in branches]
        }
        self._tasks.append(node)
        return self

    def loop(
        self, 
        condition: ConditionFunction, 
        task: Any,
        max_iterations: int = 100
    ) -> 'Flow':
        """
        Execute a task repeatedly while a condition is true.
        
        Args:
            condition: Function that returns True to continue looping
            task: Task to execute on each iteration
            max_iterations: Maximum number of iterations to prevent infinite loops
            
        Returns:
            Self for method chaining
            
        Raises:
            RuntimeError: If flow is already registered
            ValueError: If task is None or condition is async
        """
        self._validate_registration_state()
        self._validate_task(task)
        self._validate_loop_condition(condition)
        
        node: ExecutionNode = {
            "type": NodeType.LOOP.value,
            "condition": condition,
            "task": task,
            "max_iterations": max_iterations
        }
        self._tasks.append(node)
        return self

    def register(self) -> 'Flow':
        """
        Register the flow for execution.
        
        Must be called before running the flow.
        Once registered, no more tasks can be added.
        
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If flow has no tasks
        """
        if not self._tasks:
            raise ValueError("Flow must have at least one task")
        self._registered = True
        return self

    async def run(self, input_data: InputData) -> OutputData:
        """
        Execute the flow with the provided input data.
        
        Args:
            input_data: Input data dictionary to process
            
        Returns:
            The final output data after all tasks complete
            
        Raises:
            RuntimeError: If flow is not registered
        """
        if not self._registered:
            raise RuntimeError("Flow must be registered before running")
        
        return await ExecutionEngine.run(
            self._tasks, 
            input_data, 
            flow_id=self.id,
            flow_metadata=self.metadata
        )
