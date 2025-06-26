import asyncio
import json
import os
import re

from google import genai
from google.genai.types import Tool, GenerateContentConfig
from pydantic import ValidationError
import validators

from docs import create_google_doc, update_google_doc
from spreadsheet import create_sheet_service, create_rows, SPREADSHEET_ID, update_sheet
from utils import Job, cover_letter_templates

CV = ""
model_id = "gemini-2.0-flash"
url_context_tool = Tool(url_context=genai.types.UrlContext)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_DOCS_LINK = "https://docs.google.com/document/d/"


def process_response(response_text):
    """Parse response and return iterable of Job instances"""
    response_text = re.sub(r"```json\n?|\n?```", "", response_text)
    # Find the JSON array in the text
    json_match = re.search(r"\[.*\]", response_text, re.DOTALL)
    if json_match:
        try:
            json_str = json_match.group(0)
            jobs_data = json.loads(json_str)

            jobs = []
            for job_data in jobs_data:
                try:
                    job = Job(**job_data)  # Convert each dictionary into a Job object
                    jobs.append(job)
                except ValidationError as e:
                    print("Validation error:", e)
                except Exception as e:
                    print(e)
            return jobs
        except:
            return ""


def fetch_jobs(link):
    """Fetch jobs from a link"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=model_id,
            contents=f"""Follow this link ({link}) and find all jobs on the page suitable for a UK-based junior Python developer or junior product manager who can relocate and has the right to work in the EU.
    Return found jobs as a list of objects in json format using the following model schema: {Job.model_json_schema()}. Return nothing else.
    Where a value for a job field is not available, the default value should be an object that is falsy in Python e.g. the empty string or an empty list.
    The job source should be the name of the host of the link e.g. Hacker News, LinkedIn {link}.""",
            config=GenerateContentConfig(
                tools=[url_context_tool],
                response_modalities=["TEXT"],
            ),
        )
    except Exception as e:
        print(f"Job Fetching Error: {e}")
        return None
    return response


async def write_cover_letter(job):
    """Write a cover letter for the job"""
    if not isinstance(job, Job):
        raise TypeError

    cover_letter_link = cover_letter_templates.get(job.job_type, "")
    if not cover_letter_link:
        return ""
    with open(cover_letter_link) as f:
        cover_letter_template = f.read()

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=model_id,
            contents=f"""Write a cover letter for the job {job.job_title} at company {job.company} based on the following template: {cover_letter_template}.
        The job description is: {job.job_description}.
        The job type is: {job.job_type}.
        The company description is: {job.company_description}.
        The technologies used in the job are: {job.technologies}.
        The cover letter is for the person with the following CV: {CV}.
        The cover letter should include references to elements of the technologies, 
        the job and company descriptions and relate these elements to elements in the user CV.
        Do NOT claim that the user has a skill or knowledge of or experience with a technology if it isnot referenced in the CV. 
        Return only the cover letter and nothing else.
        """,
        )

    except Exception as e:
        print(f"Cover Letter Error: {e}")
        return ""
    return response.text


async def write_cover_letters(jobs):
    """Write cover letters for the jobs"""
    tasks = (write_cover_letter(job) for job in jobs)
    return await asyncio.gather(*tasks)


async def follow_up_link(job):
    """Update job details where job link"""
    if not isinstance(job, Job):
        raise TypeError
    if job.job_link:
        try:
            client = genai.Client(
                api_key=GEMINI_API_KEY
            )  # move client creation outside the functions
            response = await client.aio.models.generate_content(
                model=model_id,
                contents=f"""Follow this job page link ({job.job_link}). 
            Find any new information on the page for the job with the current state {job.model_dump()}. 
            If the page contains more information on the job, update the job's job source to be {job.job_link}.
            Return the updated state in json format using the following schema: {Job.model_json_schema()}.""",
                config=GenerateContentConfig(
                    tools=[url_context_tool],
                    response_modalities=["TEXT"],
                ),
            )
            response_text = response.text
            # Remove any markdown code block indicators
            response_text = re.sub(r"```json\n?|\n?```", "", response_text)
            job_data = json.loads(response_text)
            return Job(**job_data)

        except Exception as e:
            print(f"Follow Up Link Error: {e}")
    return job  # if update failed, return existing job info


async def follow_up_links(jobs):
    """Follow up links to get more info on the jobs"""
    tasks = (follow_up_link(job) for job in jobs)
    return await asyncio.gather(*tasks)


def store_jobs_in_spreadsheet(service, spreadsheet_id, rows):
    """Store jobs in a spreadsheet"""
    update_sheet(service, spreadsheet_id, rows=rows, range="Sheet1!A:M")


async def store_cover_letter_in_doc(cover_letter, title):
    if cover_letter:
        document_id = await create_google_doc(title)
        if document_id:
            await update_google_doc(document_id, cover_letter)
        return document_id
    return ""


async def store_cover_letters_in_docs(cover_letters, titles):
    """Store cover letters in a Google Doc. Return links"""
    tasks = (
        store_cover_letter_in_doc(letter, title)
        for letter, title in zip(cover_letters, titles)
    )
    return await asyncio.gather(*tasks)


async def main():
    sheet_service = create_sheet_service()

    if not sheet_service:
        print("Google spreadsheets is not available")
        return
    if not GEMINI_API_KEY:
        print("Please set a Gemini API key")
        return

    link = input("Provide a jobs link: ")
    while True:
        if validators.url(link):
            break
        link = input(f"Please provide a valid link. {link} is not a valid address.")

    response = fetch_jobs(link)

    if response:
        jobs = process_response(response.text)
    else:
        print("No jobs found")
        return

    updated_jobs = await follow_up_links(
        jobs
    )  # get more info on jobs from job link pages

    letters = await write_cover_letters(updated_jobs)  # AI generate cover letters
    titles = [
        f"{job.job_title} at {job.company} Cover Letter" for job in updated_jobs
    ]  # create cover letter doc titles

    letter_ids = await store_cover_letters_in_docs(letters, titles)

    rows = create_rows(updated_jobs)
    rows = [
        row + [GOOGLE_DOCS_LINK + letter_id] for row, letter_id in zip(rows, letter_ids)
    ]  # add cover letter links
    store_jobs_in_spreadsheet(
        sheet_service, SPREADSHEET_ID, rows
    )  # store job info and links to cover letters in spreadsheet


if __name__ == "__main__":
    with open("cv.txt") as f:
        CV = f.read()
    asyncio.run(main())
