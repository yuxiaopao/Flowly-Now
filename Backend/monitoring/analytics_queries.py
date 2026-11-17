"""One validated time window for every analytics series and detail table."""
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from .constants import DEFAULT_ANALYTICS_DAYS, MAX_ANALYTICS_DAYS, MAX_ANALYTICS_LIMIT


class AnalyticsWindow(serializers.Serializer):
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    days = serializers.IntegerField(min_value=1, max_value=MAX_ANALYTICS_DAYS, required=False)
    period = serializers.RegexField(r'^\d+d$', required=False)

    def validate(self, attrs):
        start, end = attrs.get('start_date'), attrs.get('end_date')
        if (start is None) != (end is None):
            raise serializers.ValidationError('请同时提供开始时间和结束时间。')
        if start is not None:
            if start >= end or end - start > timedelta(days=MAX_ANALYTICS_DAYS):
                raise serializers.ValidationError(f'开始时间须早于结束时间，范围最多 {MAX_ANALYTICS_DAYS} 天。')
        else:
            days = int(attrs['period'][:-1]) if 'period' in attrs else attrs.get('days', DEFAULT_ANALYTICS_DAYS)
            if not 1 <= days <= MAX_ANALYTICS_DAYS:
                raise serializers.ValidationError(f'统计范围须在 1 到 {MAX_ANALYTICS_DAYS} 天之间。')
            end = timezone.now()
            start = end - timedelta(days=days)
        return {'start': start, 'end': end}


def analytics_window(params):
    serializer = AnalyticsWindow(data={key: params[key] for key in ('start_date', 'end_date', 'days', 'period') if key in params})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data['start'], serializer.validated_data['end']


def analytics_limit(params, default):
    return serializers.IntegerField(min_value=1, max_value=MAX_ANALYTICS_LIMIT).run_validation(params.get('limit', default))
