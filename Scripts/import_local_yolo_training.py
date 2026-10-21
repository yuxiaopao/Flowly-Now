"""Register a completed, verifiable local YOLO run under an existing Flowly user."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1] / "Backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def load_run(project):
    project = Path(project).resolve(strict=True)

    def read(relative):
        file = (project / relative).resolve(strict=True)
        if not file.is_relative_to(project):
            raise ValueError("Training source escapes the project")
        return json.loads(file.read_text(encoding="utf-8-sig"))

    config = read("training/config.json")
    name = config["training"]["name"]
    if Path(name).name != name or "/" in name or "\\" in name:
        raise ValueError("Invalid run name")
    run = project / "runs/classify" / name
    finished = read(run.relative_to(project) / "training-complete.json")
    candidate = project / "models/candidates" / name
    manifest = read(candidate.relative_to(project) / "manifest.json")
    if manifest.get("task") != "classify" or manifest.get("validation_passed") is not True:
        raise ValueError("Expected a completed classification candidate that passed validation")
    for file, key in (("best.pt", "weights_sha256"), ("model.onnx", "onnx_sha256")):
        artifact = (candidate / file).resolve(strict=True)
        if not artifact.is_relative_to(project):
            raise ValueError("Model artifact escapes the project")
        with artifact.open("rb") as stream:
            actual_digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual_digest != manifest[key]:
            raise ValueError(f"Model digest mismatch: {file}")
    with (run / "results.csv").open(encoding="utf-8-sig", newline="") as stream:
        history = [{key.strip(): float(value) for key, value in row.items()} for row in csv.DictReader(stream)]
    if not history or len({int(row["epoch"]) for row in history}) != len(history):
        raise ValueError("Training history is empty or has duplicate epochs")
    return {
        "project": project, "name": name, "run": run, "candidate": candidate,
        "config": config["training"], "manifest": manifest, "history": history, "finished": finished,
        "state": read("training/status.json"),
    }


def register_run(source, username, workflow_name):
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from tenants.models import TenantMembership
    from training.models import TrainingJob
    from workflows.models import Edge, Node, Workflow

    user = get_user_model().objects.get(username=username, is_active=True)
    project, name = str(source["project"]), source["name"]
    local = {"project_root": project, "run_name": name}
    config, manifest, history = source["config"], source["manifest"], source["history"]
    last = history[-1]
    best = max(history, key=lambda row: row["metrics/accuracy_top1"])
    membership = TenantMembership.objects.filter(user=user, is_active=True).first()
    with transaction.atomic():
        job = TrainingJob.objects.select_for_update().filter(
            created_by=user, config__local_monitor__project_root=project,
            config__local_monitor__run_name=name,
        ).first()
        if job and (not job.workflow_id or not job.node_id):
            raise ValueError("Existing import has no workflow binding; refusing ambiguous overwrite")
        if job:
            workflow, node = job.workflow, job.node
            if workflow.owner_id != user.id or workflow.is_deleted:
                raise ValueError("The original workflow is unavailable to this user")
        else:
            workflow = Workflow.objects.create(
                owner=user, tenant=membership.tenant if membership else None,
                name=workflow_name, category="模型训练", tags=["YOLO26", "PlantVillage", "分类"],
                description="已完成本机训练的真实记录。YOLO 节点关联训练任务、曲线与导出产物；执行工作流时复用已验证权重。",
            )
            start = Node.objects.create(workflow=workflow, node_type="start", name="开始", position_x=80, position_y=160, sort_order=0, config={})
            node = Node.objects.create(workflow=workflow, node_type="yolo_training", name="YOLO26m · 叶片病害分类", position_x=410, position_y=160, sort_order=1)
            end = Node.objects.create(workflow=workflow, node_type="end", name="输出分类权重与评估", position_x=810, position_y=160, sort_order=2, config={})
            Edge.objects.create(workflow=workflow, source_node=start, target_node=node)
            Edge.objects.create(workflow=workflow, source_node=node, target_node=end)
            job = TrainingJob(created_by=user, tenant=workflow.tenant, workflow=workflow, node=node)
        values = {
            "name": name, "status": "completed", "training_kind": "yolo", "framework": "ultralytics",
            "model_type": "classification", "yolo_version": "v26", "model_variant": "m",
            "config": {"local_monitor": local, "training": config, "output_dir": str(source["run"]),
                       "imported_from_completed_local_run": True},
            "dataset_path": str(source["project"] / "datasets/plantvillage/classification"),
            "dataset_source_mode": "classification_folders",
            "class_names": [item["key"] for item in manifest["classes"]],
            "model_path": str(source["candidate"] / "best.pt"),
            "best_weight_path": str(source["candidate"] / "best.pt"),
            "last_weight_path": str(source["run"] / "weights/last.pt"),
            "exported_artifacts": {"onnx": str(source["candidate"] / "model.onnx"), "manifest": str(source["candidate"] / "manifest.json")},
            "progress": 100, "current_epoch": int(last["epoch"]), "total_epochs": config["epochs"],
            "current_loss": last["train/loss"], "current_metric": last["metrics/accuracy_top1"],
            "learning_rate": last["lr/pg0"], "best_epoch": int(best["epoch"]), "best_fitness": best["metrics/accuracy_top1"],
            "metrics_history": history, "duration_seconds": round(last["time"]),
            "metrics": {key: manifest[key] for key in ("validation_top1", "validation_macro_f1", "test_top1", "test_macro_f1")},
            "started_at": datetime.fromtimestamp(source["state"]["started_at"], timezone.utc),
            "completed_at": datetime.fromtimestamp(source["finished"]["completed_at"], timezone.utc),
        }
        for field, value in values.items():
            setattr(job, field, value)
        job.save()
        node.config = {
            **(node.config or {}), "trainingMode": "local", "task": "classify",
            "yoloVersion": "v26", "modelVariant": "m", "epochs": config["epochs"],
            "batchSize": config["batch"], "imageSize": config["imgsz"], "learningRate": config["lr0"],
            "baseWeightUri": job.best_weight_path, "datasetPath": job.dataset_path,
            "datasetSource": "classification_folders", "classNames": job.class_names,
            "outputDir": str(source["run"]), "reuseTrainingJobId": str(job.id),
            "skipTrainingIfReused": True, "localMonitor": local,
        }
        node.save(update_fields=["config", "updated_at"])
    return {"workflowId": str(workflow.id), "nodeId": str(node.id), "jobId": str(job.id),
            "workflowName": workflow.name, "username": user.username}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = load_run(args.project)
    import django
    django.setup()
    result = register_run(source, args.username, args.name)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
