from typing import Type, Callable, Optional, Dict
from pydantic import BaseModel
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
        input_schema: Type[BaseModel],
        output_schema: Type[BaseModel],
        execute: Callable[[Dict[str, InputData], 'ExecutionContext'], OutputData], 
        id: Optional[str] = None, 
        description: Optional[str] = None
    ) -> None:
        self.id: str = id if id else f"task_{uuid.uuid4().hex[:8]}"
        self.description: str = description if description else f"Task {self.id}"
        
        # Validate schemas are Pydantic BaseModel classes
        if not input_schema or not (isinstance(input_schema, type) and issubclass(input_schema, BaseModel)):
            raise WaterError("input_schema must be a Pydantic BaseModel class")
        if not output_schema or not (isinstance(output_schema, type) and issubclass(output_schema, BaseModel)):
            raise WaterError("output_schema must be a Pydantic BaseModel class")
        if not execute or not callable(execute):
            raise WaterError("Task must have a callable execute function")
        
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.execute = execute

   
def create_task(
    id: Optional[str] = None, 
    description: Optional[str] = None, 
    input_schema: Optional[Type[BaseModel]] = None, 
    output_schema: Optional[Type[BaseModel]] = None, 
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