import argparse
import asyncio
import os

import aiofiles
from google import genai
from google.genai.types import Tool, GenerateContentConfig
import validators

from docs import create_google_doc, update_google_doc
from spreadsheet import create_sheet_service, create_rows, SPREADSHEET_ID, update_sheet
from utils import Job, cover_letter_templates

CV = ""
model_id = "gemini-2.0-flash"
url_context_tool = Tool(url_context=genai.types.UrlContext)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_DOCS_LINK = "https://docs.google.com/document/d/"
USER_PROFILE = """"a British junior Python developer and product manager who is looking to work for a startup in the UK or Europe, 
                preferably in a job with a focus on AI."""


def fetch_jobs_content(link, user_profile = USER_PROFILE):
    """Fetch jobs from a link"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=model_id,
            contents=f"""Follow this link ({link}) and find all jobs on the page suitable for {user_profile}.
            Return all details of all suitable jobs. 
            Include the job source for each job. The job source should be the name of the host of the link e.g. Hacker News, LinkedIn.
            Return nothing else besides the jobs information""",
            config=GenerateContentConfig(
                tools=[url_context_tool],
                response_modalities=["TEXT"],
            ),
        )
    except Exception as e:
        print(f"Job Fetching Error: {e}")
        return None
    return response


def structure_jobs_content(jobs_content):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=model_id,
            contents=f"""Return the job information in structured json format for the text below. 
            For each job, provide a value for each of the following attributes: {Job.model_fields.items()}
            Where a value for an attribute is not available, 
            put a default value that is falsy in Python e.g. the empty string or an empty list.
            {jobs_content}""",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[Job],
            },
        )
    except Exception as e:
        print(f"Structuring Jobs Content Error: {e}")
        return None
    return response


async def write_cover_letter(job):
    """Write a cover letter for the job"""
    if not isinstance(job, Job):
        raise TypeError

    cover_letter_link = cover_letter_templates.get(job.job_type, "")
    if not cover_letter_link or not CV:
        return ""
    async with aiofiles.open(cover_letter_link, mode = 'r') as f:
        cover_letter_template = await f.read()

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = await client.aio.models.generate_content(
            model=model_id,
            contents=f"""Write a cover letter for the job {job.job_title} at company {job.company} based on the following template: {cover_letter_template}.
        The job description is: {job.job_description}.
        The job type is: {job.job_type}.
        The company description is: {job.company_description}.
        The technologies used in the job are: {job.technologies}.
        The job source is {job.job_source}.
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
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = await client.aio.models.generate_content(
                model=model_id,
                contents=f"""Follow this job page link ({job.job_link}). 
            Find any new information on the page for the job with the current state {job.model_dump()}. 
            Return the updated job state including all job fields.
            If there is no useful extra information in the job page link, just return the current job state""",
                config=GenerateContentConfig(
                    tools=[url_context_tool],
                    response_modalities=["TEXT"],
                ),
            )
            response = await client.aio.models.generate_content(
                model=model_id,
                contents=f"""Return the job information below in structured json format.
                {response.text}""",
                config={
                    "response_mime_type": "application/json",
                    "response_schema": Job,
                },
            )
            updated_job = response.parsed
            if updated_job:
                job = updated_job
        except Exception as e:
            print(f"Follow Up Link Error: {e}")
    return job


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
    
    parser = argparse.ArgumentParser(description='AI Jobs Project - Find and process job listings')
    parser.add_argument('user_profile', help='Profile of the user for whom the program is looking for jobs')
    args = parser.parse_args()
    user_profile = args.user_profile if args.user_profile else USER_PROFILE

    link = input("Provide a jobs link: ")
    while True:
        if validators.url(link):
            break
        link = input(f"{link} is not a valid address. Please provide a valid link: ")

    response = fetch_jobs_content(link, user_profile=user_profile)

    if response and response.text:
        response = structure_jobs_content(response.text)
        if response and response.parsed:
            jobs = response.parsed
            if not jobs:
                print("No jobs found")
                return
        else:
            print("No jobs found")
            return

    # get more info on jobs from job link pages
    updated_jobs = await follow_up_links(jobs)

    # AI generate cover letters
    letters = await write_cover_letters(updated_jobs)

    # create cover letter doc titles
    titles = [f"{job.job_title} at {job.company} Cover Letter" for job in updated_jobs]

    letter_ids = await store_cover_letters_in_docs(letters, titles)

    rows = create_rows(updated_jobs)

    # add cover letter links
    rows = [
        row + [GOOGLE_DOCS_LINK + letter_id] for row, letter_id in zip(rows, letter_ids)
    ]

    # store job info and links to cover letters in spreadsheet
    store_jobs_in_spreadsheet(sheet_service, SPREADSHEET_ID, rows)


if __name__ == "__main__":
    with open("cv.txt") as f:
        CV = f.read()
    asyncio.run(main())
