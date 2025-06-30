import os

from google import genai
from pydantic import BaseModel

from ai import (
    fetch_jobs_content,
    follow_up_links,
    store_cover_letters_in_docs,
    process_response,
    store_jobs_in_spreadsheet,
)
from utils import Job

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SYSTEM_INSTRUCTION = """You are an AI chatbot helping a user to find jobs to apply for.
Your job is: 1. To ask the user for job criteria
             2. To obtain links to job pages from the user
             3. To then extract job information from the job pages where the relevant jobs meet or nearly meet the user job criteria
             4. To then find out which of the extracted jobs the user is interested in
             5. To try to obtain more information on jobs of interest to the user via any links associated with those jobs
             6. To then create cover letters for jobs the user wants to apply for
             7. To record the information on all jobs of interest to the user in a Google spreadsheet"""


class State(BaseModel):
    all_jobs: list[Job]
    jobs_of_interest_to_user: list[Job]
    jobs_the_user_wants_to_apply_for: list[Job]


def llm(chat, prompt, config=None):
    try:
        if config:
            response = chat.send_message(prompt, config=config)
            return response.parsed
        else:
            response = chat.send_message(prompt)
            return response.text
    except:
        return "The model is currently unavailable."


def main():
    state = State()

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        chat = client.chats.create(
            model="gemini-2.0-flash", config={"system_instruction": SYSTEM_INSTRUCTION}
        )
        print(
            "Talk to the AI chatbot and pick a poet and a poem. The poem will be read out to you."
        )
    except:
        print("Cannot access LLM")
        return
    while True:
        pass


if __name__ == "__main__":
    main()
