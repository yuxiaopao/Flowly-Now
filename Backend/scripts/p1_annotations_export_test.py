#!/usr/bin/env python
"""P1: annotation export image_text_pairs smoke."""
import json
import os
import sys
import uuid

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from datasets.models import Dataset
from annotations.models import AnnotationProject, AnnotationItem
from annotations.utils import export_image_text_pairs

User = get_user_model()
user = User.objects.first()
if not user:
    print("SKIP: no user")
    sys.exit(0)

ds = Dataset.objects.create(
    name=f"p1_pairs_{uuid.uuid4().hex[:6]}",
    source="upload",
    file_path="/tmp",
    format="image_text_pairs",
    created_by=user,
)
proj = AnnotationProject.objects.create(
    name="p1 export test",
    dataset=ds,
    annotation_type="classification",
    labels=["cat"],
    created_by=user,
)
AnnotationItem.objects.create(
    project=proj,
    data_id="1",
    data_content={"image": "images/a.jpg", "text": "一只猫"},
    label="cat",
    status="annotated",
)
result = export_image_text_pairs(proj)
assert result.get("success"), result
lines = result["content"].strip().split("\n")
row = json.loads(lines[0])
assert row["image"] == "images/a.jpg"
assert "猫" in row["text"]
print("OK export_image_text_pairs", result["pair_count"])
proj.delete()
ds.delete()
