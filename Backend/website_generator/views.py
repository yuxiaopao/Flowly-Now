"""
Views for website generator app.
"""

import os
import logging
import zipfile
import io
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import GeneratedSite
from .serializers import (
    GeneratedSiteSerializer, GeneratedSiteCreateSerializer, GeneratedSiteUpdateSerializer
)
from .generators.classification import ClassificationGenerator
from .generators.regression import RegressionGenerator
from .generators.detection import DetectionGenerator
from .generators.nlp import NLPGGenerator

logger = logging.getLogger(__name__)


class GeneratedSiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for GeneratedSite management.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedSite.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return GeneratedSiteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GeneratedSiteUpdateSerializer
        return GeneratedSiteSerializer

    def _get_tenant(self, request):
        if hasattr(request.user, 'current_tenant'):
            return request.user.current_tenant
        return None

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Start website generation.
        
        Creates a GeneratedSite record and runs the generator in a background thread.
        """
        serializer = GeneratedSiteCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        site = serializer.save(
            status='generating',
            created_by=request.user,
            tenant=self._get_tenant(request)
        )

        def run_generation():
            try:
                generator_map = {
                    'classification': ClassificationGenerator,
                    'regression': RegressionGenerator,
                    'detection': DetectionGenerator,
                    'nlp_classification': NLPGGenerator,
                }
                generator_cls = generator_map.get(site.website_type, ClassificationGenerator)
                generator = generator_cls({
                    'output_dir': site.output_dir,
                    'model_path': site.model_path,
                    'model_type': site.model_type,
                    'labels': site.labels,
                    'framework': site.framework,
                    'website_type': site.website_type,
                    'frontend_framework': site.frontend_framework,
                    'backend_framework': site.backend_framework,
                    'port': site.port,
                    'name': site.name,
                    'description': site.description,
                })

                result = generator.generate()

                site.generated_files = result.get('generated_files', [])
                site.status = 'completed'
                site.inference_endpoint = f"http://localhost:{site.port}/predict"
                site.completed_at = timezone.now()
                site.save()

            except Exception as e:
                logger.exception(f"Website generation failed for site {site.id}")
                site.status = 'failed'
                site.error_message = str(e)
                site.completed_at = timezone.now()
                site.save()

        import threading
        t = threading.Thread(target=run_generation)
        t.start()

        return Response(GeneratedSiteSerializer(site).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download generated website as a ZIP file."""
        site = self.get_object()

        if site.status != 'completed':
            return Response({'error': 'Site not yet generated'}, status=status.HTTP_400_BAD_REQUEST)

        if not os.path.exists(site.output_dir):
            return Response({'error': 'Output directory not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(site.output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, site.output_dir)
                        zipf.write(file_path, arcname)

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{site.name.replace(" ", "_")}.zip"'
            return response

        except Exception as e:
            logger.error(f"Failed to create ZIP for site {pk}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """Deploy the generated website locally."""
        site = self.get_object()

        if site.status != 'completed':
            return Response({'error': 'Site not yet generated'}, status=status.HTTP_400_BAD_REQUEST)

        import subprocess
        import threading

        def run_deploy():
            try:
                backend_dir = os.path.join(site.output_dir, 'backend')
                if os.path.exists(os.path.join(backend_dir, 'app.py')):
                    subprocess.Popen(
                        ['python', 'app.py'],
                        cwd=backend_dir,
                        env={**os.environ, 'MODEL_PATH': site.model_path}
                    )
            except Exception as e:
                logger.error(f"Deploy failed for site {pk}: {str(e)}")

        t = threading.Thread(target=run_deploy)
        t.start()

        return Response({
            'message': 'Deployment started',
            'endpoint': site.inference_endpoint,
        })
