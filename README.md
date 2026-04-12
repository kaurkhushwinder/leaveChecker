# AI-Based Leaf Disease Detection (FastAPI)

A web application for farmers to upload leaf images, detect likely disease class, and view treatment suggestions.

This project uses a deterministic image-analysis model (color-ratio heuristics), not a random output. It currently predicts one of:
- `Leaf Blight`
- `Powdery Mildew`
- `Healthy Leaf`

## What This Project Does

- User registration and login (session-based auth)
- Protected dashboard for logged-in users
- Leaf image upload and storage in `static/uploads/`
- Disease prediction from uploaded image
- Treatment suggestion based on predicted disease
- Result page and scan history page
- Logout
- SQLite database persistence

## Tech Stack

- FastAPI
- SQLAlchemy
- SQLite
- Jinja2 templates
- Starlette `SessionMiddleware`
- Pillow (image loading and pixel analysis)
- Pytest + FastAPI TestClient

## Prediction Logic (Current)

Prediction is done in [`model_service.py`](model_service.py).

The model reads the uploaded image and classifies using pixel-color signals:
- high white/low-saturation regions -> `Powdery Mildew`
- high yellow-brown region ratio -> `Leaf Blight`
- otherwise -> `Healthy Leaf`

If an uploaded file cannot be decoded as an image, the app falls back to `Healthy Leaf` to keep app flow stable.

## Project Structure

```text
leaveChecker/
|-- main.py
|-- model_service.py
|-- database.py
|-- models.py
|-- requirements.txt
|-- README.md
|-- AI_MODEL_INTEGRATION_GUIDE.md
|-- leaf_disease_app.db
|-- templates/
|   |-- base.html
|   |-- register.html
|   |-- login.html
|   |-- dashboard.html
|   |-- upload.html
|   |-- result.html
|   |-- history.html
|-- static/
|   |-- uploads/
|-- tests/
|   |-- test_app.py
```

## Database Schema

### `users`
- `id`
- `name`
- `email` (unique)
- `password`

### `leaf_scans`
- `id`
- `user_id` (FK -> users.id)
- `image_path`
- `disease_result`
- `treatment`
- `date`

Tables are created automatically on app startup:

```python
Base.metadata.create_all(bind=engine)
```

## Main Routes

- `GET /` -> redirect to login/dashboard
- `GET /register`, `POST /register`
- `GET /login`, `POST /login`
- `GET /dashboard`
- `GET /upload`, `POST /upload`
- `GET /predict/{scan_id}`
- `GET /result/{scan_id}`
- `GET /history`
- `GET /logout`

## Setup

From project root:

```bash
pip install -r requirements.txt
```

## Run

Use either:

```bash
python main.py
```

or:

```bash
uvicorn main:app --reload
```

App URL:
- `http://127.0.0.1:8000`

## Test

```bash
python -m pytest tests -q
```

## Important Notes

- Authentication is session-based and passwords are stored as plain text (for learning/demo only).
- This is not a medical/agronomy-grade diagnosis system.
- For production use, replace heuristic prediction with a trained ML model and add proper password hashing.

## Future Improvement

Use the existing prediction hook in `model_service.py` to switch from heuristics to a trained TensorFlow/PyTorch model while keeping routes and database flow unchanged.
