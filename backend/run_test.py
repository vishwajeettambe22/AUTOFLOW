import asyncio
import uuid
import structlog
import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

from api.main import execute_workflow
from memory.postgres_store import init_db

# Configure simple logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)

async def test_run():
    # Initialize DB (like FastAPI lifespan)
    print("Initializing Database...")
    await init_db()
    
    run_id = str(uuid.uuid4())
    user_task = "Find the capital of France and write a python script to print it."
    
    print(f"\n Starting execution for task: '{user_task}'")
    print(f"Run ID: {run_id}\n")
    
    try:
        # Run workflow
        result = await execute_workflow(run_id, user_task)
        
        print("\n Workflow Completed Successfully!")
        print("\n" + "="*50)
        print("FINAL REPORT:")
        print("="*50)
        print(result.get("final_report", "No final report generated."))
        print("\n" + "="*50)
        
        print("\n Agent Statuses:")
        print(f"- Planner:    {result.get('planner_status', 'N/A')}")
        print(f"- Researcher: {result.get('researcher_status', 'N/A')}")
        print(f"- Coder:      {result.get('coder_status', 'N/A')}")
        print(f"- Reviewer:   {result.get('reviewer_status', 'N/A')}")
        print(f"- Critic:     {result.get('critic_status', 'N/A')}")
        print(f"- Reporter:   {result.get('reporter_status', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ Workflow Failed with Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_run())
