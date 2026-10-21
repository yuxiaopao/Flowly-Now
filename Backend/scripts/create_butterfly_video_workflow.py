"""Create and verify the native 15-second butterfly/feather video workflow.

The provider credential is read from the encrypted credential centre; this
script, the exported graph and its reports contain no API keys.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import uuid

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from workflows.models import APICredential, Edge, Node, Workflow
from workflows.services.langchain_service import LangChainService
from workflows.services.media_service import build_public_media_url
from workflows.services.workflow_validation import validate_workflow

SPEC = {
    "name": "蝶羽共生纹｜纹样生成·旋转·服饰应用｜15秒概念演示",
    "duration_seconds": 15,
    "clip_seconds": 5,
    "image_model": "agnes-image-2.5-flash",
    "video_model": "agnes-video-2.5",
    "available_video_models": ["agnes-video-2.5", "agnes-video-2.5-flash"],
    "size": "1792x1024",
    "resolution": "720p",
    "fps": 24,
    "timeout_seconds": 1200,
    "credential_name": "蝶羽共生纹视频生成",
    "reference_name": "butterfly-feather-reference.png",
    "reference_summary": (
        "苗绣蝴蝶为结构骨架：保留垂直中轴、左右对称、四翼菱形分区和内部菱格。"
        "娘惹凤凰仅提取S形尾羽、渐细曲率、羽片层叠，不直接复制完整凤凰。"
        "锁定中轴→删除封闭翅形→羽线重建翅形→锯齿转化羽尖。"
        "两种文化共用一套轮廓，一眼为蝶、一线见羽。"
        "服装参考为白色新中式立领斜襟上衣，蓝灰纹样沿斜襟延伸并呼应袖口。"
    ),
    "visual_style": (
        "Create an original butterfly-feather symbiotic ornament inspired by a Chinese design board. "
        "Preserve the Miao embroidered butterfly's vertical symmetry axis, exactly four wings, "
        "diamond compartments and nested lozenges. Reshape the outer wings into flowing Nyonya "
        "phoenix-tail S curves, fine tapered feather filaments and layered pointed feather tips. "
        "Both traditions share ONE connected contour, never two separate icons. "
        "Fine dark ink and muted indigo-blue lines, ivory background, refined museum design-film "
        "aesthetic, consistent motif across shots. No real living insects, no extra wings, no logos, "
        "no invented text. Leave the bottom 18 percent clean for post-production Chinese captions. "
    ),
    "shots": [
        {
            "name": "纹样结构生成",
            "image": "Frontal flat ornament, construction axis and four geometric diamond wing compartments visible, outer feathers partially drawn, crisp delicate line art centred in a widescreen composition.",
            "motion": "A five-second explanatory drawing animation. Hold the vertical axis and inner diamond compartments steady. The closed angular outer wing boundaries dissolve; graceful S-shaped feather lines draw outward from the axis, taper into layered tips. Finish with a single symmetrical four-wing butterfly-feather motif. Locked frontal camera, gradual trace-on line animation, no chaotic morphing.",
            "caption": "01 纹样结构生成｜AI概念动画\n保留苗绣中轴与菱格，羽线重建翅形",
        },
        {
            "name": "纹样空间旋转",
            "image": "The completed four-wing butterfly-feather ornament presented as one delicate raised indigo embroidery relief floating in an ivory studio, same nested diamonds and S-shaped feather contours, three-quarter perspective, subtle material shadows.",
            "motion": "A five-second slow turntable presentation of this single butterfly-feather embroidery relief. Rotate smoothly around its vertical axis to reveal its shallow relief and fine feather filaments, then return towards a readable frontal view. Preserve exactly four wings, bilateral symmetry, diamond interiors and the original ornament topology. This is a digital concept visualization, not a manufactured specimen. Stable camera and soft studio light.",
            "caption": "02 纹样旋转｜数字空间效果示意\n保留对称骨架，展示羽片层叠",
        },
        {
            "name": "新中式服饰应用",
            "image": "A white modern Chinese mandarin-collar blouse displayed on a faceless dress form, diagonal frog-button closure, the SAME indigo butterfly-feather ornament follows the diagonal front placket and appears delicately on both cuffs. No human model. Studio fashion design visualization with visibly illustrated textile material, ivory background.",
            "motion": "A five-second fashion-design concept shot. The faceless dress form turns gently by thirty degrees; the camera slowly approaches the diagonal placket and cuff ornament. Preserve the white mandarin-collar blouse, diagonal closure and indigo butterfly-feather diamond motif. Show how the ornament follows the garment construction. Digital clothing application mockup only, no documentary photography, no manufacturing or physical-prototype claims.",
            "caption": "03 服饰应用｜AI概念效果图\n非实物成品，非已实现工艺验证",
        },
    ],
}


def make_graph(reference_url: str, credential_id: str) -> tuple[list, list]:
    nodes, edges = [], []

    def add(kind, name, config, x, y):
        item = {
            "id": str(uuid.uuid4()), "node_type": kind, "name": name,
            "position_x": x, "position_y": y, "config": config,
            "sort_order": len(nodes), "error_handling": "stop",
        }
        nodes.append(item)
        return item["id"]

    def link(source, target):
        edges.append({"source": source, "target": target})

    start = add("start", "开始制作15秒概念演示", {}, 80, 320)
    brief = add("variable", "参考依据与成片规格", {"assignments": [
        {"name": "reference_url", "value": reference_url, "source": "static"},
        {"name": "design_basis", "value": SPEC["reference_summary"], "source": "static"},
        {"name": "disclosure", "value": "全片为AI概念动画与服饰应用示意；附件为设计资料，未提供实物或已实现效果证据。", "source": "static"},
    ]}, 360, 320)
    link(start, brief)
    video_ids = []
    for index, shot in enumerate(SPEC["shots"]):
        y = 80 + index * 260
        image = add("image_generation", f"0{index + 1}·{shot['name']}关键帧", {
            "provider": "agnes", "model": SPEC["image_model"],
            "credentialId": credential_id, "prompt": SPEC["visual_style"] + shot["image"],
            "size": SPEC["size"], "n": 1, "timeout": SPEC["timeout_seconds"], "max_retries": 2,
        }, 680, y)
        video = add("video_generation", f"0{index + 1}·{shot['name']}动画", {
            "provider": "agnes", "model": SPEC["video_model"], "credentialId": credential_id,
            "prompt": SPEC["visual_style"] + shot["motion"],
            "input_image": "{images.0.url}", "duration": SPEC["clip_seconds"],
            "fps": SPEC["fps"], "resolution": SPEC["resolution"], "timeout": SPEC["timeout_seconds"],
        }, 1000, y)
        link(brief, image)
        link(image, video)
        video_ids.append(video)

    collector_code = (
        "node_outputs = input.get('input', input).get('node_outputs', {})\n"
        f"required = {video_ids!r}\n"
        "clips = []\n"
        "for node_id in required:\n"
        "    clip = node_outputs.get(node_id, {})\n"
        "    if not isinstance(clip, dict) or not clip.get('video_url') or clip.get('demo') or clip.get('error'):\n"
        "        raise ValueError('镜头生成失败或不是真实模型输出，停止合成: ' + node_id)\n"
        "    if clip.get('provider') != 'agnes':\n"
        "        raise ValueError('视频来源与配置不符')\n"
        "    clips.append(clip['video_url'])\n"
        "if len(set(clips)) != len(required):\n"
        "    raise ValueError('出现重复视频镜头，停止合成')\n"
        "output = {'video_urls': clips}\n"
    )
    collect = add("code", "按分镜顺序收集并校验三个真实片段", {"code": collector_code}, 1350, 320)
    for video in video_ids:
        link(video, collect)
    merge = add("merge", "合成15秒·每镜5秒", {
        "mode": "concat", "target_duration_sec": SPEC["duration_seconds"],
        "clip_duration_sec": SPEC["clip_seconds"], "fill_mode": "none",
    }, 1660, 320)
    link(collect, merge)
    merge_code = (
        "node_outputs = input.get('input', input).get('node_outputs', {})\n"
        f"merged = node_outputs.get({merge!r}, {{}})\n"
        "if not merged.get('concatenated') or merged.get('clip_count') != 3 or merged.get('error'):\n"
        "    raise ValueError('三个片段未成功合成，禁止以首个片段冒充成片')\n"
        "if not merged.get('video_url'):\n"
        "    raise ValueError('合成未返回视频')\n"
        "output = merged\n"
    )
    gate = add("code", "校验完整成片·禁止首片回退", {"code": merge_code}, 1950, 320)
    link(merge, gate)
    srt = "\n\n".join(
        f"{index + 1}\n00:00:{index * SPEC['clip_seconds']:02d},000 --> 00:00:{(index + 1) * SPEC['clip_seconds']:02d},000\n{shot['caption']}"
        for index, shot in enumerate(SPEC["shots"])
    ) + "\n"
    burn = add("subtitle_burn", "烧录中文分镜与概念演示声明", {
        "video_input": "{video_url}", "subtitles": srt, "subtitle_format": "srt",
    }, 2250, 320)
    link(gate, burn)
    caption_gate_code = (
        "node_outputs = input.get('input', input).get('node_outputs', {})\n"
        f"final = node_outputs.get({burn!r}, {{}})\n"
        "if not final.get('burn_subtitles_applied') or not final.get('video_url'):\n"
        "    raise ValueError('概念演示声明未成功烧录，禁止输出未标注视频')\n"
        "output = final\n"
    )
    final_gate = add("code", "检查说明已烧录", {"code": caption_gate_code}, 2550, 320)
    link(burn, final_gate)
    output = add("output", "播放与下载15秒MP4", {
        "template": "{video_url}", "format": "video", "output_variable": "final_video",
    }, 2840, 320)
    link(final_gate, output)
    end = add("end", "结束·仅概念演示", {}, 3140, 320)
    link(output, end)
    return nodes, edges


def check_gates(nodes):
    """Exercise acceptance and rejection paths without paid model calls."""
    service = LangChainService()
    code_nodes = [node for node in nodes if node["node_type"] == "code"]
    videos = [node for node in nodes if node["node_type"] == "video_generation"]
    merge = next(node for node in nodes if node["node_type"] == "merge")
    burn = next(node for node in nodes if node["node_type"] == "subtitle_burn")
    outputs = {node["id"]: {"video_url": f"https://example.test/{i}.mp4", "provider": "agnes"}
               for i, node in enumerate(videos)}
    outputs[merge["id"]] = {"video_url": "https://example.test/final.mp4", "concatenated": True, "clip_count": 3}
    outputs[burn["id"]] = {"video_url": "https://example.test/labelled.mp4", "burn_subtitles_applied": True}
    for node in code_nodes:
        assert service.run_code_node(node["config"], {"node_outputs": outputs})["success"], node["name"]
        assert not service.run_code_node(node["config"], {"node_outputs": {}})["success"], node["name"]
    bad = dict(outputs)
    bad[videos[0]["id"]] = {"video_url": "https://example.test/demo.mp4", "provider": "agnes", "demo": True}
    assert not service.run_code_node(code_nodes[0]["config"], {"node_outputs": bad})["success"]
    bad = dict(outputs)
    bad[videos[1]["id"]] = outputs[videos[0]["id"]]
    assert not service.run_code_node(code_nodes[0]["config"], {"node_outputs": bad})["success"]
    bad = dict(outputs)
    bad[merge["id"]] = {"video_url": "https://example.test/first.mp4", "concatenated": False, "clip_count": 3}
    assert not service.run_code_node(code_nodes[1]["config"], {"node_outputs": bad})["success"]
    return {"gate_checks": 9, "passed": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--video-model", choices=SPEC["available_video_models"], default=SPEC["video_model"])
    args = parser.parse_args()
    SPEC["video_model"] = args.video_model
    user = get_user_model().objects.get(username=args.username)
    credential = APICredential.objects.get(owner=user, service_type="agnes", name=SPEC["credential_name"])
    if not credential.verify_integrity() or not credential.get_decrypted_data():
        raise RuntimeError("Agnes凭证未配置或完整性检查失败")
    reference_dir = Path(settings.MEDIA_ROOT) / "workflow_references" / str(user.id)
    reference_dir.mkdir(parents=True, exist_ok=True)
    target = reference_dir / SPEC["reference_name"]
    shutil.copyfile(args.reference, target)
    reference_url = build_public_media_url(target.relative_to(settings.MEDIA_ROOT).as_posix())
    nodes, edges = make_graph(reference_url, str(credential.id))
    gate_checks = check_gates(nodes)
    description = (
        "15秒：0–5秒展示锁定中轴、羽线重建；5–10秒展示纹样空间旋转；10–15秒展示新中式斜襟服饰应用。"
        f"使用Agnes Image 2.5 Flash生成关键帧、{SPEC['video_model']}生成动态片段。"
        "设计依据来自上传资料，关键帧为AI重新演绎，不承诺逐像素复刻原纹样。"
        "全片烧录概念演示说明，不代表实物成品、已实现工艺或经过验证的结构生成算法。"
    )
    with transaction.atomic():
        workflow = Workflow.objects.create(
            name=SPEC["name"], description=description, owner=user, status="draft",
            category="视频生成", tags=["蝶羽共生纹", "15秒", "概念演示", "Agnes"],
            config={"video_spec": SPEC, "reference_url": reference_url},
        )
        for item in nodes:
            Node.objects.create(workflow=workflow, **item)
        for edge in edges:
            Edge.objects.create(workflow=workflow, source_node_id=edge["source"], target_node_id=edge["target"])
        validation = validate_workflow(workflow)
        if not validation["valid"]:
            raise RuntimeError(json.dumps(validation, ensure_ascii=False))
    report = {
        "workflow_id": str(workflow.id), "owner": user.username,
        "editor_url": f"{settings.FRONTEND_URL}/workflows/{workflow.id}/edit",
        "nodes": nodes, "edges": edges, "spec": SPEC,
        "reference_url": reference_url, "validation": validation, "gate_tests": gate_checks,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("workflow_id", "editor_url", "owner", "gate_tests")}, ensure_ascii=True))


if __name__ == "__main__":
    main()
