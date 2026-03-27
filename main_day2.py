import asyncio
from orchestrator.planner import planner
from agents.worker_agent import worker_agent
from agents.validator import validator_agent
from autogen_agentchat.agents import AssistantAgent
from model_client import model_client

reflection_agent = AssistantAgent(
    name="reflection_agent",
    model_client=model_client,
    system_message="""
You are a reflection agent.

Your job:
- Understand all worker outputs
- Combine and refine them into a single answer
- Improve clarity, flow, and coherence
- Remove repetition

Rules:
- Do NOT mention workers or steps
- Do NOT explain what you changed
- Keep the answer clean and easy to read

Return only the final refined answer.
"""
)

async def run_pipeline(query):

    print("\nUSER:", query)

    #step-1: planning
    plan = await planner.run(task=query)
    plan_text = plan.messages[-1].content

    print("\nPLANNER STEPS:\n", plan_text)

    steps = [line for line in plan_text.split("\n") if line.strip()]

    #step-2: parallel workers
    tasks = []
    for i, step in enumerate(steps):
        tasks.append(
            worker_agent.run(
                task=f"Worker {i+1}\nTask: {step}"
            )
        )

    worker_results = await asyncio.gather(*tasks)

    outputs = [r.messages[-1].content for r in worker_results]

    print("\nWORKER OUTPUTS:")
    for o in outputs:
        print(o)

    combined = "\n".join(outputs)

    #step-3: reflection
    reflection = await reflection_agent.run(task=combined)
    reflection_text = reflection.messages[-1].content

    print("\nREFLECTION:\n", reflection_text)

    #step-4: validation
    final = await validator_agent.run(task=reflection_text)
    final_text = final.messages[-1].content

    print("\nFINAL ANSWER:\n", final_text)

async def main():

    query = input("Enter your query: ")
    await run_pipeline(query)

asyncio.run(main())