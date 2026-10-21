"""
Billing API views.
"""

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum
from workflows.models import Workflow, WorkflowExecution
from agents.models import Agent
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import (
    PriceTier, Subscription, UsageRecord, Invoice,
    Payment, Coupon, CouponUsage, SubscriptionStatus, PlanType
)
from .serializers import (
    PriceTierSerializer, SubscriptionSerializer, UsageRecordSerializer,
    InvoiceSerializer, PaymentSerializer, CouponSerializer, SubscriptionCreateSerializer,
    CouponValidateSerializer, UsageSummarySerializer
)


class PriceTierViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for price tiers."""

    queryset = PriceTier.objects.filter(is_active=True).order_by('plan_type', 'billing_cycle', 'id')
    serializer_class = PriceTierSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def plans(self, request):
        """Get all available plans grouped by type."""
        tiers = self.get_queryset()
        plans = {}

        for tier in tiers:
            plan_type = tier.plan_type
            if plan_type not in plans:
                plans[plan_type] = {
                    'name': tier.get_plan_type_display(),
                    'tiers': []
                }
            plans[plan_type]['tiers'].append(PriceTierSerializer(tier).data)

        return Response(plans)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for subscriptions."""

    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get current user's subscription."""
        subscription = self.get_queryset().first()

        if not subscription:
            # Return default free subscription
            subscription = Subscription.objects.create(
                user=request.user,
                plan_type=PlanType.FREE,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timedelta(days=365)
            )

        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """Create or update subscription."""
        serializer = SubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_type = serializer.validated_data.get('plan_type', PlanType.FREE)
        billing_cycle = serializer.validated_data.get('billing_cycle', 'monthly')

        subscription, created = Subscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan_type': plan_type,
                'billing_cycle': billing_cycle,
                'status': SubscriptionStatus.ACTIVE,
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + (
                    timedelta(days=30) if billing_cycle == 'monthly' else timedelta(days=365)
                )
            }
        )

        return Response(
            SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def create(self, request, *args, **kwargs):
        return self.subscribe(request)

    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """Cancel subscription."""
        subscription = self.get_queryset().first()

        if not subscription:
            return Response(
                {'error': 'No subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )

        subscription.cancel_at_period_end = True
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = timezone.now()
        subscription.save()

        return Response({'status': 'Subscription will be canceled at period end'})

    @action(detail=False, methods=['post'])
    def reactivate(self, request):
        """Reactivate canceled subscription."""
        subscription = self.get_queryset().first()

        if not subscription:
            return Response(
                {'error': 'No subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )

        subscription.cancel_at_period_end = False
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.canceled_at = None
        subscription.save()

        return Response({'status': 'Subscription reactivated'})

    @action(detail=False, methods=['get'])
    def usage(self, request):
        """Get current usage summary."""
        subscription = self.get_queryset().first()

        if not subscription:
            subscription = Subscription.objects.create(
                user=request.user,
                plan_type=PlanType.FREE,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=timezone.now(),
                current_period_end=timezone.now() + timedelta(days=365),
            )

        limits = subscription.get_usage_limits() or {}

        # Get current period usage
        period_start = subscription.current_period_start or timezone.now().replace(day=1, hour=0, minute=0, second=0)
        period_end = subscription.current_period_end or timezone.now()

        usage = UsageRecord.objects.filter(
            user=request.user,
            period_start__gte=period_start,
            period_end__lte=period_end
        ).aggregate(
            workflow_count=Sum('workflow_count'),
            execution_count=Sum('execution_count'),
            api_call_count=Sum('api_call_count'),
            storage_used_mb=Sum('storage_used_mb'),
            agent_count=Sum('agent_count'),
            input_tokens=Sum('input_tokens'),
            output_tokens=Sum('output_tokens'),
            total_cost=Sum('total_cost')
        )

        live_workflow_count = Workflow.objects.filter(owner=request.user).count()
        live_agent_count = Agent.objects.filter(owner=request.user).count()
        live_execution_count = WorkflowExecution.objects.filter(
            workflow__owner=request.user,
            queued_at__gte=period_start,
            queued_at__lte=period_end,
        ).count()

        workflow_count = max(usage['workflow_count'] or 0, live_workflow_count)
        execution_count = max(usage['execution_count'] or 0, live_execution_count)
        agent_count = max(usage['agent_count'] or 0, live_agent_count)

        usage_record = UsageRecord(
            period_start=period_start,
            period_end=period_end,
            workflow_count=workflow_count,
            execution_count=execution_count,
            api_call_count=usage['api_call_count'] or 0,
            storage_used_mb=usage['storage_used_mb'] or 0,
            agent_count=agent_count,
            input_tokens=usage['input_tokens'] or 0,
            output_tokens=usage['output_tokens'] or 0,
            total_cost=usage['total_cost'] or 0
        )

        max_workflows = limits.get('max_workflows') or 100
        max_executions = limits.get('max_executions_per_month') or 1000
        max_storage_gb = limits.get('max_storage_gb') or 5
        max_agents = limits.get('max_agents') or 5
        max_api_calls = limits.get('max_api_calls_per_month') or 10000

        storage_mb = float(usage_record.storage_used_mb or 0)

        # Calculate percentages
        usage_percentages = {
            'workflows': min(100, (usage_record.workflow_count / max_workflows) * 100) if max_workflows else 0,
            'executions': min(100, (usage_record.execution_count / max_executions) * 100) if max_executions else 0,
            'storage': min(100, (storage_mb / (max_storage_gb * 1024)) * 100) if max_storage_gb else 0,
            'agents': min(100, (usage_record.agent_count / max_agents) * 100) if max_agents else 0,
            'api_calls': min(100, (usage_record.api_call_count / max_api_calls) * 100) if max_api_calls else 0,
        }

        remaining = {
            'workflows': max(0, max_workflows - usage_record.workflow_count),
            'executions': max(0, max_executions - usage_record.execution_count),
            'storage_gb': max(0, max_storage_gb - storage_mb / 1024),
            'agents': max(0, max_agents - usage_record.agent_count),
            'api_calls': max(0, max_api_calls - usage_record.api_call_count),
        }

        return Response({
            'current_usage': UsageRecordSerializer(usage_record).data,
            'limits': limits,
            'usage_percentages': usage_percentages,
            'remaining': remaining
        })


class UsageRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for usage records."""

    serializer_class = UsageRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UsageRecord.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get usage history."""
        months = int(request.query_params.get('months', 6))
        start_date = timezone.now() - timedelta(days=months * 30)

        records = self.get_queryset().filter(
            period_start__gte=start_date
        ).order_by('-period_start')

        return Response(UsageRecordSerializer(records, many=True).data)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for invoices."""

    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download invoice PDF."""
        invoice = self.get_object()
        # In production, this would generate and return a PDF
        return Response({
            'message': 'Invoice download not implemented',
            'invoice_number': invoice.invoice_number
        })


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for payments."""

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


class CouponViewSet(viewsets.ViewSet):
    """ViewSet for coupons."""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate a coupon code."""
        code = request.data.get('code')

        if not code:
            return Response(
                {'error': 'Coupon code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            coupon = Coupon.objects.get(code=code.upper())
        except Coupon.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Invalid coupon code'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not coupon.is_valid(request.user):
            return Response(
                {'valid': False, 'error': 'Coupon is no longer valid'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            'valid': True,
            'coupon': CouponSerializer(coupon, context={'request': request}).data
        })

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get user's coupons."""
        usages = CouponUsage.objects.filter(user=request.user).select_related('coupon')
        coupons = [usage.coupon for usage in usages]
        return Response(CouponSerializer(coupons, many=True, context={'request': request}).data)
