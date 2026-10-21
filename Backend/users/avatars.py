"""Validate and store account avatars without trusting file extensions."""

import logging
import re
import warnings
from io import BytesIO
from urllib.parse import unquote, urlparse
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import (
    AVATAR_FORMATS, AVATAR_MAX_BYTES, AVATAR_MAX_PIXELS,
    AVATAR_MESSAGES, AVATAR_SIZE, AVATAR_STORAGE_DIRECTORY,
)
from .models import User

logger = logging.getLogger(__name__)


class AvatarSerializer(serializers.Serializer):
    avatar = serializers.FileField()

    def validate_avatar(self, file):
        if file.size > AVATAR_MAX_BYTES:
            raise serializers.ValidationError(AVATAR_MESSAGES['size'])
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(file) as image:
                    if image.format not in AVATAR_FORMATS:
                        raise serializers.ValidationError(AVATAR_MESSAGES['format'])
                    if image.width * image.height > AVATAR_MAX_PIXELS:
                        raise serializers.ValidationError(AVATAR_MESSAGES['pixels'])
                    image.verify()
                file.seek(0)
                with Image.open(file) as image:
                    image = ImageOps.exif_transpose(image).convert('RGBA')
                    image.thumbnail(AVATAR_SIZE, Image.Resampling.LANCZOS)
                    image.info.clear()
                    output = BytesIO()
                    image.save(output, format='PNG')
            return ContentFile(output.getvalue())
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise serializers.ValidationError(AVATAR_MESSAGES['pixels'])
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
            raise serializers.ValidationError(AVATAR_MESSAGES['format'])


def delete_owned_avatar(url, user_id):
    """Delete only files created by this endpoint for the current account."""
    prefix = f'{AVATAR_STORAGE_DIRECTORY}/{user_id}/'
    url_prefix = unquote(urlparse(default_storage.url(prefix)).path)
    path = unquote(urlparse(url).path)
    if not path.startswith(url_prefix):
        return
    name = path[len(url_prefix):]
    if not re.fullmatch(r'[0-9a-f]{32}\.png', name):
        return
    try:
        default_storage.delete(f'{prefix}{name}')
    except OSError:
        logger.exception('Could not remove previous avatar for user %s', user_id)


class UserAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = AvatarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        path = default_storage.save(
            f'{AVATAR_STORAGE_DIRECTORY}/{request.user.pk}/{uuid4().hex}.png',
            serializer.validated_data['avatar'],
        )
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=request.user.pk)
                previous = user.avatar
                user.avatar = request.build_absolute_uri(default_storage.url(path))
                user.avatar_preferences = {**user.avatar_preferences, 'mode': 'image'}
                user.save(update_fields=['avatar', 'avatar_preferences', 'updated_at'])
                transaction.on_commit(lambda: delete_owned_avatar(previous, user.pk))
        except Exception:
            default_storage.delete(path)
            raise
        return Response({'avatar': user.avatar, 'avatar_preferences': user.avatar_preferences})

    def delete(self, request):
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            previous = user.avatar
            user.avatar = ''
            user.avatar_preferences = {**user.avatar_preferences, 'mode': 'robot'}
            user.save(update_fields=['avatar', 'avatar_preferences', 'updated_at'])
            transaction.on_commit(lambda: delete_owned_avatar(previous, user.pk))
        return Response({'avatar': '', 'avatar_preferences': user.avatar_preferences})
