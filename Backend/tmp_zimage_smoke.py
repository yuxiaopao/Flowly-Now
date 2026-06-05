import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from workflows.services.langchain_service import LangChainService

service = LangChainService()
result = service.run_image_generation_node(
    {
        'provider': 'zimage_local',
        'model': 'Tongyi-MAI/Z-Image-Turbo',
        'prompt': 'A cozy futuristic desk setup, soft cinematic lighting, compact composition, highly detailed',
        'size': '512x512',
        'n': 1,
        'enable_cpu_offload': True,
        'num_inference_steps': 9,
        'guidance_scale': 0.0,
        'seed': 42,
    },
    {}
)
print(result)
