# Agentic Workflow Implementation

A modular, scalable agentic workflow implementation using Langgraph and LangChain. This project demonstrates a multi-agent system that can break down complex queries into subtasks, execute them, and provide feedback on the results.

## Features

- Task planning and decomposition using LLM
- Modular tool execution with retry logic
- Result reflection and quality assessment
- Dynamic task queue management
- Comprehensive error handling and logging

## Prerequisites

- Python 3.10 or higher
- OpenAI API key
- Tavily API key

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd agentic-workflow
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

## Usage

Run the main script:
```bash
python main.py
```

Enter your query when prompted. The system will:
1. Break down your query into subtasks
2. Execute each subtask using appropriate tools
3. Analyze the results for accuracy
4. Provide detailed feedback on the execution

Example query:
```
Enter your query: Find the average temperature in Tokyo and compare it to New York.
```

## Project Structure

- `agents/`: Contains agent implementations
  - `planner_agent.py`: Breaks down queries into subtasks
  - `tool_agent.py`: Executes tasks using available tools
  - `reflector_agent.py`: Analyzes task results
  - `task_manager.py`: Manages task queue and state
- `tools/`: Tool implementations
- `workflows/`: Workflow definitions using Langgraph
- `utils/`: Utility functions and helpers
- `config/`: Configuration files
- `tests/`: Unit and integration tests

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 