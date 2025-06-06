from typing import Any, Callable, Optional, Dict
from water.exceptions import WaterError
import inspect
import uuid

from water.types import InputData, OutputData

# Import here to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from water.context import ExecutionContext

class Task:
    def __init__(
        self, 
        input_schema: Any,
        output_schema: Any,
        execute: Callable[[Dict[str, InputData], 'ExecutionContext'], OutputData], 
        id: Optional[str] = None, 
        description: Optional[str] = None
    ) -> None:
        self.id: str = id if id else f"task_{uuid.uuid4().hex[:8]}"
        self.description: str = description if description else f"Task {self.id}"
        
        # Validate schemas
        if not input_schema:
            raise WaterError("Task must have an input schema")
        if not output_schema:
            raise WaterError("Task must have an output schema")
        if not execute or not callable(execute):
            raise WaterError("Task must have a callable execute function")
        
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.execute = execute

   
def create_task(
    id: Optional[str] = None, 
    description: Optional[str] = None, 
    input_schema: Optional[Any] = None, 
    output_schema: Optional[Any] = None, 
    execute: Optional[Callable[[Dict[str, InputData], 'ExecutionContext'], OutputData]] = None
) -> Task:
    """Factory function to create a Task instance."""
    return Task(
        input_schema=input_schema,
        output_schema=output_schema,
        execute=execute,
        id=id,
        description=description,
    )