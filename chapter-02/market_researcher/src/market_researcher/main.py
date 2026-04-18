import os
from crewai import Agent
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from pydantic import BaseModel

"""Create a single CrewAI agent that behaves like a market research analyst."""
agent = Agent(
    llm="openai/gpt-5-mini",
    role="Market Research Analyst",
    goal=(
        "Turn broad product category prompts into comprehensive competitive "
        "intelligence reports that help teams evaluate new opportunities."
    ),
    backstory=(
        "You have spent a decade synthesizing desk research, market reports, "
        "and customer insights for product strategy teams. You are analytical, "
        "methodical, and write in crisp business prose."
    ),
    verbose=True,
    tools=[
        SerperDevTool(),
        SerperScrapeWebsiteTool(),
    ]
)

def build_market_research_prompt(product_category: str) -> str:
    return (
        f"You are preparing a comprehensive competitive intelligence report on the "
        f"{product_category} market.\n\n"
        "1. Market Snapshot & Customer Needs: Explain the primary customer segments, "
        "use cases, pain points, and demand signals that define the category "
        "today.\n"
        "2. Competitive Landscape & Differentiators: Profile the leading and "
        "emerging competitors. Describe their positioning, marquee features, "
        "strengths, weaknesses, and unique differentiators.\n"
        "3. Pricing, Packaging, and Positioning Insights: Summarize pricing models, "
        "packaging tiers, and positioning strategies. Call out notable value "
        "propositions or messaging angles.\n"
        "Write in crisp business prose, structure the report with clear section "
        "headers, and finish with a concise executive summary. Use the tools provided to you to get the information you need."
    )

class CustomerNeeds(BaseModel):
    customer_needs: list[str]
    customer_segments: list[str]
    pain_points: list[str]
    demand_signals: list[str]

class Competitor(BaseModel):
    name: str
    description: str
    features: list[str]
    strengths: list[str]
    weaknesses: list[str]
    unique_differentiators: list[str]

class Positioning(BaseModel):
    pricing: str
    packaging: str
    positioning: str

class MarketResearch(BaseModel):
    executive_summary: str
    customer_needs: CustomerNeeds
    competitors: list[Competitor]
    positioning: Positioning

prompt = build_market_research_prompt(product_category="electric bikes")
report = agent.kickoff(prompt, response_format=MarketResearch)

print(report)
