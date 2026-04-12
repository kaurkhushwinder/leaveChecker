"""Image-based disease prediction helpers."""

from pathlib import Path

from PIL import Image, UnidentifiedImageError

TREATMENT_BY_DISEASE = {
    "Leaf Spot": "Use a broad-spectrum fungicide and remove infected leaves.",
    "Leaf Blight": "Use copper-based fungicide.",
    "Rust": "Apply a rust-specific fungicide and improve airflow around plants.",
    "Powdery Mildew": "Apply sulfur spray.",
    "Healthy Leaf": "No treatment required.",
}


def _connected_component_areas(mask: list[bool], width: int, height: int) -> list[int]:
    """Return areas for all connected components in a boolean mask."""

    def index(x: int, y: int) -> int:
        return y * width + x

    visited = [False] * (width * height)
    areas: list[int] = []

    for y in range(height):
        for x in range(width):
            start = index(x, y)
            if visited[start] or not mask[start]:
                continue

            stack = [start]
            visited[start] = True
            area = 0

            while stack:
                current = stack.pop()
                area += 1
                cx = current % width
                cy = current // width

                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        nxt = index(nx, ny)
                        if not visited[nxt] and mask[nxt]:
                            visited[nxt] = True
                            stack.append(nxt)

            areas.append(area)

    return areas


def _classify_leaf_image(image_path: Path) -> str:
    """Classify a leaf image using lesion-size and color heuristics."""

    width, height = 256, 256
    with Image.open(image_path) as image:
        rgb = image.convert("RGB").resize((width, height))

    total_relevant = 0
    rust_color = 0
    lesion_pixels = 0
    white_powder = 0
    yellow_halo = 0
    lesion_mask = [False] * (width * height)

    for i, (r, g, b) in enumerate(rgb.getdata()):
        max_channel = max(r, g, b)
        min_channel = min(r, g, b)

        if max_channel < 25:
            continue

        saturation = 0.0 if max_channel == 0 else (max_channel - min_channel) / max_channel

        # Skip very bright and low-saturation background pixels.
        if max_channel > 225 and saturation < 0.1:
            continue

        total_relevant += 1

        is_rust = r > 135 and g > 60 and g < 180 and b < 120 and (r - g) >= 20 and g >= b
        if is_rust:
            rust_color += 1

        is_yellow_halo = r > 135 and g > 120 and b < 125 and (r - b) > 25
        if is_yellow_halo:
            yellow_halo += 1

        if r > 165 and g > 165 and b > 165 and saturation < 0.2:
            white_powder += 1

        is_lesion = (
            (r >= g and r > 80 and b < 130 and (r - b) > 20)
            or (r < 95 and g < 95 and b < 95)
        )
        if is_lesion:
            lesion_pixels += 1
            lesion_mask[i] = True

    if total_relevant < 500:
        return "Healthy Leaf"

    lesion_ratio = lesion_pixels / total_relevant
    rust_ratio = rust_color / total_relevant
    white_ratio = white_powder / total_relevant
    yellow_ratio = yellow_halo / total_relevant

    lesion_areas = _connected_component_areas(lesion_mask, width, height)
    small_spots = sum(1 for area in lesion_areas if 4 <= area <= 90)
    large_areas = [area for area in lesion_areas if area >= 260]
    largest_area = max(lesion_areas) if lesion_areas else 0
    total_large_area = sum(large_areas)

    # Powdery mildew appears as broad pale/whitish powder patches.
    if white_ratio >= 0.13:
        return "Powdery Mildew"

    # Rust appears with orange/rust colored pustules.
    if rust_ratio >= 0.11 and small_spots >= 10:
        return "Rust"

    # Blight is characterized by larger merged dead tissue patches.
    if (
        lesion_ratio >= 0.18
        and (
            largest_area >= 1200
            or total_large_area >= 1800
            or (large_areas and small_spots < 18)
        )
    ):
        return "Leaf Blight"

    # Leaf spot has many small, discrete lesions (often with yellow halo).
    if small_spots >= 18 and lesion_ratio >= 0.05 and (yellow_ratio >= 0.03 or rust_ratio >= 0.04):
        return "Leaf Spot"

    return "Healthy Leaf"


def predict_disease_from_image(image_path: str | Path) -> tuple[str, str]:
    """Predict disease label and return the mapped treatment text."""

    image_path = Path(image_path)
    try:
        disease = _classify_leaf_image(image_path)
    except (FileNotFoundError, UnidentifiedImageError, OSError):
        # Keep the app flow stable even if the uploaded file cannot be decoded.
        disease = "Healthy Leaf"

    return disease, TREATMENT_BY_DISEASE[disease]
