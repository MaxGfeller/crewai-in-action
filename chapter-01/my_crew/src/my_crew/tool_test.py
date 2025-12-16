from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool

serper_dev_tool = SerperDevTool()
serper_scrape_website_tool = SerperScrapeWebsiteTool()

search_result = serper_dev_tool.run(search_query="What is the capital of Switzerland?")
print(search_result)

website_result = serper_scrape_website_tool.run(url="https://www.crewai.com/use-cases")
print(website_result)