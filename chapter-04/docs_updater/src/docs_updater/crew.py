import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from mcp import StdioServerParameters
from crewai_tools import MCPServerAdapter

from docs_updater.tools.scoped_file_tools import get_scoped_file_tools


@CrewBase
class DocsUpdater():
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	def __init__(self, docs_base_directory: str = "", verbose: bool = True):
		self.docs_base_directory = docs_base_directory
		self.verbose = verbose
		self._mcp_adapter = None
		self._browser_tools = None

	def _get_browser_tools(self):
		"""Lazily initialize and return Playwright MCP tools."""
		if self._browser_tools is None:
			server_params = StdioServerParameters(
				command="npx",
				args=["@playwright/mcp@latest"],
				env=os.environ.copy(),
			)
			adapter = MCPServerAdapter(server_params, connect_timeout=60)
			try:
				self._browser_tools = list(adapter.__enter__())
				self._mcp_adapter = adapter
			except Exception:
				# Ensure the adapter/subprocess is cleaned up if startup fails
				try:
					adapter.__exit__(None, None, None)
				except Exception:
					pass
				raise
		return self._browser_tools

	def close(self):
		"""Close the MCP adapter and browser."""
		if self._mcp_adapter is not None:
			self._mcp_adapter.__exit__(None, None, None)
			self._mcp_adapter = None
			self._browser_tools = None

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
		return Agent(
			config=self.agents_config['screenshotter'],
			allow_delegation=False,
			tools=self._get_browser_tools(),
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
