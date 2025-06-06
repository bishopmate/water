# Water Framework Implementation Instructions

## Project Overview
Build a Python workflow orchestration framework called "Water" inspired by Mastra's TypeScript implementation. The framework provides primitives for building complex, stateful workflows with pause/resume capabilities and automatic FastAPI server generation.

## Core Requirements

### 1. Project Structure
```
water/
├── water/
│   ├── core/          # Task, Flow, execution engine
│   ├── storage/       # Abstract storage + SQLite implementation
│   ├── control_flow/  # Conditional, parallel, loops, nested workflows
│   ├── server/        # FastAPI auto-generation
│   ├── cli/           # CLI commands
│   ├── recovery/      # Retry, circuit breaker, self-healing
│   └── utils/         # Logging, serialization, monitoring
├── examples/
├── tests/
└── pyproject.toml
```

### 2. Core Primitives

**Task Class:**
- Smallest executable unit with id, description, execute function
- Generic typing with input/output models using Pydantic
- Support for retry policies and timeouts
- Validation of inputs and outputs

**Flow Class:**
- Collection of tasks with dependency management
- Support for variables and metadata
- Fluent API methods: `.then()`, `.branch()`, `.parallel()`, `.while()`, `.for()`
- All methods return Flow instance for method chaining
- Built-in storage backend integration

**TaskContext:**
- Passed to every task execution
- Contains flow_id, execution_id, task_id, attempt number
- Access to previous task outputs and workflow variables

### 3. Control Flow Primitives

**Sequential Flow:**
- Tasks execute one after another using `.then(task)`
- Output from one task becomes input to next
- Dependencies managed automatically
- Fluent API: `flow.then(task1).then(task2).then(task3)`

**Conditional Branching:**
- Multiple condition/task pairs using `.branch([[condition, task], [condition2, task2]])`
- Conditions evaluated in order, first match executes
- Support for complex conditions based on previous task outputs
- Fluent API: `flow.branch([[lambda x: x > 5, high_task], [lambda x: x <= 5, low_task]])`

**Parallel Execution:**
- Execute multiple tasks simultaneously using `.parallel([task1, task2, task3])`
- Wait for all to complete before continuing
- Collect results from all parallel tasks
- Fluent API: `flow.parallel([task1, task2, task3]).then(combine_task)`

**Loop Constructs:**
- **While loops:** `.while(condition, task)` - repeat task while condition is true
- **For loops:** `.for(task)` - execute task for each item in array from previous output or workflow input
- For loops automatically iterate over arrays and pass individual items to the task
- For loops collect all results into an array for the next step
- Fluent API: `flow.while(lambda x: x < 100, increment_task)` or `flow.for(process_item_task)`

**Data Flow:**
- `.then()` passes output of previous task as input to next task
- `.branch()` passes same input to the task whose condition matches
- `.parallel()` passes same input to all tasks, collects outputs as array
- `.for()` splits array input into individual items, collects outputs as array
- `.while()` passes output back as input for next iteration

**Nested Workflows:**
- Embed one workflow inside another
- Treat nested workflow as a single task
- Pass data between parent and child workflows

### 4. Storage System

**Abstract Storage Interface:**
- save_snapshot(snapshot) - Save workflow state
- load_snapshot(execution_id) - Load workflow state
- save_task_result(execution_id, task_id, result) - Save task results
- list_executions() - List all executions with filtering
- delete_execution() - Clean up execution data

**SQLite Implementation:**
- Default storage backend
- Tables: flow_snapshots, task_results
- Async operations using aiosqlite
- JSON serialization for complex data

**Snapshot Format:**
- Contains complete workflow state
- execution_id, flow_id, status, current_step
- completed_steps, failed_steps, step_outputs
- variables, metadata, timestamps

### 5. Execution Engine

**FlowExecution Class:**
- Manages single workflow execution
- Tracks state (pending, running, paused, completed, failed)
- Handles step dependencies and parallel execution
- Implements pause/resume functionality

**Execution Logic:**
- Build execution graph from fluent API calls (.then, .branch, .parallel, etc.)
- Calculate ready steps based on dependencies
- Handle different execution patterns:
  - Sequential: Execute one after another
  - Branching: Evaluate conditions and execute matching task
  - Parallel: Execute all tasks concurrently, wait for completion
  - Loops: Handle iteration logic and result collection
- Save snapshots after each step completion
- Handle errors and retry logic

**Pause/Resume:**
- Save complete state to storage on pause
- Restore state from storage on resume
- Continue from exactly where it left off

### 6. Recovery & Self-Healing

**Retry Policies:**
- Configurable max attempts, delay strategies
- Fixed, linear, exponential backoff
- Jitter to prevent thundering herd
- Specific exception types to retry on

**Circuit Breaker Pattern:**
- Prevent cascade failures
- Automatic recovery after cooldown
- Configurable failure thresholds

**Compensation Actions:**
- Define rollback actions for each task
- Enable workflow-level rollback on failure
- Better than "rewind" which has side-effect issues

### 7. FastAPI Server Auto-Generation

**API Endpoints to Generate:**
- `GET /flows` - List all registered flows
- `POST /flows/{flow_id}/execute` - Start workflow execution
- `GET /flows/{flow_id}/sessions` - List executions for a flow
- `GET /sessions/{execution_id}` - Get execution details
- `POST /sessions/{execution_id}/pause` - Pause execution
- `POST /sessions/{execution_id}/resume` - Resume execution
- `DELETE /sessions/{execution_id}` - Delete execution

**Request/Response Models:**
- Use Pydantic models for all API data
- Include pagination for list endpoints
- Consistent error response format

**Server Discovery:**
- Dynamically discover Flow instances from user code
- Auto-register all flows found in specified Python file
- No manual registration required

### 8. CLI Implementation

**`water dev` command:**
- Load flows from Python file (default: flows.py)
- Start FastAPI development server
- Support --host, --port, --reload options
- Display registered flows on startup

**`water validate` command:**
- Validate flow definitions without running
- Check for circular dependencies
- Verify task configurations

**`water inspect` command:**
- Inspect specific workflow execution
- Show current state, completed steps, outputs
- Useful for debugging

### 9. Key Implementation Details

**Type Safety:**
- Use Pydantic models for all data structures
- Generic Task class with proper input/output typing
- Runtime validation of all inputs and outputs

**Error Handling:**
- Comprehensive exception handling at every level
- Structured logging with correlation IDs
- Failed tasks don't crash entire workflow

**Performance:**
- Async/await throughout for I/O operations
- Efficient dependency resolution algorithm
- Minimal serialization overhead

**Monitoring:**
- Structured logging for all operations
- Execution time tracking
- Success/failure metrics collection

### 10. Usage Example Structure
Users should be able to write workflows like this:

```python
# User defines tasks
class MyInput(BaseModel):
    value: int

class MyOutput(BaseModel):
    result: int

class DoubleTask(Task[MyInput, MyOutput]):
    def __init__(self):
        super().__init__("double", "Double the input value", MyInput, MyOutput)
    
    async def execute(self, input_data: MyInput, context: TaskContext) -> MyOutput:
        return MyOutput(result=input_data.value * 2)

# User builds workflow with clean API
flow = Flow("my_flow", "Example workflow")
flow.then(DoubleTask()) \
    .then(DoubleTask()) \
    .branch([
        [lambda x: x.result > 10, LogTask("High value")],
        [lambda x: x.result <= 10, LogTask("Low value")]
    ]) \
    .parallel([EmailTask(), SlackTask()]) \
    .for(ProcessItemTask())

# User runs: water dev flows.py
# Server auto-starts with APIs for this flow
```

### 11. Implementation Priority

**Phase 1 (Core):**
1. Task and Flow base classes
2. Basic execution engine
3. SQLite storage backend
4. Simple sequential workflows

**Phase 2 (Control Flow):**
1. Conditional branching
2. Parallel execution
3. For each loops
4. Nested workflows

**Phase 3 (Recovery):**
1. Retry policies
2. Error handling
3. Compensation patterns
4. Circuit breakers

**Phase 4 (Server/CLI):**
1. FastAPI auto-generation
2. CLI commands
3. Development server
4. Inspection tools

### 12. Critical Design Decisions

**No True "Rewind":**
- Instead of rewinding to previous steps, use compensation actions
- Rewinding creates problems with side effects (API calls, database writes)
- Compensation is more reliable and industry-standard

**Event Sourcing for Audit:**
- Store all workflow events, not just final state
- Enables complete audit trail and debugging
- Supports replay for testing and development

**Immutable Snapshots:**
- Workflow state snapshots are immutable
- New snapshot created for each state change
- Enables reliable pause/resume without corruption

**Storage Abstraction:**
- Start with SQLite but design for multiple backends
- PostgreSQL and Redis support planned for future
- Clean interface makes swapping backends easy

This framework should feel familiar to users of workflow engines like Temporal, Prefect, or Airflow, but with the simplicity and developer experience inspired by Mastra's approach. The fluent API design with `.then()`, `.branch()`, `.parallel()`, `.while()`, and `.for()` makes building workflows intuitive and readable.