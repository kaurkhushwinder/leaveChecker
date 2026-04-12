import json

import torch
import torchvision
from torch import nn, optim
from torchvision import datasets, transforms

# -----------------------------
# 1) Image preprocessing pipeline
# -----------------------------
# Every image is resized to the same shape so batches can be stacked into one tensor.
# `ToTensor()` converts a PIL image in [0, 255] to float tensor in [0.0, 1.0].
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),
])

# -----------------------------
# 2) Dataset + mini-batch loader
# -----------------------------
# ImageFolder expects this directory layout:
# dataset/
#   class_a/
#   class_b/
#   ...
# Folder names are treated as class labels automatically.
dataset = datasets.ImageFolder("dataset", transform=transform)

# DataLoader returns shuffled mini-batches for stochastic gradient descent.
# batch_size=32 means one optimizer update happens after every 32 images.
loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)

# Save class names so inference can map output index -> readable class label.
with open("classes.json", "w") as f:
    json.dump(dataset.classes, f)

print("Classes:", dataset.classes)

# -----------------------------
# 3) CNN model definition
# -----------------------------
# Input shape:  [B, 3, 128, 128]
# After Conv(3x3, no padding): [B, 32, 126, 126]
# After MaxPool(2):            [B, 32, 63, 63]
# After Conv(3x3, no padding): [B, 64, 61, 61]
# After MaxPool(2):            [B, 64, 30, 30]
# Flatten size therefore is 64 * 30 * 30.
model = nn.Sequential(
    # Learn low-level textures/edges from RGB input.
    nn.Conv2d(3, 32, 3),
    nn.ReLU(),
    nn.MaxPool2d(2),

    # Learn richer patterns from the first feature maps.
    nn.Conv2d(32, 64, 3),
    nn.ReLU(),
    nn.MaxPool2d(2),

    # Convert feature maps into one vector per image.
    nn.Flatten(),

    # Hidden dense layer for non-linear class separation.
    nn.Linear(64 * 30 * 30, 128),
    nn.ReLU(),

    # Final layer outputs raw class scores (logits).
    nn.Linear(128, len(dataset.classes)),
)

# -----------------------------
# 4) Loss function + optimizer
# -----------------------------
# CrossEntropyLoss expects raw logits + integer class IDs.
# Adam uses adaptive learning rates for each parameter.
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# -----------------------------
# 5) Training loop
# -----------------------------
# One epoch = one complete pass over the dataset.
for epoch in range(10):
    for images, labels in loader:
        # Forward pass: compute predictions from current weights.
        outputs = model(images)

        # Measure prediction error against ground-truth labels.
        loss = criterion(outputs, labels)

        # Clear old gradients so they do not accumulate across batches.
        optimizer.zero_grad()

        # Backward pass: compute gradients via backpropagation.
        loss.backward()

        # Update weights using computed gradients.
        optimizer.step()

    # Logs loss from the final batch of the epoch.
    # If needed, you can average all batch losses for a smoother metric.
    print(f"Epoch {epoch + 1}, Loss: {loss.item()}")

# -----------------------------
# 6) Save trained model weights
# -----------------------------
# Save only the state_dict (recommended PyTorch practice).
torch.save(model.state_dict(), "leaf_model.pth")

print("Model trained successfully!")
