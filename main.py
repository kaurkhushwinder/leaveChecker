import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
import json
from pathlib import Path
import shutil

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.status import HTTP_302_FOUND

from database import Base, SessionLocal, engine
from models import LeafScan, User

app = FastAPI()

# Session Secret Key - Isko secure rakhein
app.add_middleware(SessionMiddleware, secret_key="leaf-checker-super-secret")

# Paths setup
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Database Tables Create karein
Base.metadata.create_all(bind=engine)

# --- AI MODEL LOADING ---
with open("classes.json") as f:
    classes = json.load(f)

# Architecture (Matching your .pth file)
model = nn.Sequential(
    nn.Conv2d(3, 32, 3), nn.ReLU(), nn.MaxPool2d(2),
    nn.Conv2d(32, 64, 3), nn.ReLU(), nn.MaxPool2d(2),
    nn.Flatten(),
    nn.Linear(64*30*30, 128), nn.ReLU(),
    nn.Linear(128, len(classes))
)
model.load_state_dict(torch.load("leaf_model.pth", map_location=torch.device('cpu')))
model.eval()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- ROUTES ---

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "is_logged_in": "user_id" in request.session
    })

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_user(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    db.add(User(name=name, email=email, password=password))
    db.commit()
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.password == password).first()
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "message": "Invalid Login Credentials"})
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    return RedirectResponse(url="/dashboard", status_code=HTTP_302_FOUND)

@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    if "user_id" not in request.session: 
        return RedirectResponse(url="/login")
    user = db.query(User).filter(User.id == request.session["user_id"]).first()
    return templates.TemplateResponse("index.html", { # Dashboard features are in index.html as per your design
        "request": request, 
        "user_name": user.name, 
        "is_logged_in": True
    })

@app.get("/upload")
def upload_page(request: Request):
    if "user_id" not in request.session: 
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("upload.html", {"request": request, "is_logged_in": True})

@app.post("/upload")
async def upload_leaf(request: Request, leaf_image: UploadFile = File(...), db: Session = Depends(get_db)):
    if "user_id" not in request.session:
        return RedirectResponse(url="/login")
        
    user_id = request.session.get("user_id")
    new_scan = LeafScan(user_id=user_id, image_path="pending")
    db.add(new_scan)
    db.commit()
    db.refresh(new_scan)

    filename = f"scan_{new_scan.id}_{leaf_image.filename}"
    save_path = UPLOADS_DIR / filename
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(leaf_image.file, buffer)

    new_scan.image_path = f"uploads/{filename}"
    db.commit()
    return RedirectResponse(url=f"/predict/{new_scan.id}", status_code=HTTP_302_FOUND)

@app.get("/predict/{scan_id}")
def predict_scan(scan_id: int, request: Request, db: Session = Depends(get_db)):
    scan = db.query(LeafScan).filter(LeafScan.id == scan_id).first()
    if not scan:
        return RedirectResponse(url="/")

    img = Image.open(STATIC_DIR / scan.image_path).convert("RGB")
    transform = transforms.Compose([transforms.Resize((128,128)), transforms.ToTensor()])
    img_tensor = transform(img).unsqueeze(0)
    
    with torch.no_grad():
        output = model(img_tensor)
        prob = torch.nn.functional.softmax(output, dim=1)
        conf, pred = torch.max(prob, 1)
        confidence = round(conf.item() * 100, 2)
    
    scan.disease_result = classes[pred.item()]
    
    # Treatment Logic
    if "Healthy" in scan.disease_result:
        scan.treatment = "Your plant is healthy! Continue regular maintenance."
    else:
        scan.treatment = "Organic: Spray Neem Oil mixture. Chemical: Copper-based fungicide. Prevention: Improve air circulation."
    
    db.commit()
    return RedirectResponse(url=f"/result/{scan.id}?conf={confidence}", status_code=HTTP_302_FOUND)

@app.get("/result/{scan_id}")
def result_page(scan_id: int, request: Request, conf: float = 0, db: Session = Depends(get_db)):
    scan = db.query(LeafScan).filter(LeafScan.id == scan_id).first()
    if not scan:
        return RedirectResponse(url="/")
        
    clean_name = scan.disease_result.replace('___', ' | ').replace('_', ' ').title()
    return templates.TemplateResponse("result.html", {
        "request": request, 
        "scan": scan, 
        "clean_disease": clean_name, 
        "confidence": conf,
        "is_logged_in": True
    })

@app.get("/history")
def history_page(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id: 
        return RedirectResponse(url="/login")
    scans = db.query(LeafScan).filter(LeafScan.user_id == user_id).order_by(LeafScan.id.desc()).all()
    return templates.TemplateResponse("history.html", {
        "request": request, 
        "scans": scans, 
        "is_logged_in": True
    })

# --- NEW TIPS ROUTE ---
@app.get("/tips")
def get_tips(request: Request):
    return templates.TemplateResponse("tips.html", {
        "request": request,
        "is_logged_in": "user_id" in request.session
    })

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)