from agents import Agent, trace, Runner, WebSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel, EmailStr, Field
from dotenv import load_dotenv, find_dotenv
import asyncio
import os
from datetime import datetime
from uuid import uuid4
import re




from myapps.jobs import jobs

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
    INSTRUCTIONS = f"""You are a search planning assistant.

        Task:
        - Read the user's research topic.
        - Generate exactly {NUMBER_OF_SEARCHES} web search queries that best cover the topic.
        - For each query, provide a short one-line reason.

        Output rules:
        - Return only data that matches the required schema (WebSearchPlan).
        - Keep query text specific and high-signal.
        - Avoid duplicates and near-duplicates.

        Safety policy:
        - Do not generate or optimize search queries for harmful, illegal, exploitative, abusive, or explicit sexual content.
        - Do not assist with instructions for wrongdoing, evasion, weaponization, malware, fraud, or privacy invasion.
        - If the request appears unsafe, pivot to safe, high-level, educational alternatives in the same schema (neutral framing, prevention, legality, ethics, risk awareness)."""
    query = query
    planner_agent = Agent(name = "Planner_Agent", model = "gpt-4o-mini", instructions = INSTRUCTIONS, output_type= WebSearchPlan)
    
    result = await Runner.run(planner_agent, query)
    return result.final_output


#Searching strategy item by item

async def search(query_reason : WebSearchItem):
    """ It is used for searching the information on the query provided. """
    INSTRUCTIONS = """You are a research assistant.

        Task:
        - Given a search query and reason, produce a concise factual summary of likely results.
        - Write 2-3 short paragraphs, maximum 300 words total.

        Writing rules:
        - Focus on major facts, trends, and key entities.
        - Remove fluff, repetition, and opinionated language.
        - Do not include meta commentary, disclaimers, or process notes.

        Safety policy:
        - Refuse to provide content that enables harmful, illegal, exploitative, abusive, or explicit sexual activity.
        - Do not provide procedural instructions, tactics, or operational details for wrongdoing.
        - For unsafe intent, provide a brief safe alternative summary focused on prevention, legal context, ethics, or public safety."""

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


SAFETY_BLOCKLIST = {}


def evaluate_query_safety(query: str) -> tuple[bool, str]:
    """Return (is_allowed, reason)."""
    text = (query or "").strip().lower()
    if not text:
        return False, "Please enter a non-empty query."

    for category, patterns in SAFETY_BLOCKLIST.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return False, f"Blocked by safety policy: {category}."

    return True, "allowed"

async def report_writer(query : str, search_results : list):
    message = f""" Search term for writing report : {query} \
                Sources information to be used for writing reports ; {search_results} """
    INSTRUCTIONS = """You are a senior research writer.

        Task:
        - Use the user query and provided research notes to write a cohesive report.
        - Internally plan an outline, then produce the final answer directly.

        Output requirements:
        - Return output in the required ReportData schema.
        - `short_summary`: 2-3 sentences.
        - `markdown_report`: well-structured markdown with headings, clear sections, and synthesis across sources.
        - `follow_up_questions`: practical next research questions.
        - Target depth around 1000+ words when topic scope justifies it.

        Quality bar:
        - Be accurate, balanced, and explicit about uncertainty where evidence is weak.
        - Prefer clear synthesis over copying source phrasing.

        Safety policy:
        - Do not provide content that facilitates harmful, illegal, exploitative, abusive, or explicit sexual behavior.
        - Do not provide actionable instructions for wrongdoing.
        - If topic is unsafe, provide a safety-focused report (risk awareness, legal/ethical context, prevention, and harm reduction) within the same schema."""

    writer_agent = Agent(name = "Writer_Agent", model = "gpt-4o-mini", instructions = INSTRUCTIONS, output_type = ReportData)
    report_ = await Runner.run(writer_agent , message)
    report_ = report_.final_output
    return report_

async def circare_main(current_job_id : str):
    #current_datetime = datetime.fromtimestamp()
    to_search = jobs[current_job_id]['query']
    is_allowed, reason = evaluate_query_safety(to_search)
    if not is_allowed:
        jobs[current_job_id]["status_messages"].append(reason)
        jobs[current_job_id]["status"] = "Complete"
        jobs[current_job_id]["report"] = ReportData(
            short_summary=reason,
            markdown_report=(
                "## Request blocked\n\n"
                "This query cannot be processed due to safety policy.\n\n"
                "Try a safe alternative topic (education, prevention, legal awareness, ethics)."
            ),
            follow_up_questions=[
                "What are legal and ethical internet research practices?",
                "How can I improve online safety and digital wellbeing?",
                "How should harmful online content be reported safely?",
            ],
        )
        return jobs[current_job_id]["report"]

    jobs[current_job_id]['status'] = "Processing"
    jobs[current_job_id]['status_messages'].append("The search planning has initiated...")
    with trace(f"Circare_Trace"):
        to_search = to_search
        query = f"""query : {to_search}"""
        searches = await search_planner(query)
        jobs[current_job_id]['status_messages'].append("The search planning has completed...")
        jobs[current_job_id]['status_messages'].append("The search has been initiated on 3 most relevant keywords...")
        searching = await search_process(searches)
        jobs[current_job_id]['status_messages'].append("The material has been collected on the relevant keywords")
        jobs[current_job_id]['status_messages'].append("The report writing has begun")
        report_writing = await report_writer(to_search , searching)
        jobs[current_job_id]['status_messages'].append("The report writing has been successfully concluded")
        jobs[current_job_id]['status'] = "Complete"
        jobs[current_job_id]['report'] = report_writing
        return report_writing

