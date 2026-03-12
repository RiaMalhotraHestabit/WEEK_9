import asyncio
from agents.research_agent import research_agent
from agents.summarizer_agent import summarizer_agent
from agents.answer_agent import answer_agent

async def run_pipeline(query):

    print("\nUser:", query)

    research = await research_agent.run(task=query)
    research_text = research.messages[-1].content
    print("\nResearch Agent:\n", research_text)

    summary = await summarizer_agent.run(task=research_text)
    summary_text = summary.messages[-1].content
    print("\nSummarizer Agent:\n", summary_text)

    answer = await answer_agent.run(task=summary_text)
    answer_text = answer.messages[-1].content
    print("\nFinal Answer:\n", answer_text)

async def main():

    query = "Why is the sky blue?"
    await run_pipeline(query)


asyncio.run(main())