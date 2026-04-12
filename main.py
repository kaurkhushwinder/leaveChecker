"""Main FastAPI application for the AI Based Leaf Disease Detection System for Farmers."""

import os
import shutil
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND

from database import Base, SessionLocal, engine
from model_service import predict_disease_from_image
from models import LeafScan, User

app = FastAPI(title="AI Based Leaf Disease Detection System for Farmers")
app.add_middleware(SessionMiddleware, secret_key="leaf-checker-super-secret")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

Base.metadata.create_all(bind=engine)

DiseaseGuidance = dict[str, list[str]]

DISEASE_GUIDANCE: dict[str, DiseaseGuidance] = {
    "Leaf Spot": {
        "symptoms": [
            "Many small, circular, well-defined spots on the leaf surface.",
            "Spots may have dark brown centers and yellow halos.",
            "Lesions are mostly discrete instead of fully merged.",
        ],
        "solutions": [
            "Remove and destroy infected leaves to reduce spread.",
            "Avoid overhead irrigation and keep foliage dry.",
            "Apply a broad-spectrum fungicide as per label instructions.",
        ],
    },
    "Leaf Blight": {
        "symptoms": [
            "Large irregular brown patches spreading across leaf area.",
            "Lesions merge and create large dead sections.",
            "Rapid drying and blighting of affected leaves.",
        ],
        "solutions": [
            "Prune heavily infected leaves and improve field sanitation.",
            "Use copper-based fungicide at recommended intervals.",
            "Improve spacing and airflow to reduce leaf wetness duration.",
        ],
    },
    "Rust": {
        "symptoms": [
            "Raised rust-colored or orange-brown pustules on leaves.",
            "Pustules may rupture and release powdery spores.",
            "Spots can appear in clusters on both leaf surfaces.",
        ],
        "solutions": [
            "Remove infected leaves and control volunteer host plants nearby.",
            "Apply a rust-targeted fungicide early in disease development.",
            "Improve ventilation and avoid long periods of leaf moisture.",
        ],
    },
    "Powdery Mildew": {
        "symptoms": [
            "White to gray powdery growth on leaf surfaces.",
            "Patchy coverage that may expand and merge over time.",
            "Leaf curling or distortion in advanced infection.",
        ],
        "solutions": [
            "Remove infected parts and avoid dense canopy conditions.",
            "Apply sulfur spray or other mildew-specific fungicide.",
            "Water at soil level and avoid wetting foliage late in the day.",
        ],
    },
    "Healthy Leaf": {
        "symptoms": [
            "No clear disease lesions or abnormal fungal growth visible.",
            "Leaf tissue is mostly uniform and green.",
        ],
        "solutions": [
            "No treatment required at this stage.",
            "Continue regular monitoring and preventive crop hygiene.",
        ],
    },
}


def get_db():
    """Provide a database session for each request."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_logged_in_user(request: Request, db: Session) -> User | None:
    """Return the current logged-in user using the session value."""

    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def login_required(request: Request) -> RedirectResponse | None:
    """Redirect to login page if the user is not logged in."""

    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)
    return None


def get_guidance_for_disease(disease_name: str | None) -> DiseaseGuidance:
    """Return symptom and solution guidance for a disease name."""

    if not disease_name:
        return {"symptoms": [], "solutions": []}
    return DISEASE_GUIDANCE.get(disease_name, {"symptoms": [], "solutions": []})


@app.get("/")
def home(request: Request):
    """Send the user to dashboard if logged in, otherwise to login."""

    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


@app.get("/register")
def register_page(request: Request):
    """Show the registration form."""

    return templates.TemplateResponse(
        request,
        "register.html",
        {"message": "", "is_logged_in": False},
    )


@app.post("/register")
def register_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Save a new user to the database."""

    clean_name = name.strip()
    clean_email = email.strip().lower()
    clean_password = password.strip()

    if not clean_name or not clean_email or not clean_password:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "message": "Name, email, and password are required.",
                "is_logged_in": False,
            },
        )

    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "message": "Email already registered. Please use another email.",
                "is_logged_in": False,
            },
        )

    new_user = User(name=clean_name, email=clean_email, password=clean_password)
    db.add(new_user)
    db.commit()

    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


@app.get("/login")
def login_page(request: Request):
    """Show the login form."""

    return templates.TemplateResponse(
        request,
        "login.html",
        {"message": "", "is_logged_in": False},
    )


@app.post("/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Check credentials and store user_id in the session."""

    clean_email = email.strip().lower()
    clean_password = password.strip()
    user = (
        db.query(User)
        .filter(User.email == clean_email, User.password == clean_password)
        .first()
    )

    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "message": "Invalid email or password.",
                "is_logged_in": False,
            },
        )

    request.session["user_id"] = user.id
    return RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Show the dashboard page for logged-in users."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    user = get_logged_in_user(request, db)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "is_logged_in": True},
    )


@app.get("/upload")
def upload_page(request: Request):
    """Show the image upload form."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    return templates.TemplateResponse(
        request,
        "upload.html",
        {"message": "", "is_logged_in": True},
    )


@app.post("/upload")
def upload_leaf(
    request: Request,
    leaf_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Save uploaded image and create a scan record."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    filename = leaf_image.filename or "leaf_image.jpg"
    safe_filename = os.path.basename(filename)
    file_path = UPLOADS_DIR / safe_filename

    if file_path.exists():
        file_stem = file_path.stem
        file_suffix = file_path.suffix
        counter = 1
        while file_path.exists():
            file_path = UPLOADS_DIR / f"{file_stem}_{counter}{file_suffix}"
            counter += 1

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(leaf_image.file, buffer)

    new_scan = LeafScan(
        user_id=request.session["user_id"],
        image_path=f"uploads/{file_path.name}",
    )
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)

    return RedirectResponse(url=f"/predict/{new_scan.id}", status_code=HTTP_302_FOUND)


@app.get("/predict/{scan_id}")
def predict_scan(scan_id: int, request: Request, db: Session = Depends(get_db)):
    """Predict disease from uploaded image and save result."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    scan = (
        db.query(LeafScan)
        .filter(
            LeafScan.id == scan_id,
            LeafScan.user_id == request.session["user_id"],
        )
        .first()
    )

    if not scan:
        return RedirectResponse(url="/history", status_code=HTTP_302_FOUND)

    full_image_path = STATIC_DIR / scan.image_path
    disease, treatment = predict_disease_from_image(full_image_path)
    scan.disease_result = disease
    scan.treatment = treatment
    db.commit()

    return RedirectResponse(url=f"/result/{scan.id}", status_code=HTTP_302_FOUND)


@app.get("/result/{scan_id}")
def result_page(scan_id: int, request: Request, db: Session = Depends(get_db)):
    """Show the image, disease result, treatment, and guidance."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    scan = (
        db.query(LeafScan)
        .filter(
            LeafScan.id == scan_id,
            LeafScan.user_id == request.session["user_id"],
        )
        .first()
    )

    if not scan:
        return RedirectResponse(url="/history", status_code=HTTP_302_FOUND)

    guidance = get_guidance_for_disease(scan.disease_result)
    return templates.TemplateResponse(
        request,
        "result.html",
        {"scan": scan, "guidance": guidance, "is_logged_in": True},
    )


@app.get("/history")
def history_page(request: Request, db: Session = Depends(get_db)):
    """Show all scans of the logged-in user."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    scans = (
        db.query(LeafScan)
        .filter(LeafScan.user_id == request.session["user_id"])
        .order_by(LeafScan.date.desc())
        .all()
    )
    guidance_by_scan_id = {
        scan.id: get_guidance_for_disease(scan.disease_result) for scan in scans
    }

    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "scans": scans,
            "guidance_by_scan_id": guidance_by_scan_id,
            "is_logged_in": True,
        },
    )


@app.get("/tips")
def get_tips(request: Request):
    """Show generic farming tips page."""

    return templates.TemplateResponse(
        request,
        "tips.html",
        {"is_logged_in": "user_id" in request.session},
    )


@app.get("/logout")
def logout(request: Request):
    """Clear session and redirect to login."""

    request.session.clear()
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
