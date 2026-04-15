from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

from product_catalog.models import (
    CatalogFindings,
    ProductFeatures,
    ProductListing,
)
from product_catalog.tools.catalog_similarity_tool import CatalogSimilarityTool

gemini = LLM(model="gemini/gemini-3-flash-preview")


@CrewBase
class ProductCatalogCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def image_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config["image_analyzer"],
            llm=gemini,
            verbose=True,
        )

    @agent
    def description_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["description_writer"],
            llm=gemini,
            verbose=True,
        )

    @agent
    def catalog_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["catalog_analyst"],
            llm=gemini,
            verbose=True,
            tools=[CatalogSimilarityTool()],
        )

    @task
    def image_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["image_analysis_task"],
            output_pydantic=ProductFeatures,
        )

    @task
    def description_writing_task(self) -> Task:
        return Task(
            config=self.tasks_config["description_writing_task"],
            output_pydantic=ProductListing,
        )

    @task
    def catalog_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["catalog_analysis_task"],
            output_pydantic=CatalogFindings,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
