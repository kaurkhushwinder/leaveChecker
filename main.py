"""Main FastAPI application for the AI Based Leaf Disease Detection System for Farmers."""

import os
import random
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
from models import LeafScan, User

app = FastAPI(title="AI Based Leaf Disease Detection System for Farmers")
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"

# Create the upload folder automatically if it does not exist.
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Automatically create database tables when the app starts.
Base.metadata.create_all(bind=engine)


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


def predict_disease() -> tuple[str, str]:
    """Return a random disease result and its treatment."""

    diseases = [
        "Leaf Blight",
        "Powdery Mildew",
        "Healthy Leaf",
    ]

    treatments = {
        "Leaf Blight": "Use copper-based fungicide.",
        "Powdery Mildew": "Apply sulfur spray.",
        "Healthy Leaf": "No treatment required.",
    }

    disease = random.choice(diseases)
    return disease, treatments[disease]


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

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "message": "Email already registered. Please use another email.",
                "is_logged_in": False,
            },
        )

    new_user = User(name=name, email=email, password=password)
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
    """Check the email and password and store user_id in the session."""

    user = db.query(User).filter(User.email == email, User.password == password).first()

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
    """Save the uploaded image and create a scan record."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    filename = leaf_image.filename or "leaf_image.jpg"
    safe_filename = os.path.basename(filename)
    file_path = UPLOADS_DIR / safe_filename

    # Add a number to the filename if the same name already exists.
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
    """Generate a random disease result and save it for the scan."""

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

    disease, treatment = predict_disease()
    scan.disease_result = disease
    scan.treatment = treatment
    db.commit()

    return RedirectResponse(url=f"/result/{scan.id}", status_code=HTTP_302_FOUND)


@app.get("/result/{scan_id}")
def result_page(scan_id: int, request: Request, db: Session = Depends(get_db)):
    """Show the image, disease result, and treatment."""

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

    return templates.TemplateResponse(
        request,
        "result.html",
        {"scan": scan, "is_logged_in": True},
    )


@app.get("/history")
def history_page(request: Request, db: Session = Depends(get_db)):
    """Show all previous scans of the logged-in user."""

    redirect_response = login_required(request)
    if redirect_response:
        return redirect_response

    scans = (
        db.query(LeafScan)
        .filter(LeafScan.user_id == request.session["user_id"])
        .order_by(LeafScan.date.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "history.html",
        {"scans": scans, "is_logged_in": True},
    )


@app.get("/logout")
def logout(request: Request):
    """Clear session data and send the user to the login page."""

    request.session.clear()
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", reload=True)
