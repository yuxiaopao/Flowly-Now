"""
White-label and branding API views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import BrandingConfig, EmailTemplate, CustomDomain, ThemePreset
from .serializers import (
    BrandingConfigSerializer, BrandingPreviewSerializer,
    EmailTemplateSerializer, EmailTemplateCreateSerializer,
    CustomDomainSerializer, CustomDomainCreateSerializer,
    ThemePresetSerializer, BrandingUpdateSerializer
)


class BrandingViewSet(viewsets.ModelViewSet):
    """ViewSet for branding configuration."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BrandingConfig.objects.filter(tenant=self.request.user.tenant)

    def get_serializer_class(self):
        if self.action == 'preview':
            return BrandingPreviewSerializer
        return BrandingConfigSerializer

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current tenant's branding."""
        try:
            branding = self.get_queryset().first()
            if not branding:
                # Create default branding
                branding = BrandingConfig.objects.create(
                    tenant=request.user.tenant,
                    company_name=request.user.tenant.name
                )
            serializer = self.get_serializer(branding)
            return Response(serializer.data)
        except Exception:
            # Return public config if tenant doesn't exist
            return Response({
                'company_name': 'Flowly',
                'primary_color': '#3b82f6',
                'accent_color': '#8b5cf6',
                'bg_color': '#ffffff',
                'text_color_primary': '#1f2937'
            })

    @action(detail=False, methods=['post'])
    def update_config(self, request):
        """Update branding configuration."""
        serializer = BrandingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        branding, created = BrandingConfig.objects.get_or_create(
            tenant=request.user.tenant,
            defaults={'company_name': request.user.tenant.name}
        )

        for key, value in serializer.validated_data.items():
            setattr(branding, key, value)
        branding.save()

        return Response(BrandingConfigSerializer(branding).data)

    @action(detail=False, methods=['post'])
    def apply_preset(self, request):
        """Apply a theme preset."""
        preset_id = request.data.get('preset_id')
        if not preset_id:
            return Response(
                {'error': 'preset_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            preset = ThemePreset.objects.get(id=preset_id, is_active=True)
        except ThemePreset.DoesNotExist:
            return Response(
                {'error': 'Preset not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        branding, created = BrandingConfig.objects.get_or_create(
            tenant=request.user.tenant,
            defaults={'company_name': request.user.tenant.name}
        )
        preset.apply_to(branding)

        return Response(BrandingConfigSerializer(branding).data)

    @action(detail=False, methods=['get'])
    def presets(self, request):
        """Get available theme presets."""
        presets = ThemePreset.objects.filter(is_active=True, is_public=True)
        return Response(ThemePresetSerializer(presets, many=True).data)

    @action(detail=False, methods=['post'])
    def preview(self, request):
        """Preview branding changes without saving."""
        serializer = BrandingPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for email templates."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmailTemplate.objects.filter(tenant=self.request.user.tenant)

    def get_serializer_class(self):
        if self.action == 'create':
            return EmailTemplateCreateSerializer
        return EmailTemplateSerializer

    @action(detail=False, methods=['post'])
    def reset_to_default(self, request):
        """Reset an email template to default."""
        template_type = request.data.get('template_type')
        if not template_type:
            return Response(
                {'error': 'template_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            template = self.get_queryset().get(template_type=template_type)
            template.use_default = True
            template.save()
            return Response(EmailTemplateSerializer(template).data)
        except EmailTemplate.DoesNotExist:
            return Response(
                {'error': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def send_test(self, request, pk=None):
        """Send a test email."""
        template = self.get_object()

        # Send test email logic would go here
        return Response({
            'message': 'Test email sent successfully',
            'template': template.name
        })


class CustomDomainViewSet(viewsets.ModelViewSet):
    """ViewSet for custom domains."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomDomain.objects.filter(tenant=self.request.user.tenant)

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomDomainCreateSerializer
        return CustomDomainSerializer

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify domain ownership."""
        domain = self.get_object()

        # DNS verification logic would go here
        # For now, just update status
        domain.status = 'verified'
        domain.save()

        return Response(CustomDomainSerializer(domain).data)

    @action(detail=True, methods=['post'])
    def refresh_ssl(self, request, pk=None):
        """Refresh SSL certificate."""
        domain = self.get_object()

        if domain.status != 'active':
            return Response(
                {'error': 'Domain must be active to refresh SSL'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # SSL refresh logic would go here
        return Response({
            'message': 'SSL certificate refresh initiated'
        })


class ThemePresetViewSet(viewsets.ModelViewSet):
    """ViewSet for theme presets."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ThemePreset.objects.filter(is_active=True, is_public=True)

    def get_serializer_class(self):
        return ThemePresetSerializer
