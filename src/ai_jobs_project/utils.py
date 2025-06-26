import enum
from pydantic import BaseModel, Field


class JobType(str, enum.Enum):
    SOFTWARE_ENGINEER = "Software Engineer"
    PRODUCT_MANAGER = "Product Manager"
    DATA_SCIENTIST = "Data Scientist"
    DATA_ENGINEER = "Data Engineer"
    PYTHON_DEVELOPER = "Python Developer"
    AI_DEVELOPER = "AI Developer"
    AI_ENGINEER = "AI Engineer"


class Job(BaseModel):
    job_type: JobType = Field(description="The type of job")
    job_title: str = Field(description="The job title")
    company: str = Field(description="The name of the company")
    salary: str = Field(description="The salary of the job")
    location: str = Field(description="The location of the job")
    contact_email: str = Field(description="The email of the contact person")
    company_link: str = Field(description="The link to the company")
    job_link: str = Field(description="The link to the job")
    technologies: list[str] = Field(description="The technologies used in the job")
    job_description: str = Field(description="The description of the job")
    company_description: str = Field(description="The description of the company")
    job_source: str = Field(description="Source of job information")


cover_letter_templates = {
    job_type: "letter_templates/"
    + "_".join(job_type.value.lower().split(" "))
    + "_template.txt"
    for job_type in JobType
}
