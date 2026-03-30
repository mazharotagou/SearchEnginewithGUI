from agents import Agent, trace, Runner, WebSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv, find_dotenv
import asyncio
import os
from datetime import datetime

load_dotenv(override = True)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

#Planner agent that findsout relevant keywords
class WebSearchItem(BaseModel):
    query : str = Field(description = "The term that needs to be searched.")
    reason: str = Field(description = " The reasoning why the query/keyword is relevant to the topic. ")

class WebSearchPlan(BaseModel):
    searches : list[WebSearchItem] = Field(description = " The list of search terms and reasonings that needs to be searched ")

async def search_planner(query : str):
    """ It plans the  search by finding a number of relevant keywords or terms along with reasons. """
    NUMBER_OF_SEARCHES = 3
    INSTRUCTIONS = f""" You  are a search planner who takes query and identifies {NUMBER_OF_SEARCHES} of terms relevant to query. \
        You come up with the queries along with reasoning why do you think those terms are relevant. While writing reasoning, be concise and write one liners."""
    query = query
    planner_agent = Agent(name = "Planner_Agent", model = "gpt-4o-mini", instructions = INSTRUCTIONS, output_type= WebSearchPlan)
    
    result = await Runner.run(planner_agent, query)
    return result.final_output


#Searching strategy item by item

async def search(query_reason : WebSearchItem):
    """ It is used for searching the information on the query provided. """
    INSTRUCTIONS = "You are a research assistant. Given a search term, you search the web for that term and \
        produce a concise summary of the results. The summary must 2-3 paragraphs and less than 300 \
        words. Capture the main points. Write succintly, no need to have complete sentences or good \
        grammar. This will be consumed by someone synthesizing a report, so it's vital you capture the \
        essence and ignore any fluff. Do not include any additional commentary other than the summary itself."

    message = f""" Query to be searched is : {query_reason.query} \n The reason of the query is : {query_reason.reason} """
    search_agent = Agent(name="Search_Agent", model = "gpt-4o-mini", instructions = INSTRUCTIONS)
    result = await Runner.run(search_agent, message)
    result = result.final_output
    return result

#, tools=[WebSearchTool(search_context_size="low")], model_settings=ModelSettings(tool_choice="required")


async def search_process(searches : WebSearchPlan):
    """ It searches each term one by one and compiles the results in the form of a list object. """
    tasks = []
    searches = searches
    #print ("searches look like this : ", searches)
    for search_ in searches.searches:
        task = asyncio.create_task(search(search_))
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    print (results)
    return results

#Report Writer

class ReportData(BaseModel):
    short_summary: str = Field(description="A short 2-3 sentence summary of the findings.")
    markdown_report: str = Field(description="The final report")
    follow_up_questions: list[str] = Field(description="Suggested topics to research further")

async def report_writer(query : str, search_results : list):
    message = f""" Search term for writing report : {query} \
                Sources information to be used for writing reports ; {search_results} """
    INSTRUCTIONS = f""" You are a senior researcher tasked with writing a cohesive report for a research query. 
                    You will be provided with the original query, and some initial research done by a research assistant.\n
                    You should first come up with an outline for the report that describes the structure and 
                    flow of the report. Then, generate the report and return that as your final output.\n
                    The final output should be in markdown format, and it should be lengthy and detailed. Aim 
                    for 5-10 pages of content, at least 1000 words. """

    writer_agent = Agent(name = "Writer_Agent", model = "gpt-4o-mini", instructions = INSTRUCTIONS, output_type = ReportData)
    report_ = await Runner.run(writer_agent , message)
    report_ = report_.final_output
    return report_

async def circare_main(to_search : str):
    #current_datetime = datetime.fromtimestamp()
    with trace(f"Circare_Trace"):
        to_search = to_search
        query = f"""query : {to_search}"""
        searches = await search_planner(query)
        searching = await search_process(searches)
        report_writing = await report_writer(to_search , searching)
        return report_writing

