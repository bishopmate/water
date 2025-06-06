from water import Flow, create_task, FlowServer
from pydantic import BaseModel

# Define schemas
class NumberInput(BaseModel):
    value: int

class NumberOutput(BaseModel):
    value: int

# Create some example flows
simple_flow = Flow(id="simple_math", description="Simple math operations")
simple_flow.then(create_task(
    id="add_five",
    description="Add 5 to input",
    input_schema=NumberInput,
    output_schema=NumberOutput,
    execute=lambda params, context: {"value": params["input_data"]["value"] + 5}
)).register()

complex_flow = Flow(id="data_processing", description="Complex data processing")
complex_flow.then(create_task(
    id="multiply",
    description="Multiply by 2",
    input_schema=NumberInput,
    output_schema=NumberOutput,
    execute=lambda params, context: {"value": params["input_data"]["value"] * 2}
)).then(create_task(
    id="subtract",
    description="Subtract 1",
    input_schema=NumberOutput,
    output_schema=NumberOutput,
    execute=lambda params, context: {"value": params["input_data"]["value"] - 1}
)).register()

# Create server with flows
app = FlowServer(flows=[simple_flow, complex_flow]).get_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("example_server:app", host="0.0.0.0", port=8000, reload=True) 