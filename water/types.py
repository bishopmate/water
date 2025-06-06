from typing import Any, Callable, Dict, List, Union
from typing_extensions import TypedDict

# Forward declaration for ExecutionContext
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from water.context import ExecutionContext

# Type aliases
InputData = Dict[str, Any]
OutputData = Dict[str, Any]
ConditionFunction = Callable[[InputData], bool]

# Updated task execution function signature to include context
TaskExecuteFunction = Callable[[Dict[str, InputData], 'ExecutionContext'], OutputData]

# TypedDict definitions for node structures
class SequentialNode(TypedDict):
    type: str
    task: Any  # Will be Task when we import it

class ParallelNode(TypedDict):
    type: str
    tasks: List[Any]  # Will be List[Task]

class BranchCondition(TypedDict):
    condition: ConditionFunction
    task: Any  # Will be Task

class BranchNode(TypedDict):
    type: str
    branches: List[BranchCondition]

class LoopNode(TypedDict):
    type: str
    condition: ConditionFunction
    task: Any  # Will be Task
    max_iterations: int

# Union type for all node types
ExecutionNode = Union[SequentialNode, ParallelNode, BranchNode, LoopNode]
ExecutionGraph = List[ExecutionNode]