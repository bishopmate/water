import inspect
import asyncio
from enum import Enum
from typing import Any, Dict, List
from datetime import datetime

from water.types import (
    ExecutionGraph, 
    ExecutionNode, 
    InputData, 
    OutputData,
    SequentialNode,
    ParallelNode,
    BranchNode,
    LoopNode
)
from water.context import ExecutionContext

class NodeType(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BRANCH = "branch"
    LOOP = "loop"

class ExecutionEngine:
    @staticmethod
    async def run(
        execution_graph: ExecutionGraph, 
        input_data: InputData,
        flow_id: str,
        flow_metadata: Dict[str, Any] = None
    ) -> OutputData:
        """Main orchestrator - delegates to specific node handlers."""
        # Create root execution context
        context = ExecutionContext(
            flow_id=flow_id,
            flow_metadata=flow_metadata or {}
        )
        
        data: OutputData = input_data
        step_number = 0
        
        for node in execution_graph:
            step_number += 1
            # Create context for this step
            step_context = context.create_child_context(
                task_id=f"step_{step_number}",
                step_number=step_number
            )
            
            data = await ExecutionEngine._execute_node(node, data, step_context)
            
            # Record step completion in context
            if hasattr(node, 'get') and 'task' in node:
                task = node['task']
                context.add_task_output(task.id, data)
        
        return data
    
    @staticmethod
    async def _execute_node(
        node: ExecutionNode, 
        data: InputData, 
        context: ExecutionContext
    ) -> OutputData:
        """Route to appropriate node type handler."""
        try:
            node_type = NodeType(node["type"])
        except ValueError:
            raise ValueError(f"Unknown node type: {node['type']}")
        
        if node_type == NodeType.SEQUENTIAL:
            return await ExecutionEngine._execute_sequential(node, data, context)
        elif node_type == NodeType.PARALLEL:
            return await ExecutionEngine._execute_parallel(node, data, context)
        elif node_type == NodeType.BRANCH:
            return await ExecutionEngine._execute_branch(node, data, context)
        elif node_type == NodeType.LOOP:
            return await ExecutionEngine._execute_loop(node, data, context)
        else:
            raise ValueError(f"Unhandled node type: {node_type}")
    
    @staticmethod
    async def _execute_task(task: Any, data: InputData, context: ExecutionContext) -> OutputData:
        """Common task execution logic - always passes context."""
        params: Dict[str, InputData] = {"input_data": data}
        
        # Update context with current task info
        context.task_id = task.id
        context.step_start_time = datetime.utcnow()  # Reset step timer
        
        if inspect.iscoroutinefunction(task.execute):
            result: OutputData = await task.execute(params, context)
        else:
            result = task.execute(params, context)
        
        return result
    
    @staticmethod
    async def _execute_sequential(
        node: SequentialNode, 
        data: InputData, 
        context: ExecutionContext
    ) -> OutputData:
        """Execute a single task sequentially."""
        task = node["task"]
        return await ExecutionEngine._execute_task(task, data, context)
    
    @staticmethod
    async def _execute_parallel(
        node: ParallelNode,
        data: InputData,
        context: ExecutionContext
    ) -> OutputData:
        """Execute multiple tasks in parallel."""
        tasks = node["tasks"]
        
        # Create coroutines for each task with individual contexts
        coroutines: List[Any] = []
        task_contexts: List[ExecutionContext] = []
        
        for i, task in enumerate(tasks):
            # Create individual context for each parallel task
            task_context = context.create_child_context(
                task_id=task.id,
                step_number=context.step_number + i
            )
            task_contexts.append(task_context)
            
            params: Dict[str, InputData] = {"input_data": data}
            if inspect.iscoroutinefunction(task.execute):
                coroutines.append(task.execute(params, task_context))
            else:
                # Wrap synchronous functions in coroutines
                async def sync_wrapper(t=task, p=params, ctx=task_context):
                    return t.execute(p, ctx)
                coroutines.append(sync_wrapper())
        
        # Execute all tasks in parallel
        results: List[OutputData] = await asyncio.gather(*coroutines)
        
        # Organize results by task ID
        organized_results: Dict[str, OutputData] = {}
        for task, result in zip(tasks, results):
            organized_results[task.id] = result
        
        return organized_results
    
    @staticmethod
    async def _execute_branch(
        node: BranchNode, 
        data: InputData, 
        context: ExecutionContext
    ) -> OutputData:
        """Execute one task based on condition matching."""
        branches = node["branches"]
        
        for branch in branches:
            condition = branch["condition"]
            if condition(data):
                task = branch["task"]
                result = await ExecutionEngine._execute_task(task, data, context)
                context.add_task_output(task.id, result)
                return result
        
        # If no condition matched, return data unchanged
        return data
    
    @staticmethod
    async def _execute_loop(
        node: LoopNode, 
        data: InputData, 
        context: ExecutionContext
    ) -> OutputData:
        """Execute a task repeatedly while condition is true."""
        condition = node["condition"]
        task = node["task"]
        max_iterations: int = node.get("max_iterations", 100)
        
        iteration_count: int = 0
        current_data: OutputData = data
        
        while condition(current_data) and iteration_count < max_iterations:
            # Create context for this iteration
            iteration_context = context.create_child_context(
                task_id=f"{task.id}_iter_{iteration_count}",
                step_number=context.step_number,
                attempt_number=iteration_count + 1
            )
            
            current_data = await ExecutionEngine._execute_task(task, current_data, iteration_context)
            context.add_task_output(f"{task.id}_iter_{iteration_count}", current_data)
            iteration_count += 1
            
        if iteration_count >= max_iterations:
            print(f"Warning: Loop reached maximum iterations ({max_iterations})")
            
        return current_data