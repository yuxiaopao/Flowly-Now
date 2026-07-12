#!/usr/bin/env python3
"""Batch wire workflow nodes to useNodePresentation from nodeRegistry."""
from __future__ import annotations

import re
from pathlib import Path

NODES_DIR = Path(__file__).resolve().parents[1] / "src" / "components" / "workflow" / "nodes"

# filename stem -> registry type
FILE_TO_TYPE: dict[str, str] = {
    "ManualTriggerNode": "manual",
    "ScheduleTriggerNode": "schedule",
    "WebhookTriggerNode": "webhook",
    "FormTriggerNode": "form",
    "MergeNode": "merge",
    "SplitBatchesNode": "split",
    "FilterNode": "filter",
    "SetNode": "set",
    "JsonParserNode": "json_parser",
    "TextTemplateNode": "text_template",
    "DateTimeNode": "datetime",
    "RssFeedNode": "rss_feed",
    "DatasetUploadNode": "dataset_upload",
    "DataAnnotationNode": "data_annotation",
    "DataAugmentationNode": "data_augmentation",
    "ModelTrainingNode": "model_training",
    "YoloTrainingNode": "yolo_training",
    "ModelEvaluationNode": "model_evaluation",
    "ModelDeploymentNode": "model_deployment",
    "WebsiteGeneratorNode": "website_generator",
    "ImageGenerationNode": "image_generation",
    "VideoGenerationNode": "video_generation",
    "AudioGenerationNode": "audio_generation",
    "SubtitleGenerationNode": "subtitle_generation",
    "ImageEditingNode": "image_editing",
    "WebScraperNode": "web_scraper",
    "FileReaderNode": "file_reader",
    "FileWriterNode": "file_writer",
    "DocumentLoaderNode": "document_loader",
    "RetrieverNode": "retriever",
    "RerankerNode": "reranker",
    "EmbeddingNode": "embedding",
    "VectorStoreNode": "vector_store",
    "MemoryNode": "memory",
    "ExecutorNode": "executor",
    "PlannerNode": "planner",
    "AgentNode": "agent",
    "CsvTransformNode": "csv_transform",
    "JsonTransformNode": "json_transform",
    "SwitchNode": "switch",
    "ConditionNode": "condition",
    "LoopNode": "loop",
    "DelayNode": "delay",
    "SubworkflowNode": "subworkflow",
    "LLMNode": "llm",
    "PromptNode": "prompt",
    "CodeNode": "code",
    "VariableNode": "variable",
    "ToolNode": "tool",
    "HttpNode": "http",
    "EmailNode": "email",
    "TransformNode": "transform",
}

PRESENTATION_IMPORT = "import { useNodePresentation } from '@/composables/useNodePresentation'\n"
PRESENTATION_BLOCK = "\nconst NODE_TYPE = '{node_type}'\nconst {{ nodeIcon, nodeColor, nodeLabel }} = useNodePresentation(NODE_TYPE)\n"

COLOR_PATTERNS = [
    re.compile(r"^const nodeColor = ['\"][^'\"]+['\"]\s*$", re.M),
    re.compile(r"^const color = ['\"][^'\"]+['\"]\s*$", re.M),
]


def patch_file(path: Path, node_type: str) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text

    if "useNodePresentation" in text and f"NODE_TYPE = '{node_type}'" in text:
        return False

    if PRESENTATION_IMPORT.strip() not in text:
        # insert after last import from lucide or vue-flow
        m = list(re.finditer(r"^import .+$", text, re.M))
        if not m:
            return False
        insert_at = m[-1].end()
        text = text[:insert_at] + "\n" + PRESENTATION_IMPORT + text[insert_at:]

    for pat in COLOR_PATTERNS:
        text = pat.sub("", text)

    # insert presentation block before first const props or defineProps closing
    if f"NODE_TYPE = '{node_type}'" not in text:
        m = re.search(r"(const props = defineProps\([\s\S]*?\)\n)", text)
        if m:
            insert_at = m.end()
            text = text[:insert_at] + PRESENTATION_BLOCK.format(node_type=node_type) + text[insert_at:]
        else:
            m = re.search(r"(defineProps\([\s\S]*?\)\n)", text)
            if m:
                insert_at = m.end()
                text = text[:insert_at] + PRESENTATION_BLOCK.format(node_type=node_type) + text[insert_at:]

    # v-bind(color) -> v-bind(nodeColor) for core/trigger
    text = text.replace("v-bind(color)", "v-bind(nodeColor)")
    text = text.replace("color + '22'", "nodeColor + '22'")
    text = text.replace("color + '15'", "nodeColor + '15'")
    text = text.replace("color + '18'", "nodeColor + '18'")
    text = text.replace("color + '40'", "nodeColor + '40'")
    text = text.replace("{ color }", "{ color: nodeColor }")
    text = text.replace(":style=\"{ color }\"", ":style=\"{ color: nodeColor }\"")
    text = text.replace("border: 2px solid v-bind(color)", "border: 2px solid v-bind(nodeColor)")

    # domain nodes: add --node-accent on root if domain-node class present
    if "class=\"domain-node" in text and "--node-accent" not in text:
        text = text.replace(
            "class=\"domain-node",
            ":style=\"{ '--node-accent': nodeColor }\" class=\"domain-node",
            1,
        )

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for stem, node_type in FILE_TO_TYPE.items():
        path = NODES_DIR / f"{stem}.vue"
        if not path.exists():
            continue
        if patch_file(path, node_type):
            print(f"patched {path.name}")
            changed += 1
    print(f"done: {changed} files")


if __name__ == "__main__":
    main()
