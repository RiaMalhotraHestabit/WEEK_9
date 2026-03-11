from agents.research_agent import ResearchAgent
from agents.summarizer_agent import SummarizerAgent
from agents.answer_agent import AnswerAgent

from llm.model_loader import LocalLLM

def main():

    llm = LocalLLM()

    research_agent = ResearchAgent(llm)
    summarizer_agent = SummarizerAgent(llm)
    answer_agent = AnswerAgent(llm)

    query = "How do airplanes fly?"

    research = research_agent.run(query)
    print("Research Agent Output:")
    print(research)

    summary = summarizer_agent.run(research)
    print("\nSummary:")
    print(summary)

    final_answer = answer_agent.run(summary)
    print("\nFinal Answer:\n")
    print(final_answer)


if __name__ == "__main__":
    main()