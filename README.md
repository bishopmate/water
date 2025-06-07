# Water
**A multi-agent orchestration framework that works with any agent framework.**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Overview
Water is a production ready orchestration framework that enables developers to build complex multi-agent systems without being locked into specific agent framework. Whether you are using LangChain, CrewAI, Agno, or custom agents, Water provides the orchestration layer to coordinate and scale your multi-agent workflows.

### Key Features

- **Framework Agnostic** - Integrate any agent framework or custom implementation
- **Flexible Workflows** - Orchestrate complex multi-agent interactions with simple Python
- **Playground** - Run lightweight FastAPI server with all the flows you define

## Quick Start
### Installation

```bash
pip install water-ai
```

### Basic Usage

```python
import asyncio
from water import Flow, create_task
from pydantic import BaseModel

class NumberInput(BaseModel):
    value: int

class NumberOutput(BaseModel):
    result: int

def add_five(params, context):
    return {"result": params["input_data"]["value"] + 5}

math_task = create_task(
    id="math_task",
    description="Math task",
    input_schema=NumberInput,
    output_schema=NumberOutput,
    execute=add_five
)

flow = Flow(id="my_flow", description="My flow").then(math_task).register()

async def main():
    result = await flow.run({"value": 10})
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## Contributing

We welcome contributions from the community!

- Bug reports and feature requests
- Code contributions
- Documentation improvements
- Testing and quality assurance

## Roadmap

- Storage layer to store flow sessions and task runs
- Human in the loop support
- Retry mechanism for individual tasks

## License

Water is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
