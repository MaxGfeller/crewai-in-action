from crewai_tools import SerperDevTool, SerperScrapeWebsiteTool 		#A

serper_dev_tool = SerperDevTool() 						#B
serper_scrape_website_tool = SerperScrapeWebsiteTool() 			#C

search_result = serper_dev_tool.run( 					#D
	search_query="What is the capital of Switzerland?"
)

website_result = serper_scrape_website_tool.run( 				#E
	url="https://www.crewai.com/use-cases"
)

print(search_result, website_result)
