import os
from dotenv import load_dotenv
from typing import Dict, Any
from workflow.main_workflow import create_workflow

def init_state(query: str) -> Dict[str, Any]:
    """Initialize workflow state with all required fields."""
    return {
        "query": query,
        "tasks": [],
        "results": [],
        "reflection": {},
        "final_response": "",
        "iteration": 0,
        "max_iterations": 3,
        "error_message": ""
    }

def main():
    # Load environment variables
    load_dotenv()
    
    # Verify required API keys
    required_keys = ["GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        print(f"Error: Missing required API keys: {', '.join(missing_keys)}")
        print("Please set them in your .env file")
        return

    try:
        # Create workflow
        workflow = create_workflow()
        
        # Get user query
        query = input("Enter your query: ")
        if not query.strip():
            print("Error: Query cannot be empty")
            return
        
        # Initialize state and run workflow
        initial_state = init_state(query)
        final_state = workflow.invoke(initial_state)
        
        # Check for errors
        if final_state.get("error_message"):
            print(f"\nError occurred: {final_state['error_message']}")
            return
        
        # Print results
        print("\nWorkflow completed!")
        final_response = final_state.get("final_response")
        if final_response:
            print("\nFinal Response:")
            print(final_response)
        else:
            print("No results were generated.")
    
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Please try again with a different query or check your API keys.")

if __name__ == "__main__":
    main() 