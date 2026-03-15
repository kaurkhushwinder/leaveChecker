# AI Based Leaf Disease Detection System for Farmers

This is a beginner-friendly FastAPI project for detecting leaf disease from uploaded plant images.

Right now, the project does not use a real AI model. It uses `random.choice()` to return a sample disease result. The project is structured so a real AI model can be added later with minimal changes.

## Project Features

- User registration
- User login using `SessionMiddleware`
- Dashboard for logged-in users
- Leaf image upload
- Fake disease prediction using `random.choice()`
- Treatment suggestion based on disease result
- Scan result page
- Scan history page
- Logout
- SQLite database stored locally
- HTML pages rendered using Jinja2 templates

## Technologies Used

- FastAPI
- SQLite
- SQLAlchemy
- Jinja2
- SessionMiddleware
- Pytest

## Project Structure

```text
C:\Users\asus\Desktop\Khushi\Code
│
├── main.py
├── database.py
├── models.py
├── requirements.txt
├── README.md
├── AI_MODEL_INTEGRATION_GUIDE.md
├── leaf_disease_app.db
│
├── templates/
│   ├── base.html
│   ├── register.html
│   ├── login.html
│   ├── dashboard.html
│   ├── upload.html
│   ├── result.html
│   └── history.html
│
├── static/
│   └── uploads/
│
└── tests/
    └── test_app.py
```

## Database Information

This project uses SQLite with this connection string:

```python
sqlite:///./leaf_disease_app.db
```

Database file:

- `leaf_disease_app.db`

Tables:

### Users

- `id`
- `name`
- `email`
- `password`

### LeafScans

- `id`
- `user_id`
- `image_path`
- `disease_result`
- `treatment`
- `date`

The database tables are created automatically using:

```python
Base.metadata.create_all(bind=engine)
```

## Main Routes

- `GET /register`
- `POST /register`
- `GET /login`
- `POST /login`
- `GET /dashboard`
- `GET /upload`
- `POST /upload`
- `GET /predict/{scan_id}`
- `GET /result/{scan_id}`
- `GET /history`
- `GET /logout`

## How the Project Works

### Registration

The user opens `/register`, fills in name, email, and password, and the data is saved in the SQLite database.

### Login

The user opens `/login`, enters email and password, and if the credentials match, the app stores:

```python
request.session["user_id"]
```

### Dashboard

After login, the user can:

- upload a leaf image
- view scan history
- logout

### Upload and Prediction

1. User uploads an image
2. Image is saved in `static/uploads/`
3. A `LeafScan` record is created
4. The app redirects to `/predict/{scan_id}`
5. The app generates a fake prediction using `random.choice()`
6. Disease and treatment are saved to the database
7. The user is redirected to the result page

### History

The user can view all previous scan results from `/history`.

## Disease Output Used in This Project

Possible disease results:

- `Leaf Blight`
- `Powdery Mildew`
- `Healthy Leaf`

Treatment mapping:

- `Leaf Blight` -> `Use copper-based fungicide.`
- `Powdery Mildew` -> `Apply sulfur spray.`
- `Healthy Leaf` -> `No treatment required.`

## Installation

From the project root, run:

```bash
pip install -r requirements.txt
```

If you are using the local virtual environment:

```bash
venv\Scripts\activate
pip install -r requirements.txt
```

## How to Run the Project

From the project root, run:

```bash
python main.py
```

If you are using the local virtual environment:

```bash
venv\Scripts\activate
python main.py
```

The application will start at:

- `http://127.0.0.1:8000`

Useful URLs:

- `http://127.0.0.1:8000/register`
- `http://127.0.0.1:8000/login`
- `http://127.0.0.1:8000/dashboard`

## How to Run Tests

The project includes route-level tests in:

- `tests/test_app.py`

Run tests with:

```bash
venv\Scripts\python.exe -m pytest tests -q
```

Or:

```bash
python -m pytest tests -q
```

## Current Authentication Method

This project uses:

```python
from starlette.middleware.sessions import SessionMiddleware
```

And:

```python
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")
```

This project does not use:

- JWT
- MySQL
- PostgreSQL

## Future AI Model Integration

This project is prepared for future AI integration.

Right now, fake prediction is handled by:

```python
def predict_disease():
```

Later, this can be replaced by a real model prediction function such as:

```python
def predict_disease_from_model(image_path: str) -> tuple[str, str]:
```

Recommended future input:

- saved image path

Recommended future output:

```python
("Leaf Blight", "Use copper-based fungicide.")
```

For full future integration details, read:

- [`AI_MODEL_INTEGRATION_GUIDE.md`](C:\Users\asus\Desktop\Khushi\Code\AI_MODEL_INTEGRATION_GUIDE.md)

## Important Notes

- This version is made simple for beginners
- Passwords are compared as plain text for learning purposes
- A real AI model is not yet connected
- Uploaded files are stored in `static/uploads/`
- Database is stored locally in the project folder

## Requirements

The `requirements.txt` file includes:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `jinja2`
- `python-multipart`
- `itsdangerous`
- `pytest`
- `httpx`

## Submission Summary

This project is ready to:

- run locally
- store users and scan history in SQLite
- render HTML templates
- upload images
- generate beginner-friendly sample results
- be extended later with a real AI model
