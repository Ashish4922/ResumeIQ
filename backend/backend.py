from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import os
from backend.gemini_service import (
    save_uploaded_file,
    analyze_resume,
    analyze_job_match
)

from backend.database import (
    init_database,
    create_user,
    get_user_by_email,
    get_user_by_id,
    consume_analysis
)
from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token
)

app = FastAPI(
    title="ResumeIQ API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

security = HTTPBearer()

init_database()

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")

    user = get_user_by_id(
        int(user_id)
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user

@app.get("/")
def root():
    return {
        "message": "ResumeIQ backend is running"
    }

@app.post("/register")
def register(data: RegisterRequest):

    existing_user = get_user_by_email(
        data.email
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 6 characters"
        )

    hashed_password = hash_password(
        data.password
    )

    user_id = create_user(
        data.name,
        data.email,
        hashed_password
    )

    token = create_access_token(
        user_id
    )

    return {
        "message": "Registration successful",
        "token": token,
        "user": {
            "id": user_id,
            "name": data.name,
            "email": data.email
        }
    }

@app.post("/login")
def login(data: LoginRequest):

    user = get_user_by_email(
        data.email
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        data.password,
        user["password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(
        user["id"]
    )

    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    }

@app.get("/me")
def me(
    user = Depends(get_current_user)
):

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "free_credits": user["free_credits"],
        "paid_balance": user["paid_balance"],
        "total_analyses": user["total_analyses"]
    }

@app.get("/credits")
def credits(
    user = Depends(get_current_user)
):

    return {
        "free_credits": user["free_credits"],
        "paid_balance": user["paid_balance"],
        "price_per_analysis": 10,
        "total_analyses": user["total_analyses"]
    }

@app.post("/consume-analysis")
def consume(
    user = Depends(get_current_user)
):

    result = consume_analysis(
        user["id"]
    )

    if not result["allowed"]:
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Free credits exhausted",
                "price": 10,
                "reason": "Payment required"
            }
        )
    

    return result
@app.post("/analyze-resume")
def analyze_resume_endpoint(
    file: UploadFile = File(...),
    user = Depends(get_current_user)
):
    allowed_extensions = {
        ".pdf",
        ".docx",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg"
    }

    filename = file.filename or ""

    extension = filename.lower().split(".")[-1]

    if f".{extension}" not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported resume format."
        )

    temporary_file = None

    try:
        temporary_file = save_uploaded_file(file)

        result = analyze_resume(
            temporary_file,
            extension
        )

        credit_result = consume_analysis(
            user["id"]
        )

        if not credit_result["allowed"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Free credits exhausted",
                    "price": 10,
                    "reason": "Payment required"
                }
            )

        return {
            "message": "Resume analyzed successfully",
            "credit": credit_result,
            "analysis": result.model_dump()
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        if temporary_file:
            try:
                os.remove(temporary_file)
            except Exception:
                pass

@app.post("/analyze-job")
def analyze_job_endpoint(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    user = Depends(get_current_user)
):

    allowed_extensions = {
        ".pdf",
        ".docx",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg"
    }

    filename = file.filename or ""

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported resume format."
        )

    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    temporary_file = None

    try:

        temporary_file = save_uploaded_file(
            file
        )

        result = analyze_job_match(
            temporary_file,
            extension.replace(".", ""),
            job_description
        )

        credit_result = consume_analysis(
            user["id"]
        )

        if not credit_result["allowed"]:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Free credits exhausted",
                    "price": 10,
                    "reason": "Payment required"
                }
            )

        return {
            "message": "Job analyzed successfully",
            "credit": credit_result,
            "analysis": result.model_dump()
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:

        if temporary_file:

            try:
                os.remove(temporary_file)

            except Exception:
                pass