"""
Create a 文生图→视频 工作流测试脚本 (通过 Django shell)
"""
import os
import sys
import django

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from workflows.models import Workflow, Node, Edge

User = get_user_model()

user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()
if not user:
    print("No user found. Please create a user first.")
    exit(1)
print(f"Using owner: {user.username} (id={user.id})")

wf = Workflow.objects.create(
    name="文生图 → 视频生成测试",
    description="测试图像生成节点到视频生成节点的串联执行",
    status="draft",
    owner=user,
)

start_node = Node.objects.create(
    workflow=wf, node_type="start", name="开始",
    position_x=0, position_y=200, config={}
)
img_node = Node.objects.create(
    workflow=wf, node_type="image_generation", name="生成图片",
    position_x=300, position_y=200,
    config={
        "model": "dall-e-3", "provider": "openai",
        "prompt": "A beautiful sunset over a mountain lake, cinematic photography, 8K resolution",
        "size": "1024x1024", "quality": "hd", "style": "vivid"
    }
)
vid_node = Node.objects.create(
    workflow=wf, node_type="video_generation", name="生成视频",
    position_x=600, position_y=200,
    config={
        "model": "kling", "provider": "kling",
        "prompt": "Animate this scene with gentle water ripples and moving clouds",
        "duration": 5, "resolution": "1080p", "fps": "30"
    }
)
end_node = Node.objects.create(
    workflow=wf, node_type="end", name="结束",
    position_x=900, position_y=200, config={}
)

Edge.objects.create(workflow=wf, source_node=start_node, target_node=img_node)
Edge.objects.create(workflow=wf, source_node=img_node, target_node=vid_node)
Edge.objects.create(workflow=wf, source_node=vid_node, target_node=end_node)

print(f"\nWorkflow created!")
print(f"  Name: {wf.name}")
print(f"  ID: {wf.id}")
print(f"  Nodes: {wf.nodes.count()}")
print(f"  Edges: {wf.edges.count()}")
print(f"  Open: http://localhost:5200/workflows/{wf.id}/edit")
