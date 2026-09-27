import math
import os
from pathlib import Path

from app.embeddings import generate_query_embedding
from app.ingestion import prepare_image_item


IMAGES = [
    Path("test_images/hair_oil.png"),
    Path("test_images/freefit_booking.png"),
]


def cosine_similarity(a, b):
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    return dot_product / (magnitude_a * magnitude_b)


items = []

for image_path in IMAGES:
    print(f"Processing: {image_path}")

    item = prepare_image_item(
        image_bytes=image_path.read_bytes(),
        mime_type="image/png",
    )

    item["path"] = image_path
    items.append(item)


query = "תראה לי את השמפו ששמרתי"

print(f"\nQuery: {query}")

query_embedding = generate_query_embedding(query)

best_item = max(
    items,
    key=lambda item: cosine_similarity(
        query_embedding,
        item["embedding"],
    ),
)

score = cosine_similarity(
    query_embedding,
    best_item["embedding"],
)

print("Matched:", best_item["title"])
print("File:", best_item["path"])
print("Similarity:", round(score, 4))

os.startfile(best_item["path"])