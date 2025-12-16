from crewai import Agent, Crew, Process, Task
from crewai.knowledge.knowledge_config import KnowledgeConfig
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool
from seo_crew.tools.image_generation_tool import ImageGenerationTool
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.source.json_knowledge_source import JSONKnowledgeSource

about_us_md = TextFileKnowledgeSource(file_paths=["about-us.md"])
competitors_json = JSONKnowledgeSource(file_paths=["competitors.json"])

knowledge_config = KnowledgeConfig(results_limit=30, score_threshold=0.4)

@CrewBase
class SeoCrew():
  agents_config = 'config/agents.yaml'
  tasks_config = 'config/tasks.yaml'

  @agent
  def keyword_researcher(self) -> Agent:
    return Agent(
      config=self.agents_config['keyword_researcher'],
      verbose=True,
      tools=[SerperDevTool()]
    )

  @agent
  def topic_researcher(self) -> Agent:
    return Agent(
      config=self.agents_config['topic_researcher'],
      verbose=True,
      tools=[SerperDevTool(), SerperScrapeWebsiteTool()]
    )

  @agent
  def blog_post_writer(self) -> Agent:
    return Agent(
      config=self.agents_config['blog_post_writer'],
      verbose=True,
      tools=[ImageGenerationTool(base_path="./images")]
    )

  @task
  def keyword_research_task(self) -> Task:
    return Task(
      config=self.tasks_config['keyword_research_task'],
    )

  @task
  def topic_research_task(self) -> Task:
    return Task(
      config=self.tasks_config['topic_research_task'],
    )

  @task
  def blog_writing_task(self) -> Task:
    return Task(
      config=self.tasks_config['blog_writing_task'],
    )

  @crew
  def crew(self) -> Crew:
    return Crew(
      agents=self.agents,
      tasks=self.tasks,
      process=Process.sequential,
      verbose=True,
	  knowledge_sources=[about_us_md, competitors_json],
	  knowledge_config=knowledge_config,
    )
