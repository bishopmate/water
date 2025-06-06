from typing import List, Dict, Any, Optional, Type
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from datetime import datetime

from water.flow import Flow
from water.types import InputData, OutputData

# Request/Response Models
class RunFlowRequest(BaseModel):
    input_data: Dict[str, Any]

class RunFlowResponse(BaseModel):
    flow_id: str
    status: str
    result: Dict[str, Any]
    execution_time_ms: float
    timestamp: datetime

class TaskInfo(BaseModel):
    id: str
    description: str
    type: str  # "sequential", "parallel", "branch", "loop"
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None

class FlowSummary(BaseModel):
    id: str
    description: str
    tasks: List[TaskInfo]

class FlowDetail(BaseModel):
    id: str
    description: str
    metadata: Dict[str, Any]
    tasks: List[TaskInfo]

class FlowsListResponse(BaseModel):
    flows: List[FlowSummary]

class FlowServer:
    """
    FastAPI server for hosting Water flows.
    
    Usage:
        flows = [flow1, flow2, flow3]
        app = FlowServer(flows=flows).get_app()
        
        if __name__ == "__main__":
            import uvicorn
            uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    """
    
    def __init__(self, flows: List[Flow]):
        """
        Initialize FlowServer with a list of flows.
        
        Args:
            flows: List of registered Flow instances
        """
        # Index flows by ID and validate uniqueness
        self.flows: Dict[str, Flow] = {}
        for flow in flows:
            if flow.id in self.flows:
                raise ValueError(f"Duplicate flow ID: {flow.id}")
            if not flow._registered:
                raise ValueError(f"Flow {flow.id} must be registered before adding to server")
            self.flows[flow.id] = flow
    
    def _serialize_schema(self, schema_class: Type[BaseModel]) -> Optional[Dict[str, Any]]:
        """Convert Pydantic model to a simple field:type mapping."""
        if schema_class is None:
            return None
        
        try:
            schema_dict = {}
            for field_name, field_info in schema_class.model_fields.items():
                # Get the clean type name
                field_type = self._get_clean_type_name(field_info.annotation)
                schema_dict[field_name] = field_type
            
            return schema_dict
            
        except Exception as e:
            return {"error": f"Could not parse schema: {str(e)}"}
    
    def _get_clean_type_name(self, field_type) -> str:
        """Get a clean, readable type name."""
        # Convert type to string and clean it up
        type_str = str(field_type)
        
        # Handle common types
        if field_type == int:
            return "int"
        elif field_type == float:
            return "float"
        elif field_type == str:
            return "string"
        elif field_type == bool:
            return "boolean"
        elif field_type == list:
            return "array"
        elif field_type == dict:
            return "object"
        
        # Handle typing module types
        if "typing." in type_str:
            # Extract the base type name
            if "List" in type_str:
                return "array"
            elif "Dict" in type_str:
                return "object"
            elif "Optional" in type_str:
                # Extract the inner type from Optional[Type]
                inner_type = type_str.replace("typing.Union[", "").replace("typing.Optional[", "").replace(", NoneType]", "").replace("]", "")
                return self._get_clean_type_name_from_string(inner_type)
        
        # Handle class types (like custom Pydantic models)
        if hasattr(field_type, '__name__'):
            return field_type.__name__
        
        # Fallback: clean up the string representation
        return self._get_clean_type_name_from_string(type_str)
    
    def _get_clean_type_name_from_string(self, type_str: str) -> str:
        """Clean up type string representation."""
        # Remove common prefixes
        type_str = type_str.replace("<class '", "").replace("'>", "")
        type_str = type_str.replace("typing.", "")
        
        # Handle basic types
        if "int" in type_str.lower():
            return "int"
        elif "float" in type_str.lower():
            return "float"
        elif "str" in type_str.lower():
            return "string"
        elif "bool" in type_str.lower():
            return "boolean"
        elif "list" in type_str.lower():
            return "array"
        elif "dict" in type_str.lower():
            return "object"
        
        # Return the cleaned string
        return type_str.split(".")[-1] if "." in type_str else type_str
    
    def _extract_task_info(self, execution_nodes: List[Dict[str, Any]]) -> List[TaskInfo]:
        """Extract task information from execution nodes."""
        task_infos = []
        
        for node in execution_nodes:
            node_type = node["type"]
            
            if node_type == "sequential":
                task = node["task"]
                task_infos.append(TaskInfo(
                    id=task.id,
                    description=task.description,
                    type="sequential",
                    input_schema=self._serialize_schema(task.input_schema),
                    output_schema=self._serialize_schema(task.output_schema)
                ))
            
            elif node_type == "parallel":
                for task in node["tasks"]:
                    task_infos.append(TaskInfo(
                        id=task.id,
                        description=task.description,
                        type="parallel",
                        input_schema=self._serialize_schema(task.input_schema),
                        output_schema=self._serialize_schema(task.output_schema)
                    ))
            
            elif node_type == "branch":
                for branch in node["branches"]:
                    task = branch["task"]
                    task_infos.append(TaskInfo(
                        id=task.id,
                        description=task.description,
                        type="branch",
                        input_schema=self._serialize_schema(task.input_schema),
                        output_schema=self._serialize_schema(task.output_schema)
                    ))
            
            elif node_type == "loop":
                task = node["task"]
                task_infos.append(TaskInfo(
                    id=task.id,
                    description=task.description,
                    type="loop",
                    input_schema=self._serialize_schema(task.input_schema),
                    output_schema=self._serialize_schema(task.output_schema)
                ))
        
        return task_infos
    
    def get_app(self) -> FastAPI:
        """Create and configure the FastAPI application."""
        app = FastAPI(
            title="Water Flows API",
            description="REST API for executing Water framework workflows",
            version="1.0.0"
        )
        
        # Add CORS middleware for development
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Health check endpoint
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "flows_count": len(self.flows),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # List all flows
        @app.get("/flows", response_model=FlowsListResponse)
        async def list_flows():
            """Get list of all available flows."""
            flows_summary = []
            for flow in self.flows.values():
                task_infos = self._extract_task_info(flow._tasks)
                flows_summary.append(FlowSummary(
                    id=flow.id,
                    description=flow.description,
                    tasks=task_infos,
                ))
            
            return FlowsListResponse(flows=flows_summary)
        
        # Get specific flow details
        @app.get("/flows/{flow_id}", response_model=FlowDetail)
        async def get_flow_details(flow_id: str):
            """Get detailed information about a specific flow."""
            if flow_id not in self.flows:
                raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
            
            flow = self.flows[flow_id]
            task_infos = self._extract_task_info(flow._tasks)
            
            return FlowDetail(
                id=flow.id,
                description=flow.description,
                metadata=flow.metadata,
                tasks=task_infos,
            )
        
        # Execute a flow
        @app.post("/flows/{flow_id}/run", response_model=RunFlowResponse)
        async def run_flow(flow_id: str, request: RunFlowRequest):
            """Execute a specific flow with input data."""
            if flow_id not in self.flows:
                raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")
            
            flow = self.flows[flow_id]
            
            try:
                start_time = datetime.utcnow()
                result = await flow.run(request.input_data)
                end_time = datetime.utcnow()
                
                execution_time_ms = round((end_time - start_time).total_seconds() * 1000, 4)
                
                return RunFlowResponse(
                    flow_id=flow_id,
                    status="success",
                    result=result,
                    execution_time_ms=execution_time_ms,
                    timestamp=end_time
                )
                
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail={
                        "error": str(e),
                        "flow_id": flow_id
                    }
                )
        
        return app 