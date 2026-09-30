import os
import time
import tempfile
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel
from pypdf import PdfReader
from docx import Document
from PIL import Image


from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(ENV_FILE)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY was not found in .env")

MODEL = "gemini-3.8-flash"

FALLBACK_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]

client = genai.Client(
    api_key=GEMINI_API_KEY
)


class Candidate(BaseModel):
    name: str
    email: str
    phone: str
    location: str
    education: list[str]
    experience: list[str]
    technical_skills: list[str]
    soft_skills: list[str]
    projects: list[str]
    certifications: list[str]


class ResumeQuality(BaseModel):
    score: int
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]


class ATSAnalysis(BaseModel):
    score: int
    issues: list[str]
    keywords_found: list[str]
    missing_keywords: list[str]
    suggestions: list[str]


class SkillUpgrade(BaseModel):
    skill: str
    reason: str
    priority: str


class ResumeAnalysis(BaseModel):
    candidate: Candidate
    resume_quality: ResumeQuality
    ats_analysis: ATSAnalysis
    skill_upgrades: list[SkillUpgrade]

class JobMatchAnalysis(BaseModel):
    match_score: int
    summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    matched_requirements: list[str]
    missing_requirements: list[str]
    recommendations: list[str]
    skill_upgrades: list[SkillUpgrade]


def extract_pdf_text(file_path):
    reader = PdfReader(file_path)

    text = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text.append(page_text)

    return "\n".join(text)


def extract_docx_text(file_path):
    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n".join(paragraphs)


def extract_txt_text(file_path):
    return Path(file_path).read_text(
        encoding="utf-8",
        errors="ignore"
    )


def build_prompt(resume_text):
    return f"""
You are an expert resume analyst and ATS evaluator.

Analyze the following resume carefully.

Extract factual information only from the resume.

Do not invent:
- education
- employment
- skills
- projects
- certifications
- contact details

If a field is not present, return an empty string or empty list.

Evaluate the resume for:
1. Candidate information
2. Education
3. Experience
4. Technical skills
5. Soft skills
6. Projects
7. Certifications
8. Resume quality
9. ATS compatibility
10. Missing keywords or sections
11. Skills the candidate should learn or improve

For skill upgrades, recommend skills based on:
- the candidate's existing technical profile
- modern software/technology roles
- skills that would make the resume stronger

Do not claim that a skill is required for a specific job because no job description was provided.

Resume:

{resume_text}
"""
def build_job_match_prompt(resume_text, job_description):
    return f"""
You are an expert recruitment and ATS analyst.

Compare the candidate resume with the provided job description.

Use only factual information available in the resume and job description.

Do not invent:
- skills
- experience
- education
- projects
- certifications
- job requirements

Calculate a match score from 0 to 100 based on how well the candidate's resume matches the job description.

Analyze:

1. Overall job match score
2. Short summary of the match
3. Skills present in both resume and job description
4. Skills required by the job but missing from the resume
5. Job requirements that the candidate appears to satisfy
6. Job requirements that are not satisfied or not demonstrated
7. Practical recommendations for improving the resume for this job
8. Skills the candidate should learn or improve

For skill upgrades:
- Recommend skills relevant to the job description
- Give a reason
- Assign priority as High, Medium, or Low

Do not claim that the candidate has a skill unless it appears in the resume.

RESUME:

{resume_text}

JOB DESCRIPTION:

{job_description}
"""


def generate_with_fallback(contents, response_schema=ResumeAnalysis):
    last_error = None

    for model in [MODEL] + FALLBACK_MODELS:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=response_schema
                    )
                )

                return response

            except Exception as error:
                last_error = error

                error_text = str(error).upper()

                if "503" not in error_text and "429" not in error_text:
                    raise

                if attempt == 0:
                    time.sleep(2)

        continue

    raise last_error


def analyze_resume(file_path, file_type):
    if file_type == "pdf":
        resume_text = extract_pdf_text(file_path)

        if not resume_text.strip():
            uploaded_file = client.files.upload(
                file=file_path
            )

            response = generate_with_fallback(
                [
                    build_prompt(
                        "Analyze the attached resume document."
                    ),
                    uploaded_file
                ]
            )

            return ResumeAnalysis.model_validate_json(
                response.text
            )

    elif file_type == "docx":
        resume_text = extract_docx_text(file_path)

    elif file_type == "txt":
        resume_text = extract_txt_text(file_path)

    elif file_type in ["png", "jpg", "jpeg"]:
        image = Image.open(file_path)

        response = generate_with_fallback(
            [
                build_prompt(
                    "Extract and analyze the resume shown in the attached image."
                ),
                image
            ]
        )

        return ResumeAnalysis.model_validate_json(
            response.text
        )

    else:
        raise ValueError(
            "Unsupported resume format."
        )

    if not resume_text.strip():
        raise ValueError(
            "Could not extract text from the resume."
        )

    response = generate_with_fallback(
        build_prompt(resume_text)
    )

    return ResumeAnalysis.model_validate_json(
        response.text
    )


def save_uploaded_file(uploaded_file):
    suffix = Path(
        uploaded_file.filename
    ).suffix.lower()

    temporary_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    )

    content = uploaded_file.file.read()

    temporary_file.write(content)
    temporary_file.close()

    return temporary_file.name

def analyze_job_match(file_path, file_type, job_description):

    if file_type == "pdf":
        resume_text = extract_pdf_text(file_path)

        if not resume_text.strip():
            uploaded_file = client.files.upload(
                file=file_path
            )

            response = generate_with_fallback(
                [
                    build_job_match_prompt(
                        "Analyze the attached resume document.",
                        job_description
                    ),
                    uploaded_file
                ],
                response_schema=JobMatchAnalysis
            )

            return JobMatchAnalysis.model_validate_json(
                response.text
            )

    elif file_type == "docx":
        resume_text = extract_docx_text(file_path)

    elif file_type == "txt":
        resume_text = extract_txt_text(file_path)

    elif file_type in ["png", "jpg", "jpeg"]:

        image = Image.open(file_path)

        response = generate_with_fallback(
            [
                build_job_match_prompt(
                    "Extract and analyze the resume shown in the attached image.",
                    job_description
                ),
                image
            ],
            response_schema=JobMatchAnalysis
        )

        return JobMatchAnalysis.model_validate_json(
            response.text
        )

    else:
        raise ValueError(
            "Unsupported resume format."
        )

    if not resume_text.strip():
        raise ValueError(
            "Could not extract text from the resume."
        )

    response = generate_with_fallback(
        build_job_match_prompt(
            resume_text,
            job_description
        ),
        response_schema=JobMatchAnalysis
    )

    return JobMatchAnalysis.model_validate_json(
        response.text
    )