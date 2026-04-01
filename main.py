from fasthtml.common import *
import asyncio
from myapps.circare import *
from uuid import uuid4
import markdown
import time


#from myapps.circare import 

# -----------------------------
# App setup
# -----------------------------
app, rt = fast_app(live = True)

#jobs = {job_id : "uuid", {query : "The keywords for job", status : "Queued/Processing/Complete", status_messages : [list of comments], report : "None/Full report"}}

from myapps.jobs import jobs

PRIMARY = "#1a73e8"
TEXT = "#202124"
MUTED = "#5f6368"
BORDER = "#dfe1e5"
BG = "#ffffff"
SUBTLE = "#f8f9fa"


def shell(*children, title="Circare"):
    """Shared document wrapper."""
    return (
        Title(title),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Style(f"""
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                font-family: Arial, Helvetica, sans-serif;
                color: {TEXT};
                background: {BG};
            }}
            a {{ color: {PRIMARY}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .home-wrap {{
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 24px;
            }}
            .brand {{
                font-size: 4.5rem;
                font-weight: 700;
                letter-spacing: -0.05em;
                margin-bottom: 24px;
                color: {PRIMARY};
            }}
            .search-form {{ width: min(680px, 92vw); }}
            .search-box {{
                display: flex;
                align-items: center;
                gap: 12px;
                width: 100%;
                border: 1px solid {BORDER};
                border-radius: 999px;
                padding: 14px 18px;
                box-shadow: 0 1px 6px rgba(32,33,36,0.08);
                background: white;
            }}
            .search-box:hover, .search-box:focus-within {{
                box-shadow: 0 2px 10px rgba(32,33,36,0.14);
            }}
            .search-input {{
                border: none;
                outline: none;
                width: 100%;
                font-size: 1.05rem;
                background: transparent;
                color: {TEXT};
            }}
            .search-actions {{
                margin-top: 28px;
                display: flex;
                justify-content: center;
                gap: 12px;
                flex-wrap: wrap;
            }}
            .btn {{
                border: 1px solid transparent;
                background: {SUBTLE};
                color: {TEXT};
                padding: 10px 18px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.95rem;
            }}
            .btn:hover {{ border-color: {BORDER}; }}
            .results-page {{ padding: 20px 24px 60px; }}
            .topbar {{
                display: flex;
                align-items: center;
                gap: 24px;
                flex-wrap: wrap;
                border-bottom: 1px solid #ebebeb;
                padding-bottom: 18px;
            }}
            .brand-small {{
                font-size: 2rem;
                font-weight: 700;
                color: {PRIMARY};
                line-height: 1;
            }}
            .results-form {{ width: min(720px, 100%); flex: 1; }}
            .results-layout {{
                max-width: 920px;
                margin-left: 108px;
                padding-top: 22px;
            }}
            .meta {{ color: {MUTED}; font-size: 0.95rem; margin-bottom: 20px; }}
            .result {{ margin-bottom: 28px; }}
            .result-url {{ color: #188038; font-size: 0.92rem; margin-bottom: 4px; }}
            .result-title {{ font-size: 1.3rem; line-height: 1.3; display: inline-block; margin-bottom: 6px; }}
            .result-snippet {{ color: #4d5156; line-height: 1.58; font-size: 0.96rem; }}
            .loader {{
                display: inline-flex;
                align-items: center;
                gap: 10px;
                color: {MUTED};
                font-size: 0.95rem;
            }}
            .spinner {{
                width: 18px;
                height: 18px;
                border: 2px solid #dadce0;
                border-top-color: {PRIMARY};
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
            }}
            .search-tips {{
                margin-top: 18px;
                color: {MUTED};
                font-size: 0.92rem;
                text-align: center;
            }}
            .empty-state {{
                border: 1px solid #ebebeb;
                border-radius: 12px;
                padding: 18px;
                background: #fff;
            }}
            mark {{ background: #fff3b0; padding: 0 2px; }}
            @keyframes spin {{
                from {{ transform: rotate(0deg); }}
                to {{ transform: rotate(360deg); }}
            }}
            @media (max-width: 900px) {{
                .results-layout {{ margin-left: 0; }}
            }}
        """),
        Body(*children),
    )




# -----------------------------
# Views
# -----------------------------
@rt("/circare")
def circare():
    current_job_id = str(uuid4())
    return shell(
        Main(
            Div("Circare", cls="brand"),
            Form(
                Div(
                    Span("🔎"),
                    Input(
                        name="q",
                        placeholder="Search the web to write report",
                        cls="search-input",
                        autofocus=True,
                        autocomplete="off",
                    ),
                    cls="search-box",
                ),
                Div(
                    Button("Circare Search & Write Report", cls="btn", type="submit"),
                    cls="search-actions",
                ),
                action=f"/circare-search/{current_job_id}",
                method="post",
                cls="search-form",
            ),
            P(
                "Disclaimer: This app is developed by Dr Mazhar Hussain on top of Python. It is only for demonstration purpose. The user of the app should consume information on their own risk.",
                cls="search-tips",
            ),
            cls="home-wrap",
        ),
        title="Circare",
    )

@rt("/circare-search/{current_job_id}")
def search_page(current_job_id : str, q: str = ""):
    q = q.strip()
    is_allowed, reason = evaluate_query_safety(q)

    if current_job_id not in jobs:
        jobs[current_job_id] = {
            "query": q,
            "status": "Queued",
            "status_messages": [],
            "report": "None",
            "task_started": False,
            "start_time": None,
        }
        if not is_allowed:
            jobs[current_job_id]["status"] = "Complete"
            jobs[current_job_id]["task_started"] = True
            jobs[current_job_id]["status_messages"] = [reason]
            jobs[current_job_id]["report"] = ReportData(
                short_summary=reason,
                markdown_report=(
                    "## Request blocked\n\n"
                    "This query cannot be processed due to safety policy.\n\n"
                    "Please ask a legal, non-harmful, and non-explicit topic."
                ),
                follow_up_questions=[
                    "What topics are safe to research online?",
                    "How can I research controversial topics responsibly?",
                    "How do I evaluate source quality and bias?",
                ],
            )
    elif q:
        # Keep original job unless a non-empty query is explicitly resubmitted.
        jobs[current_job_id]["query"] = q
    current_query = jobs[current_job_id]["query"]
    
    #Status = Queued/Processing/Complete
    #Status_messages
    #report == None/Full report
    
    return shell(
        Main(
            Div(
                A("Circare", href="/circare", cls="brand-small"),
                
                cls="topbar",
            ),
            Div(
                Div(id="results-meta"),
                Div(
                    Div(Div(cls="spinner"), Span("Loading and processing results..."), cls="loader"),
                    id="results-container",
                    hx_get=f"/results_fragment?current_job_id={current_job_id}",
                    hx_trigger="load",
                    hx_target="#results-container",
                    hx_swap="innerHTML",
                ),
                cls="results-layout",
            ),
            cls="results-page",
        ),
        title=f"{current_query} - Circare" if current_query else "Circare results",
    )

@rt("/results_fragment")
async def result_fragment(current_job_id : str):
    if current_job_id not in jobs:
        return Div(P("This job no longer exists. Please start a new search."), cls="container")

    if jobs[current_job_id]["status"] == "Complete":
        report_data = jobs[current_job_id]["report"]
        report_text = report_data.markdown_report if hasattr(report_data, "markdown_report") else str(report_data)
        report_html = markdown.markdown(report_text, extensions=["extra", "tables"])
        return Div(
            NotStr(report_html),
            cls="container",
        )
    else:
        if not jobs[current_job_id]["task_started"]:
            jobs[current_job_id]["start_time"] = time.perf_counter()
            asyncio.create_task(circare_main(current_job_id=current_job_id))
            jobs[current_job_id]["task_started"] = True

    return Div(
        Div(Div(cls="spinner"), Span("Loading and processing results..."), cls="loader"),
        id="status-panel",
        hx_get=f"/status_checker?current_job_id={current_job_id}",
        hx_trigger="load, every 1s",
        hx_target="this",
        hx_swap="outerHTML",
    )
    
    
@rt("/status_checker")
async def status_checker(current_job_id: str):    
    if current_job_id not in jobs:
        return Div(P("This job no longer exists. Please start a new search."), cls="container")

    if jobs[current_job_id]['status'] == "Complete":
        report_data = jobs[current_job_id]["report"]
        report_text = report_data.markdown_report if hasattr(report_data, "markdown_report") else str(report_data)
        report_html = markdown.markdown(report_text, extensions=["extra", "tables"])
        return Div(
            NotStr(report_html),
            cls="container",
        )

        
    else:
        current_status_messages = jobs[current_job_id]['status_messages']
        start_time = jobs[current_job_id].get("start_time")
        if start_time is None:
            time_elapsed = 0.0
        else:
            time_elapsed = time.perf_counter() - start_time

        
        status_list_items = []
        for current_message in current_status_messages:
            list_item = Li(
                current_message,
                cls = "server-message"
            )
            status_list_items.append(list_item)
        current_messages_list = Ul(
            *status_list_items,
            cls = "status-list-itms"
        )

        page_content = Div(
            H2("Job Updates"),
            P("Following is the continuously updating state of the submitted job."),
            current_messages_list,
            P(f"""Elapsed time: {time_elapsed:.2f} seconds"""),
            id="status-panel",
            hx_get=f"/status_checker?current_job_id={current_job_id}",
            hx_trigger="every 1s",
            hx_target="this",
            hx_swap="outerHTML",
            cls="container",
        )
        return page_content
        


serve()
