# AI Model Integration Guide

This document explains how to integrate a real AI model into the current FastAPI project in the future.

Right now, the project uses `random.choice()` to return a fake prediction. Later, this can be replaced with a real machine learning or deep learning model without changing the full project structure.

## 1. Current Project Flow

At the moment, the prediction flow works like this:

1. User uploads a leaf image from `/upload`
2. The image is saved inside `static/uploads/`
3. A `LeafScan` record is created in the database
4. The route `/predict/{scan_id}` is called
5. The function `predict_disease()` returns a random disease and treatment
6. The result is saved in the database
7. The user is redirected to `/result/{scan_id}`

## 2. Which File Should Contain the AI Model Integration?

The best place to integrate the real AI model is:

- `main.py`

More specifically:

- Replace or upgrade the `predict_disease()` function
- Update the `/predict/{scan_id}` route if needed

This is the simplest option for beginners.

If the project grows later, a cleaner structure would be:

- `main.py` for routes
- `model_service.py` for AI model loading and prediction logic

For now, keeping it simple inside `main.py` is enough.

## 3. Current Fake Prediction Function

Right now, `main.py` has this function:

```python
def predict_disease() -> tuple[str, str]:
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
```

This function should later be replaced by a real model-based prediction function.

## 4. Future AI Integration Goal

When a real AI model is added, the system should:

1. Read the uploaded image from disk
2. Preprocess the image into the format required by the model
3. Send the image to the model
4. Get the predicted disease label
5. Map that disease label to a treatment
6. Save the disease and treatment into the database

## 5. Recommended Future Function

Later, the fake function should be replaced with something like this:

```python
def predict_disease_from_model(image_path: str) -> tuple[str, str]:
    # 1. Load the saved image from image_path
    # 2. Preprocess image for the model
    # 3. Run model prediction
    # 4. Convert model output into disease name
    # 5. Return disease name and treatment
    pass
```

This function should accept:

- `image_path: str`

And return:

- `tuple[str, str]`

Meaning:

- First value: predicted disease name
- Second value: treatment text

Example:

```python
("Leaf Blight", "Use copper-based fungicide.")
```

## 6. Expected Model Input

The model will usually need:

- Image file path, or
- Image array/tensor after preprocessing

In this project, the easiest approach is:

- Save image first
- Pass the saved image path to the prediction function

Example:

```python
image_path = "static/uploads/leaf1.jpg"
```

Then the function can load the image from disk.

## 7. Expected Model Output

The AI model should finally provide one disease label such as:

- `"Leaf Blight"`
- `"Powdery Mildew"`
- `"Healthy Leaf"`

The project should convert the model output into a response format the app can use directly.

Recommended app-level output:

```python
{
    "disease": "Leaf Blight",
    "treatment": "Use copper-based fungicide."
}
```

Or as a tuple:

```python
("Leaf Blight", "Use copper-based fungicide.")
```

For this project, the tuple is easier because the current database save logic already expects two separate values.

## 8. Recommended Treatment Mapping

Even if the AI model predicts only the disease name, the treatment should still be mapped inside the app.

Example:

```python
treatments = {
    "Leaf Blight": "Use copper-based fungicide.",
    "Powdery Mildew": "Apply sulfur spray.",
    "Healthy Leaf": "No treatment required.",
}
```

This is useful because:

- The model only focuses on disease prediction
- The app handles farmer-friendly treatment text
- Treatment text can be updated without retraining the model

## 9. Where to Update the Code

The main changes will be in `main.py`.

### Part A: Replace prediction function

Current:

```python
def predict_disease() -> tuple[str, str]:
```

Future:

```python
def predict_disease_from_model(image_path: str) -> tuple[str, str]:
```

### Part B: Update `/predict/{scan_id}` route

Current code:

```python
disease, treatment = predict_disease()
```

Future code:

```python
full_image_path = str(STATIC_DIR / scan.image_path)
disease, treatment = predict_disease_from_model(full_image_path)
```

This means the route will send the actual saved image file to the AI function.

## 10. Example Future Version of the Route

Below is an example of how the route may look later:

```python
@app.get("/predict/{scan_id}")
def predict_scan(scan_id: int, request: Request, db: Session = Depends(get_db)):
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

    full_image_path = str(STATIC_DIR / scan.image_path)
    disease, treatment = predict_disease_from_model(full_image_path)

    scan.disease_result = disease
    scan.treatment = treatment
    db.commit()

    return RedirectResponse(url=f"/result/{scan.id}", status_code=HTTP_302_FOUND)
```

## 11. If You Use a Deep Learning Model

If the future model is built using TensorFlow or PyTorch, the prediction function may look like this:

```python
def predict_disease_from_model(image_path: str) -> tuple[str, str]:
    # Load image
    # Resize image
    # Normalize pixel values
    # Convert image to tensor
    # Run model prediction
    # Get class label
    # Map label to treatment
    return disease, treatment
```

Possible future libraries:

- `tensorflow`
- `torch`
- `torchvision`
- `Pillow`
- `opencv-python`
- `numpy`

These should only be added when the real model is introduced.

## 12. If You Use an External AI API

If the future model is not stored locally and instead runs on another server or cloud API, then:

1. Upload image
2. Read image bytes
3. Send image to external model API
4. Receive JSON response
5. Extract disease and treatment
6. Save values in the database

Example expected API response:

```json
{
  "disease": "Powdery Mildew",
  "confidence": 0.94
}
```

Then inside the app:

```python
treatments = {
    "Leaf Blight": "Use copper-based fungicide.",
    "Powdery Mildew": "Apply sulfur spray.",
    "Healthy Leaf": "No treatment required."
}
```

And finally:

```python
disease = api_response["disease"]
treatment = treatments.get(disease, "Consult an agricultural expert.")
```

## 13. Recommended Standard Response for the App

Whether the model is local or external, the application should standardize the final result to this format:

```python
{
    "disease": "Leaf Blight",
    "treatment": "Use copper-based fungicide.",
    "confidence": 0.95
}
```

Notes:

- `disease` is required
- `treatment` is required
- `confidence` is optional

Right now, the database only stores:

- `disease_result`
- `treatment`

If confidence is needed later, you can add a new column in `models.py`, for example:

```python
confidence = Column(String, nullable=True)
```

Or better:

```python
from sqlalchemy import Float

confidence = Column(Float, nullable=True)
```

## 14. Recommended Future Folder Structure

When AI integration becomes bigger, the project can be improved like this:

```text
project_root/
│
├── main.py
├── database.py
├── models.py
├── model_service.py
├── requirements.txt
├── leaf_disease_app.db
│
├── templates/
├── static/
└── tests/
```

Purpose of `model_service.py`:

- Load the AI model once
- Preprocess images
- Run prediction
- Return disease name and treatment

This keeps `main.py` cleaner.

## 15. Beginner-Friendly Upgrade Path

When you are ready to add the model, follow this order:

1. Keep the upload process the same
2. Keep the database the same
3. Replace `predict_disease()` with a real prediction function
4. Pass the image path into that function
5. Return disease and treatment
6. Save the result exactly as the project already does

This approach is safe because it changes only the prediction logic, not the full app.

## 16. Final Recommendation

For this project, the best future plan is:

- Keep routes in `main.py`
- Replace the fake prediction function first
- Later move prediction logic into `model_service.py`
- Make the model return a disease label
- Let the app map that label to treatment text
- Save final values in the database

## 17. Short Summary

When a real AI model is introduced:

- Integrate it in `main.py` first
- Best function to replace: `predict_disease()`
- Best future function signature:

```python
def predict_disease_from_model(image_path: str) -> tuple[str, str]:
```

- Input:
  - saved image path

- Output:
  - disease name
  - treatment text

- Main route to update:
  - `/predict/{scan_id}`

This means the current project is already ready for future AI integration with only small code changes.
