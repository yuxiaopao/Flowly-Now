"""
System capability endpoints for client/server hardware-aware workflow generation.
"""

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.services.hardware_profile import get_system_capabilities


class SystemCapabilitiesView(APIView):
    """
    Return merged server + optional client hardware profile and training recommendations.

    POST body may include `client_capabilities` from the browser.
    GET returns server-side detection only.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'code': 200, 'message': 'success', 'data': get_system_capabilities()})

    def post(self, request):
        client = request.data.get('client_capabilities') or request.data.get('clientCapabilities')
        return Response({
            'code': 200,
            'message': 'success',
            'data': get_system_capabilities(client),
        })


class SystemCapabilitiesPublicPingView(APIView):
    """Lightweight ping for health; no auth required."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'ok': True, 'service': 'system-capabilities'})
