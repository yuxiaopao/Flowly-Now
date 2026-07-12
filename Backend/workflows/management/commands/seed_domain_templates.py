"""
Seed command for domain workflow templates.
Usage: python manage.py seed_domain_templates
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from workflows.models import WorkflowTemplate, TemplateCategory

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with domain workflow templates'

    def handle(self, *args, **options):
        self.stdout.write('Seeding domain templates...')

        # Create categories
        categories = self._create_categories()

        # Create templates
        self._create_multimodal_templates(categories)
        self._create_video_translation_template(categories)
        self._create_rag_templates(categories)
        self._create_ml_templates(categories)
        self._create_yolo_detection_template(categories)
        self._create_yolo_detection_v2_template(categories)
        self._create_clip_retrieval_template(categories)
        self._create_transformer_classification_template(categories)
        self._create_agent_templates(categories)
        self._create_utility_templates(categories)
        self._create_hybrid_templates(categories)

        self.stdout.write(self.style.SUCCESS('Successfully seeded domain templates'))

    def _create_categories(self):
        """Create template categories."""
        categories_data = [
            {
                "name": "Multimodal Generation",
                "slug": "multimodal",
                "description": "Generate images, videos, audio, and subtitles with AI",
                "icon": "sparkles",
                "color": "#ec4899",
                "sort_order": 1,
            },
            {
                "name": "Data Management",
                "slug": "data",
                "description": "Upload, annotate, and augment datasets",
                "icon": "upload",
                "color": "#10b981",
                "sort_order": 2,
            },
            {
                "name": "ML & MLOps",
                "slug": "mlops",
                "description": "Train, evaluate, and deploy machine learning models",
                "icon": "brain",
                "color": "#f59e0b",
                "sort_order": 3,
            },
            {
                "name": "RAG & Knowledge",
                "slug": "rag",
                "description": "Build retrieval-augmented generation pipelines",
                "icon": "database",
                "color": "#06b6d4",
                "sort_order": 4,
            },
            {
                "name": "AI Agents",
                "slug": "agent",
                "description": "Deploy autonomous AI agents with tools and memory",
                "icon": "bot",
                "color": "#8b5cf6",
                "sort_order": 5,
            },
            {
                "name": "Utilities",
                "slug": "utility",
                "description": "File operations, web scraping, and data transforms",
                "icon": "zap",
                "color": "#6366f1",
                "sort_order": 6,
            },
        ]

        categories = {}
        for cat_data in categories_data:
            obj, created = TemplateCategory.objects.get_or_create(
                slug=cat_data["slug"],
                defaults=cat_data
            )
            categories[cat_data["slug"]] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {obj.name}"))
            else:
                self.stdout.write(f"Category already exists: {obj.name}")

        return categories

    def _create_multimodal_templates(self, categories):
        """Template 1: AI Video Production Pipeline."""
        category = categories["multimodal"]

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "Text Input",
                        "inputs": {"prompt": {"type": "string", "label": "Video Prompt"}}
                    }
                },
                {
                    "id": "image_gen_1",
                    "type": "image_generation",
                    "position": {"x": 300, "y": 200},
                    "data": {
                        "name": "image_generation",
                        "label": "Image Generation",
                        "provider": "openai",
                        "model": "dall-e-3",
                        "inputs": {
                            "prompt": {"type": "expression", "value": "{{ trigger_1.prompt }}"},
                            "n": {"type": "number", "value": 1}
                        }
                    }
                },
                {
                    "id": "video_gen_1",
                    "type": "video_generation",
                    "position": {"x": 500, "y": 200},
                    "data": {
                        "name": "video_generation",
                        "label": "Video Generation",
                        "provider": "replicate",
                        "inputs": {
                            "prompt": {"type": "expression", "value": "{{ trigger_1.prompt }}"},
                            "duration": {"type": "number", "value": 4}
                        }
                    }
                },
                {
                    "id": "subtitle_1",
                    "type": "subtitle_generation",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "name": "subtitle_generation",
                        "label": "Subtitle Generation",
                        "inputs": {
                            "inputType": {"type": "string", "value": "video"},
                            "inputPath": {"type": "expression", "value": "{{ video_gen_1.output.video_url }}"},
                            "language": {"type": "string", "value": "en"},
                            "format": {"type": "string", "value": "srt"}
                        }
                    }
                },
                {
                    "id": "image_edit_1",
                    "type": "image_editing",
                    "position": {"x": 300, "y": 350},
                    "data": {
                        "name": "image_editing",
                        "label": "Image Editing",
                        "provider": "openai",
                        "inputs": {
                            "image": {"type": "expression", "value": "{{ image_gen_1.output.images[0].url }}"},
                            "instruction": {"type": "string", "value": "Enhance for cinematic look"}
                        }
                    }
                },
                {
                    "id": "file_writer_1",
                    "type": "file_writer",
                    "position": {"x": 900, "y": 150},
                    "data": {
                        "name": "file_writer",
                        "label": "Save Video",
                        "inputs": {
                            "path": {"type": "expression", "value": "/output/{{ trigger_1.id }}/video.mp4"},
                            "content": {"type": "expression", "value": "{{ video_gen_1.output }}"}
                        }
                    }
                },
                {
                    "id": "file_writer_2",
                    "type": "file_writer",
                    "position": {"x": 900, "y": 250},
                    "data": {
                        "name": "file_writer",
                        "label": "Save Subtitles",
                        "inputs": {
                            "path": {"type": "expression", "value": "/output/{{ trigger_1.id }}/subtitles.srt"},
                            "content": {"type": "expression", "value": "{{ subtitle_1.output }}"}
                        }
                    }
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 1100, "y": 200},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "message": "Video created with subtitles"
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "image_gen_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "trigger_1", "target": "video_gen_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e3", "source": "video_gen_1", "target": "subtitle_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e4", "source": "image_gen_1", "target": "image_edit_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e5", "source": "subtitle_1", "target": "file_writer_2", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e6", "source": "video_gen_1", "target": "file_writer_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e7", "source": "file_writer_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
            ]
        }

        variables_schema = [
            {
                "name": "prompt",
                "type": "string",
                "label": "Video Prompt",
                "description": "Text description of the video to generate",
                "required": True
            }
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="ai-video-production-pipeline",
            defaults={
                "category": category,
                "name": "AI Video Production Pipeline",
                "description": "Automatically generate videos from text prompts with AI-powered editing and subtitle generation",
                "difficulty": "intermediate",
                "tags": ["video", "AI", "automation", "content creation"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "10 min",
                "required_apis": ["openai", "replicate"],
                "use_count": 0,
                "rating": 4.8,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")

    def _create_video_translation_template(self, categories):
        """Template: Video multilingual translation with lip sync and subtitles."""
        category = categories.get("multimodal") or categories.get("content")

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "Video Input",
                        "inputs": {
                            "video_url": {"type": "expression", "value": "{{ video_url }}"},
                        },
                    },
                },
                {
                    "id": "video_translation_1",
                    "type": "video_translation",
                    "position": {"x": 400, "y": 200},
                    "data": {
                        "name": "video_translation",
                        "label": "Video Translation",
                        "inputs": {
                            "video_input": {"type": "expression", "value": "{{ trigger_1.output.video_url }}"},
                            "source_language": {"type": "static", "value": "zh"},
                            "target_languages": {"type": "static", "value": ["en"]},
                            "voice": {"type": "static", "value": "longanyang"},
                            "subtitle_format": {"type": "static", "value": "srt"},
                            "burn_subtitles": {"type": "static", "value": True},
                            "lip_sync": {"type": "static", "value": True},
                            "provider": {"type": "static", "value": "dashscope"},
                        },
                    },
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "message": "Translated video with subtitles",
                    },
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "video_translation_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "video_translation_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
            ],
        }

        variables_schema = [
            {
                "name": "video_url",
                "type": "string",
                "label": "Video URL",
                "description": "Public URL of the source video to translate",
                "required": True,
            },
            {
                "name": "target_language",
                "type": "string",
                "label": "Target Language",
                "description": "Target language code (e.g. en, ja, ko)",
                "required": False,
                "default": "en",
            },
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="video-multilingual-translation",
            defaults={
                "category": category,
                "name": "视频多语言翻译",
                "description": "Translate video speech with AI dubbing, lip sync, and burned-in subtitles",
                "difficulty": "advanced",
                "tags": ["video", "translation", "lip-sync", "subtitles", "multilingual"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "15 min",
                "required_apis": ["dashscope"],
                "use_count": 0,
                "rating": 4.7,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")

    def _create_rag_templates(self, categories):
        """Template 2: RAG Knowledge Q&A System."""
        category = categories["rag"]

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "User Query",
                        "inputs": {
                            "input": {"type": "string", "label": "Question"},
                            "url": {"type": "string", "label": "Document URL"}
                        }
                    }
                },
                {
                    "id": "doc_loader_1",
                    "type": "document_loader",
                    "position": {"x": 300, "y": 200},
                    "data": {
                        "name": "document_loader",
                        "label": "Document Loader",
                        "inputs": {
                            "sourceType": {"type": "string", "value": "url"},
                            "path": {"type": "expression", "value": "{{ trigger_1.url }}"},
                            "parser": {"type": "string", "value": "txt"},
                            "chunkSize": {"type": "number", "value": 500}
                        }
                    }
                },
                {
                    "id": "embedding_1",
                    "type": "embedding",
                    "position": {"x": 500, "y": 200},
                    "data": {
                        "name": "embedding",
                        "label": "Embedding",
                        "provider": "openai",
                        "model": "text-embedding-3-small",
                        "inputs": {
                            "batchSize": {"type": "number", "value": 100}
                        }
                    }
                },
                {
                    "id": "vector_store_1",
                    "type": "vector_store",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "name": "vector_store",
                        "label": "Vector Store",
                        "provider": "chroma",
                        "inputs": {
                            "indexName": {"type": "string", "value": "knowledge_base"}
                        }
                    }
                },
                {
                    "id": "retriever_1",
                    "type": "retriever",
                    "position": {"x": 500, "y": 350},
                    "data": {
                        "name": "retriever",
                        "label": "Retriever",
                        "inputs": {
                            "query": {"type": "expression", "value": "{{ trigger_1.input }}"},
                            "topK": {"type": "number", "value": 5}
                        }
                    }
                },
                {
                    "id": "llm_1",
                    "type": "llm",
                    "position": {"x": 700, "y": 350},
                    "data": {
                        "name": "llm",
                        "label": "LLM Answer",
                        "model": "gpt-4o",
                        "inputs": {
                            "systemPrompt": {"type": "string", "value": "You are a helpful assistant. Use the provided context to answer questions."},
                            "userTemplate": {"type": "string", "value": "Context:\n{{ retriever_1.documents }}\n\nQuestion: {{ trigger_1.input }}"}
                        }
                    }
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 900, "y": 350},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "response": {"type": "expression", "value": "{{ llm_1.response }}"}
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "doc_loader_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "doc_loader_1", "target": "embedding_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e3", "source": "embedding_1", "target": "vector_store_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e4", "source": "vector_store_1", "target": "retriever_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e5", "source": "retriever_1", "target": "llm_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e6", "source": "llm_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
            ]
        }

        variables_schema = [
            {
                "name": "input",
                "type": "string",
                "label": "Question",
                "description": "The question to ask the knowledge base",
                "required": True
            },
            {
                "name": "url",
                "type": "string",
                "label": "Document URL",
                "description": "URL of the document to load into knowledge base",
                "required": True
            }
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="rag-knowledge-qa-system",
            defaults={
                "category": category,
                "name": "RAG Knowledge Q&A System",
                "description": "Build a complete RAG pipeline: load documents, chunk, embed, store, retrieve, and answer questions",
                "difficulty": "intermediate",
                "tags": ["RAG", "knowledge base", "Q&A", "vector search"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "15 min",
                "required_apis": ["openai", "chroma"],
                "use_count": 0,
                "rating": 4.9,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")

    def _create_ml_templates(self, categories):
        """Template 3: AutoML Training Pipeline."""
        category = categories["mlops"]

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "Dataset Input",
                        "inputs": {"dataset_url": {"type": "string", "label": "Dataset URL"}}
                    }
                },
                {
                    "id": "dataset_upload_1",
                    "type": "dataset_upload",
                    "position": {"x": 300, "y": 200},
                    "data": {
                        "name": "dataset_upload",
                        "label": "Dataset Upload",
                        "inputs": {
                            "source": {"type": "string", "value": "url"},
                            "path": {"type": "expression", "value": "{{ trigger_1.dataset_url }}"},
                            "format": {"type": "string", "value": "csv"}
                        }
                    }
                },
                {
                    "id": "annotation_1",
                    "type": "data_annotation",
                    "position": {"x": 500, "y": 200},
                    "data": {
                        "name": "data_annotation",
                        "label": "Data Annotation",
                        "inputs": {
                            "annotationType": {"type": "string", "value": "classification"},
                            "labels": {"type": "array", "value": ["positive", "negative"]},
                            "modelAssisted": {"type": "boolean", "value": True}
                        }
                    }
                },
                {
                    "id": "augmentation_1",
                    "type": "data_augmentation",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "name": "data_augmentation",
                        "label": "Data Augmentation",
                        "inputs": {
                            "strategy": {"type": "string", "value": "geometric"},
                            "ratio": {"type": "number", "value": 2.0}
                        }
                    }
                },
                {
                    "id": "training_1",
                    "type": "model_training",
                    "position": {"x": 500, "y": 350},
                    "data": {
                        "name": "model_training",
                        "label": "Model Training",
                        "framework": "pytorch",
                        "modelType": "classifier",
                        "inputs": {
                            "epochs": {"type": "number", "value": 10},
                            "batchSize": {"type": "number", "value": 32},
                            "learningRate": {"type": "number", "value": 0.001}
                        }
                    }
                },
                {
                    "id": "evaluation_1",
                    "type": "model_evaluation",
                    "position": {"x": 700, "y": 350},
                    "data": {
                        "name": "model_evaluation",
                        "label": "Model Evaluation",
                        "inputs": {
                            "modelPath": {"type": "expression", "value": "{{ training_1.output.model_path }}"},
                            "testDataset": {"type": "expression", "value": "{{ trigger_1.dataset_url }}"},
                            "metrics": {"type": "array", "value": ["accuracy", "precision", "recall", "f1"]}
                        }
                    }
                },
                {
                    "id": "deployment_1",
                    "type": "model_deployment",
                    "position": {"x": 900, "y": 350},
                    "data": {
                        "name": "model_deployment",
                        "label": "Model Deployment",
                        "platform": "sagemaker",
                        "endpointType": "realtime",
                        "inputs": {
                            "autoscaling": {"type": "boolean", "value": True}
                        }
                    }
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 1100, "y": 350},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "deployment_url": {"type": "expression", "value": "{{ deployment_1.endpoint_name }}"}
                    }
                },
                {
                    "id": "output_2",
                    "type": "output",
                    "position": {"x": 900, "y": 500},
                    "data": {
                        "name": "output",
                        "label": "Evaluation Results",
                        "metrics": {"type": "expression", "value": "{{ evaluation_1.output }}"}
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "dataset_upload_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "dataset_upload_1", "target": "annotation_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e3", "source": "annotation_1", "target": "augmentation_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e4", "source": "augmentation_1", "target": "training_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e5", "source": "training_1", "target": "evaluation_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e6", "source": "evaluation_1", "target": "deployment_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e7", "source": "deployment_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e8", "source": "evaluation_1", "target": "output_2", "sourceHandle": "output", "targetHandle": "input"},
            ]
        }

        variables_schema = [
            {
                "name": "dataset_url",
                "type": "string",
                "label": "Dataset URL",
                "description": "URL or path to the training dataset (CSV format)",
                "required": True
            }
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="automl-training-pipeline",
            defaults={
                "category": category,
                "name": "AutoML Training Pipeline",
                "description": "End-to-end ML pipeline: upload dataset, annotate, augment, train, evaluate, and deploy model",
                "difficulty": "advanced",
                "tags": ["ML", "automation", "training", "deployment"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "30 min",
                "required_apis": ["aws-sagemaker"],
                "use_count": 0,
                "rating": 4.6,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")

    def _create_yolo_detection_template(self, categories):
        """YOLO detection project: dataset → train → website generator."""
        category = categories["mlops"]
        workflow_data = {
            "nodes": [
                {
                    "id": "dataset_upload_1",
                    "type": "dataset_upload",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "label": "上传标注数据集",
                        "config": {"format": "yolo", "sourceType": "upload"},
                    },
                },
                {
                    "id": "yolo_training_1",
                    "type": "yolo_training",
                    "position": {"x": 400, "y": 200},
                    "data": {
                        "label": "YOLO 训练",
                        "config": {
                            "trainingMode": "local",
                            "yoloVersion": "v8",
                            "modelVariant": "n",
                            "epochs": 50,
                            "batchSize": 16,
                            "imageSize": 640,
                        },
                    },
                },
                {
                    "id": "project_profiler_1",
                    "type": "project_profiler",
                    "position": {"x": 550, "y": 200},
                    "data": {
                        "label": "场景分析",
                        "config": {"websiteType": "detection", "useLlmEnrich": False},
                    },
                },
                {
                    "id": "website_generator_1",
                    "type": "website_generator",
                    "position": {"x": 750, "y": 200},
                    "data": {
                        "label": "生成识别网站",
                        "config": {
                            "websiteType": "detection",
                            "qaProfile": "default",
                            "wizard": {
                                "siteName": "YOLO 识别系统",
                                "usageDescription": "上传现场图片进行目标检测",
                                "wizardCompleted": True,
                            },
                        },
                    },
                },
                {
                    "id": "environment_provision_1",
                    "type": "environment_provision",
                    "position": {"x": 950, "y": 200},
                    "data": {
                        "label": "环境配置",
                        "config": {"runtimeMode": "desktop"},
                    },
                },
                {
                    "id": "site_qa_1",
                    "type": "site_qa",
                    "position": {"x": 1300, "y": 200},
                    "data": {
                        "label": "站点自查",
                        "config": {
                            "websiteType": "detection",
                            "qaProfile": "default",
                            "skipPlaywright": False,
                        },
                    },
                },
                {
                    "id": "site_preview_1",
                    "type": "site_preview",
                    "position": {"x": 1600, "y": 200},
                    "data": {
                        "label": "站点预览",
                        "config": {"qaProfile": "default"},
                    },
                },
                {
                    "id": "project_agent_1",
                    "type": "project_agent",
                    "position": {"x": 1900, "y": 200},
                    "data": {
                        "label": "项目 Agent",
                        "config": {
                            "qaProfile": "default",
                            "autoQaAfterEdit": True,
                            "message": "",
                        },
                    },
                },
            ],
            "edges": [
                {"id": "e1", "source": "dataset_upload_1", "target": "yolo_training_1"},
                {"id": "e2", "source": "yolo_training_1", "target": "project_profiler_1"},
                {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1"},
                {"id": "e4", "source": "website_generator_1", "target": "environment_provision_1"},
                {"id": "e5", "source": "environment_provision_1", "target": "site_qa_1"},
                {"id": "e6", "source": "site_qa_1", "target": "site_preview_1"},
                {"id": "e7", "source": "site_preview_1", "target": "project_agent_1"},
            ],
        }
        template, created = WorkflowTemplate.objects.get_or_create(
            slug="yolo-detection-project",
            defaults={
                "category": category,
                "name": "YOLO 识别项目",
                "description": "上传已标注数据集 → YOLO 训练 → 场景分析 → 建站向导 → 环境 → QA → 预览 → Agent",
                "difficulty": "intermediate",
                "tags": ["YOLO", "detection", "MLOps", "website"],
                "workflow_data": workflow_data,
                "variables_schema": [],
                "estimated_duration": "2-4 hours",
                "required_apis": [],
                "use_count": 0,
                "rating": 4.8,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            template.workflow_data = workflow_data
            template.description = "上传已标注数据集 → YOLO 训练 → 场景分析 → 建站向导 → 环境 → QA → 预览 → Agent"
            template.save(update_fields=["workflow_data", "description"])
            self.stdout.write(f"Updated template: {template.name}")

    def _create_yolo_detection_v2_template(self, categories):
        """YOLO detection v2: scaffold + AI role agents + QA + preview + agent."""
        category = categories["mlops"]
        workflow_data = {
            "nodes": [
                {
                    "id": "dataset_upload_1",
                    "type": "dataset_upload",
                    "position": {"x": 80, "y": 200},
                    "data": {
                        "label": "上传标注数据集",
                        "config": {"format": "yolo", "sourceType": "upload"},
                    },
                },
                {
                    "id": "yolo_training_1",
                    "type": "yolo_training",
                    "position": {"x": 280, "y": 200},
                    "data": {
                        "label": "YOLO 训练",
                        "config": {
                            "trainingMode": "local",
                            "yoloVersion": "v8",
                            "modelVariant": "n",
                            "epochs": 50,
                            "batchSize": 16,
                            "imageSize": 640,
                        },
                    },
                },
                {
                    "id": "project_profiler_1",
                    "type": "project_profiler",
                    "position": {"x": 480, "y": 200},
                    "data": {
                        "label": "场景分析",
                        "config": {"websiteType": "detection", "useLlmEnrich": False},
                    },
                },
                {
                    "id": "website_generator_1",
                    "type": "website_generator",
                    "position": {"x": 680, "y": 200},
                    "data": {
                        "label": "网站脚手架",
                        "config": {
                            "websiteType": "detection",
                            "waitForCompletion": True,
                            "wizard": {
                                "siteName": "YOLO 识别系统",
                                "usageDescription": "上传现场图片进行目标检测",
                                "wizardCompleted": True,
                            },
                        },
                    },
                },
                {
                    "id": "backend_setup_1",
                    "type": "backend_setup",
                    "position": {"x": 880, "y": 200},
                    "data": {
                        "label": "后端搭建",
                        "config": {"agentMode": "auto", "allowCoreEdit": True},
                    },
                },
                {
                    "id": "frontend_setup_1",
                    "type": "frontend_setup",
                    "position": {"x": 1080, "y": 200},
                    "data": {
                        "label": "前端搭建",
                        "config": {"agentMode": "auto"},
                    },
                },
                {
                    "id": "ui_beautify_1",
                    "type": "ui_beautify",
                    "position": {"x": 1280, "y": 200},
                    "data": {
                        "label": "UI 美化",
                        "config": {"agentMode": "auto"},
                    },
                },
                {
                    "id": "environment_provision_1",
                    "type": "environment_provision",
                    "position": {"x": 1480, "y": 200},
                    "data": {
                        "label": "环境配置",
                        "config": {"runtimeMode": "desktop"},
                    },
                },
                {
                    "id": "site_qa_1",
                    "type": "site_qa",
                    "position": {"x": 1680, "y": 200},
                    "data": {
                        "label": "站点自查",
                        "config": {
                            "websiteType": "detection",
                            "qaProfile": "default",
                            "skipPlaywright": False,
                        },
                    },
                },
                {
                    "id": "site_code_review_1",
                    "type": "site_code_review",
                    "position": {"x": 1880, "y": 200},
                    "data": {
                        "label": "代码复查",
                        "config": {"agentMode": "auto", "maxRounds": 2},
                    },
                },
                {
                    "id": "site_preview_1",
                    "type": "site_preview",
                    "position": {"x": 2080, "y": 200},
                    "data": {
                        "label": "站点预览",
                        "config": {"qaProfile": "default"},
                    },
                },
                {
                    "id": "project_agent_1",
                    "type": "project_agent",
                    "position": {"x": 2280, "y": 200},
                    "data": {
                        "label": "项目 Agent",
                        "config": {
                            "qaProfile": "default",
                            "autoQaAfterEdit": True,
                            "message": "",
                        },
                    },
                },
            ],
            "edges": [
                {"id": "e1", "source": "dataset_upload_1", "target": "yolo_training_1"},
                {"id": "e2", "source": "yolo_training_1", "target": "project_profiler_1"},
                {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1"},
                {"id": "e4", "source": "website_generator_1", "target": "backend_setup_1"},
                {"id": "e5", "source": "backend_setup_1", "target": "frontend_setup_1"},
                {"id": "e6", "source": "frontend_setup_1", "target": "ui_beautify_1"},
                {"id": "e7", "source": "ui_beautify_1", "target": "environment_provision_1"},
                {"id": "e8", "source": "environment_provision_1", "target": "site_qa_1"},
                {"id": "e9", "source": "site_qa_1", "target": "site_code_review_1"},
                {"id": "e10", "source": "site_code_review_1", "target": "site_preview_1"},
                {"id": "e11", "source": "site_preview_1", "target": "project_agent_1"},
            ],
        }
        template, created = WorkflowTemplate.objects.get_or_create(
            name="YOLO 识别项目 v2（AI 分工）",
            defaults={
                "category": category,
                "name": "YOLO 识别项目 v2（AI 分工）",
                "description": "训练 → 脚手架 → 后端/前端/UI Agent → 环境 → QA → 复查 → 预览 → Agent",
                "difficulty": "intermediate",
                "tags": ["YOLO", "detection", "MLOps", "website", "ai-agents"],
                "workflow_data": workflow_data,
                "variables_schema": [],
                "estimated_duration": "2-4 hours",
                "required_apis": [],
                "use_count": 0,
                "rating": 4.9,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            template.workflow_data = workflow_data
            template.save(update_fields=["workflow_data"])
            self.stdout.write(f"Updated template: {template.name}")

    def _create_clip_retrieval_template(self, categories):
        """CLIP retrieval project workflow template (M4)."""
        category = categories.get("ml") or categories.get("computer_vision") or list(categories.values())[0]

        workflow_data = {
            "nodes": [
                {
                    "id": "dataset_upload_1",
                    "type": "dataset_upload",
                    "position": {"x": 80, "y": 200},
                    "data": {
                        "label": "上传图文数据集",
                        "config": {"format": "image_text_pairs", "source": "upload"},
                    },
                },
                {
                    "id": "clip_retrieval_1",
                    "type": "clip_retrieval",
                    "position": {"x": 280, "y": 200},
                    "data": {
                        "label": "CLIP 检索索引",
                        "config": {"indexType": "flat", "baseModel": "simple-bow"},
                    },
                },
                {
                    "id": "project_profiler_1",
                    "type": "project_profiler",
                    "position": {"x": 480, "y": 200},
                    "data": {
                        "label": "场景分析",
                        "config": {"websiteType": "clip_retrieval", "useLlmEnrich": False},
                    },
                },
                {
                    "id": "website_generator_1",
                    "type": "website_generator",
                    "position": {"x": 680, "y": 200},
                    "data": {
                        "label": "生成检索网站",
                        "config": {
                            "websiteType": "clip_retrieval",
                            "qaProfile": "default",
                            "wizard": {
                                "siteName": "CLIP 图文检索",
                                "usageDescription": "输入文字描述，搜索相似图片",
                                "primaryColor": "#06b6d4",
                                "wizardCompleted": True,
                            },
                        },
                    },
                },
                {
                    "id": "environment_provision_1",
                    "type": "environment_provision",
                    "position": {"x": 880, "y": 200},
                    "data": {"label": "环境配置", "config": {"runtimeMode": "desktop"}},
                },
                {
                    "id": "site_qa_1",
                    "type": "site_qa",
                    "position": {"x": 1080, "y": 200},
                    "data": {
                        "label": "站点自查",
                        "config": {"websiteType": "clip_retrieval", "qaProfile": "default", "skipPlaywright": True},
                    },
                },
                {
                    "id": "site_preview_1",
                    "type": "site_preview",
                    "position": {"x": 1280, "y": 200},
                    "data": {"label": "站点预览", "config": {"qaProfile": "default"}},
                },
                {
                    "id": "project_agent_1",
                    "type": "project_agent",
                    "position": {"x": 1480, "y": 200},
                    "data": {"label": "项目 Agent", "config": {"autoQaAfterEdit": True}},
                },
            ],
            "edges": [
                {"id": "e1", "source": "dataset_upload_1", "target": "clip_retrieval_1"},
                {"id": "e2", "source": "clip_retrieval_1", "target": "project_profiler_1"},
                {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1"},
                {"id": "e4", "source": "website_generator_1", "target": "environment_provision_1"},
                {"id": "e5", "source": "environment_provision_1", "target": "site_qa_1"},
                {"id": "e6", "source": "site_qa_1", "target": "site_preview_1"},
                {"id": "e7", "source": "site_preview_1", "target": "project_agent_1"},
            ],
        }
        template, created = WorkflowTemplate.objects.get_or_create(
            slug="clip-retrieval-project",
            defaults={
                "category": category,
                "name": "CLIP 检索项目",
                "description": "图文数据集 → CLIP 索引 → 检索站 → QA → 预览 → Agent",
                "difficulty": "intermediate",
                "tags": ["CLIP", "retrieval", "MLOps", "website"],
                "workflow_data": workflow_data,
                "variables_schema": [],
                "estimated_duration": "1-2 hours",
                "required_apis": [],
                "use_count": 0,
                "rating": 4.7,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            template.workflow_data = workflow_data
            template.save(update_fields=["workflow_data", "description"])
            self.stdout.write(f"Updated template: {template.name}")

    def _create_transformer_classification_template(self, categories):
        """Transformer fine-tune → classification site factory chain."""
        category = categories.get("ml") or categories.get("computer_vision") or list(categories.values())[0]
        workflow_data = {
            "nodes": [
                {"id": "dataset_upload_1", "type": "dataset_upload", "position": {"x": 80, "y": 200},
                 "data": {"label": "上传数据集", "config": {"format": "image_folder", "sourceType": "upload"}}},
                {"id": "model_training_1", "type": "model_training", "position": {"x": 280, "y": 200},
                 "data": {"label": "Transformer 微调", "config": {
                     "framework": "transformers", "trainingKind": "transformer",
                     "baseWeightUri": "bert-base-uncased", "epochs": 10}}},
                {"id": "project_profiler_1", "type": "project_profiler", "position": {"x": 480, "y": 200},
                 "data": {"label": "场景分析", "config": {"websiteType": "classification", "useLlmEnrich": True}}},
                {"id": "website_generator_1", "type": "website_generator", "position": {"x": 680, "y": 200},
                 "data": {"label": "生成分类网站", "config": {"websiteType": "classification", "backendFramework": "flask"}}},
                {"id": "environment_provision_1", "type": "environment_provision", "position": {"x": 880, "y": 200},
                 "data": {"label": "环境配置", "config": {"runtimeMode": "desktop"}}},
                {"id": "site_qa_1", "type": "site_qa", "position": {"x": 1080, "y": 200},
                 "data": {"label": "站点自查", "config": {"websiteType": "classification"}}},
                {"id": "site_preview_1", "type": "site_preview", "position": {"x": 1280, "y": 200},
                 "data": {"label": "站点预览", "config": {}}},
                {"id": "project_agent_1", "type": "project_agent", "position": {"x": 1480, "y": 200},
                 "data": {"label": "项目 Agent", "config": {"agentMode": "auto"}}},
            ],
            "edges": [
                {"id": "e1", "source": "dataset_upload_1", "target": "model_training_1"},
                {"id": "e2", "source": "model_training_1", "target": "project_profiler_1"},
                {"id": "e3", "source": "project_profiler_1", "target": "website_generator_1"},
                {"id": "e4", "source": "website_generator_1", "target": "environment_provision_1"},
                {"id": "e5", "source": "environment_provision_1", "target": "site_qa_1"},
                {"id": "e6", "source": "site_qa_1", "target": "site_preview_1"},
                {"id": "e7", "source": "site_preview_1", "target": "project_agent_1"},
            ],
        }
        template, created = WorkflowTemplate.objects.get_or_create(
            slug="transformer-classification-project",
            defaults={
                "category": category,
                "name": "Transformer 微调项目",
                "description": "数据集 → Transformer 微调 → 分类站 → QA → 预览 → Agent",
                "difficulty": "intermediate",
                "tags": ["Transformers", "classification", "MLOps", "website"],
                "workflow_data": workflow_data,
                "variables_schema": [],
                "estimated_duration": "2-4 hours",
                "required_apis": [],
                "use_count": 0,
                "rating": 4.6,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            template.workflow_data = workflow_data
            template.save(update_fields=["workflow_data", "description"])
            self.stdout.write(f"Updated template: {template.name}")

    def _create_agent_templates(self, categories):
        """Template 4: Multi-Agent Research Assistant."""
        category = categories["agent"]

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "Research Task",
                        "inputs": {
                            "task": {"type": "string", "label": "Research Topic", "value": "Research the latest developments in quantum computing"}
                        }
                    }
                },
                {
                    "id": "planner_1",
                    "type": "planner",
                    "position": {"x": 300, "y": 200},
                    "data": {
                        "name": "planner",
                        "label": "Task Planner",
                        "model": "gpt-4o",
                        "inputs": {
                            "decompositionStrategy": {"type": "string", "value": "sequential"},
                            "maxSubtasks": {"type": "number", "value": 5}
                        }
                    }
                },
                {
                    "id": "researcher_1",
                    "type": "agent",
                    "position": {"x": 500, "y": 200},
                    "data": {
                        "name": "researcher_agent",
                        "label": "Research Agent",
                        "model": "gpt-4o",
                        "inputs": {
                            "tools": {"type": "array", "value": ["web_scraper", "document_loader"]},
                            "maxIterations": {"type": "number", "value": 5},
                            "memoryEnabled": {"type": "boolean", "value": True}
                        }
                    }
                },
                {
                    "id": "executor_1",
                    "type": "executor",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "name": "executor",
                        "label": "Task Executor",
                        "inputs": {
                            "toolSelection": {"type": "string", "value": "auto"},
                            "contextWindow": {"type": "number", "value": 128000}
                        }
                    }
                },
                {
                    "id": "memory_1",
                    "type": "memory",
                    "position": {"x": 700, "y": 350},
                    "data": {
                        "name": "memory",
                        "label": "Agent Memory",
                        "memoryType": "conversation",
                        "inputs": {
                            "maxItems": {"type": "number", "value": 100}
                        }
                    }
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 900, "y": 200},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "summary": {"type": "expression", "value": "{{ executor_1.results }}"}
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "planner_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "planner_1", "target": "researcher_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e3", "source": "researcher_1", "target": "executor_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e4", "source": "executor_1", "target": "memory_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e5", "source": "memory_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e6", "source": "executor_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
            ]
        }

        variables_schema = [
            {
                "name": "task",
                "type": "string",
                "label": "Research Topic",
                "description": "The topic to research",
                "required": True
            }
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="multi-agent-research-assistant",
            defaults={
                "category": category,
                "name": "Multi-Agent Research Assistant",
                "description": "Deploy a team of AI agents: planner decomposes tasks, executor runs them, memory tracks progress",
                "difficulty": "advanced",
                "tags": ["agent", "research", "automation", "multi-agent"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "20 min",
                "required_apis": ["openai"],
                "use_count": 0,
                "rating": 4.7,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")

    def _create_utility_templates(self, categories):
        """Template 5: Data ETL Pipeline."""
        category = categories["utility"]

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "Data Source",
                        "inputs": {"source_url": {"type": "string", "label": "Source URL"}}
                    }
                },
                {
                    "id": "scraper_1",
                    "type": "web_scraper",
                    "position": {"x": 300, "y": 200},
                    "data": {
                        "name": "web_scraper",
                        "label": "Web Scraper",
                        "inputs": {
                            "url": {"type": "expression", "value": "{{ trigger_1.source_url }}"},
                            "selectors": {"type": "array", "value": [{"name": "items", "selector": "table tr"}]}
                        }
                    }
                },
                {
                    "id": "csv_transform_1",
                    "type": "csv_transform",
                    "position": {"x": 500, "y": 200},
                    "data": {
                        "name": "csv_transform",
                        "label": "CSV Transform",
                        "operation": "filter",
                        "inputs": {
                            "column": {"type": "string", "value": "status"},
                            "value": {"type": "string", "value": "active"},
                            "operator": {"type": "string", "value": "=="}
                        }
                    }
                },
                {
                    "id": "json_transform_1",
                    "type": "json_transform",
                    "position": {"x": 700, "y": 200},
                    "data": {
                        "name": "json_transform",
                        "label": "JSON Transform",
                        "operation": "map",
                        "inputs": {
                            "schema": {"type": "object", "value": {
                                "mappings": {"id": "id", "name": "title", "value": "count"}
                            }}
                        }
                    }
                },
                {
                    "id": "file_writer_1",
                    "type": "file_writer",
                    "position": {"x": 900, "y": 200},
                    "data": {
                        "name": "file_writer",
                        "label": "Save Data",
                        "inputs": {
                            "path": {"type": "string", "value": "/output/data.json"},
                            "content": {"type": "expression", "value": "{{ json_transform_1.output }}"}
                        }
                    }
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 1100, "y": 200},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "records": {"type": "expression", "value": "{{ file_writer_1.output }}"}
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "scraper_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "scraper_1", "target": "csv_transform_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e3", "source": "csv_transform_1", "target": "json_transform_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e4", "source": "json_transform_1", "target": "file_writer_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e5", "source": "file_writer_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
            ]
        }

        variables_schema = [
            {
                "name": "source_url",
                "type": "string",
                "label": "Source URL",
                "description": "URL of the web page to scrape data from",
                "required": True
            }
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="data-etl-pipeline",
            defaults={
                "category": category,
                "name": "Data ETL Pipeline",
                "description": "Extract data from web sources, transform with CSV/JSON operations, and load into files",
                "difficulty": "beginner",
                "tags": ["ETL", "data", "automation", "web scraping"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "5 min",
                "required_apis": [],
                "use_count": 0,
                "rating": 4.5,
                "rating_count": 0,
                "is_featured": False,
                "is_verified": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")

    def _create_hybrid_templates(self, categories):
        """Template 6: Multimodal Content Studio."""
        category = categories["multimodal"]

        workflow_data = {
            "nodes": [
                {
                    "id": "trigger_1",
                    "type": "trigger",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "name": "trigger",
                        "label": "Content Topic",
                        "inputs": {"topic": {"type": "string", "label": "Topic"}}
                    }
                },
                {
                    "id": "agent_1",
                    "type": "agent",
                    "position": {"x": 300, "y": 200},
                    "data": {
                        "name": "content_agent",
                        "label": "Content Strategist",
                        "model": "gpt-4o",
                        "inputs": {
                            "maxIterations": {"type": "number", "value": 3},
                            "systemPrompt": {"type": "string", "value": "You are a content strategist. Generate image descriptions and narration scripts."}
                        }
                    }
                },
                {
                    "id": "image_gen_1",
                    "type": "image_generation",
                    "position": {"x": 500, "y": 150},
                    "data": {
                        "name": "image_generation",
                        "label": "Image Generation",
                        "provider": "openai",
                        "model": "dall-e-3",
                        "inputs": {
                            "prompt": {"type": "expression", "value": "{{ agent_1.output.scenes[0] }}"}
                        }
                    }
                },
                {
                    "id": "image_edit_1",
                    "type": "image_editing",
                    "position": {"x": 700, "y": 150},
                    "data": {
                        "name": "image_editing",
                        "label": "Brand Watermark",
                        "provider": "openai",
                        "inputs": {
                            "image": {"type": "expression", "value": "{{ image_gen_1.output.images[0].url }}"},
                            "instruction": {"type": "string", "value": "Add brand watermark in corner"}
                        }
                    }
                },
                {
                    "id": "audio_gen_1",
                    "type": "audio_generation",
                    "position": {"x": 500, "y": 300},
                    "data": {
                        "name": "audio_generation",
                        "label": "Voiceover",
                        "provider": "elevenlabs",
                        "inputs": {
                            "text": {"type": "expression", "value": "{{ agent_1.output.narration }}"},
                            "voice": {"type": "string", "value": "alloy"},
                            "speed": {"type": "number", "value": 1.0}
                        }
                    }
                },
                {
                    "id": "file_writer_1",
                    "type": "file_writer",
                    "position": {"x": 900, "y": 100},
                    "data": {
                        "name": "file_writer",
                        "label": "Save Image",
                        "inputs": {
                            "path": {"type": "expression", "value": "/output/content/{{ trigger_1.id }}/image.png"},
                            "content": {"type": "expression", "value": "{{ image_edit_1.output }}"}
                        }
                    }
                },
                {
                    "id": "file_writer_2",
                    "type": "file_writer",
                    "position": {"x": 900, "y": 300},
                    "data": {
                        "name": "file_writer",
                        "label": "Save Audio",
                        "inputs": {
                            "path": {"type": "expression", "value": "/output/content/{{ trigger_1.id }}/voiceover.mp3"},
                            "content": {"type": "expression", "value": "{{ audio_gen_1.output }}"}
                        }
                    }
                },
                {
                    "id": "output_1",
                    "type": "output",
                    "position": {"x": 1100, "y": 200},
                    "data": {
                        "name": "output",
                        "label": "Output",
                        "message": {"type": "string", "value": "Content created: image and voiceover ready"}
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "trigger_1", "target": "agent_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e2", "source": "agent_1", "target": "image_gen_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e3", "source": "agent_1", "target": "audio_gen_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e4", "source": "image_gen_1", "target": "image_edit_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e5", "source": "image_edit_1", "target": "file_writer_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e6", "source": "audio_gen_1", "target": "file_writer_2", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e7", "source": "file_writer_1", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
                {"id": "e8", "source": "file_writer_2", "target": "output_1", "sourceHandle": "output", "targetHandle": "input"},
            ]
        }

        variables_schema = [
            {
                "name": "topic",
                "type": "string",
                "label": "Content Topic",
                "description": "The topic for content generation",
                "required": True
            }
        ]

        template, created = WorkflowTemplate.objects.get_or_create(
            slug="multimodal-content-studio",
            defaults={
                "category": category,
                "name": "Multimodal Content Studio",
                "description": "Create rich content: generate images, add voiceover narration, and export as branded multimedia",
                "difficulty": "intermediate",
                "tags": ["multimedia", "content creation", "branding", "automation"],
                "workflow_data": workflow_data,
                "variables_schema": variables_schema,
                "estimated_duration": "12 min",
                "required_apis": ["openai", "elevenlabs"],
                "use_count": 0,
                "rating": 4.4,
                "rating_count": 0,
                "is_featured": True,
                "is_verified": True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created template: {template.name}"))
        else:
            self.stdout.write(f"Template already exists: {template.name}")
