from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from docs_updater.tools.scoped_file_tools import get_scoped_file_tools
from docs_updater.tools.browser_tools import get_browser_tools


@CrewBase
class DocsUpdater():
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	def __init__(self, docs_base_directory: str = "", verbose: bool = True):
		self.docs_base_directory = docs_base_directory
		self.verbose = verbose

	@agent
	def docs_updater(self) -> Agent:
		return Agent(
			config=self.agents_config['docs_updater'],
			tools=get_scoped_file_tools(self.docs_base_directory),
			allow_delegation=True,  # Can delegate screenshot work to screenshotter
			verbose=self.verbose,
		)

	@agent
	def screenshotter(self) -> Agent:
		# Screenshots go directly into the images/ subdirectory
		images_dir = f"{self.docs_base_directory}/images"
		return Agent(
			config=self.agents_config['screenshotter'],
			allow_delegation=False,
			tools=get_browser_tools(docs_base_directory=images_dir),
			verbose=self.verbose,
		)

	@task
	def update_docs(self) -> Task:
		return Task(
			config=self.tasks_config['update_docs'],
			agent=self.docs_updater(),
		)

	# Note: screenshotter agent has no pre-defined task.
	# It is invoked via delegation when docs_updater needs screenshots.

	@crew
	def crew(self) -> Crew:
		return Crew(
			agents=self.agents,
			tasks=self.tasks,
			process=Process.sequential,
			verbose=self.verbose,
		)
