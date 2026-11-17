"""Exercise real PDF and image parsers across dependency upgrades."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from rag.models import DocumentCollection, VectorStore
from users.constants import AVATAR_SIZE

pytestmark = pytest.mark.django_db


def pdf_bytes(*, encrypted=False, blank=False):
    writer = PdfWriter()
    for text in ('FlowlyParserFirstPage', 'FlowlyParserSecondPage'):
        page = writer.add_blank_page(width=300, height=200)
        if not blank:
            font = DictionaryObject({
                NameObject('/Type'): NameObject('/Font'),
                NameObject('/Subtype'): NameObject('/Type1'),
                NameObject('/BaseFont'): NameObject('/Helvetica'),
            })
            page[NameObject('/Resources')] = DictionaryObject({
                NameObject('/Font'): DictionaryObject({NameObject('/F1'): font}),
            })
            stream = DecodedStreamObject()
            stream.set_data(f'BT /F1 12 Tf 20 100 Td ({text}) Tj ET'.encode('ascii'))
            page[NameObject('/Contents')] = stream
    if encrypted:
        writer.encrypt('test-document-password')
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture
def parser_collection(user):
    store = VectorStore.objects.create(name='Parser regression', store_type='memory', owner=user)
    return DocumentCollection.objects.create(name='Parser regression', vector_store=store, owner=user)


def test_pdf_upload_extracts_and_indexes_real_text(authenticated_client, parser_collection):
    uploaded = SimpleUploadedFile('two-pages.pdf', pdf_bytes(), content_type='application/pdf')
    response = authenticated_client.post(
        f'/api/v1/rag/collections/{parser_collection.pk}/upload_file/',
        {'file': uploaded}, format='multipart',
    )
    assert response.status_code == 201, response.data
    document = parser_collection.documents.get()
    assert document.content == 'FlowlyParserFirstPage\n\nFlowlyParserSecondPage'
    assert document.status == 'completed'
    results = authenticated_client.get(
        f'/api/v1/rag/collections/{parser_collection.pk}/search/',
        {'query': 'FlowlyParserSecondPage'},
    )
    assert results.status_code == 200
    assert results.data['results'][0]['metadata']['doc_id'] == str(document.pk)


@pytest.mark.parametrize('document_kind', ['encrypted', 'blank', 'corrupted'])
def test_invalid_pdf_upload_does_not_create_a_document(authenticated_client, parser_collection, document_kind):
    content = b'%PDF-1.7\ninvalid body' if document_kind == 'corrupted' else pdf_bytes(
        encrypted=document_kind == 'encrypted', blank=document_kind == 'blank',
    )
    response = authenticated_client.post(
        f'/api/v1/rag/collections/{parser_collection.pk}/upload_file/',
        {'file': SimpleUploadedFile('invalid.pdf', content, content_type='application/pdf')},
        format='multipart',
    )
    assert response.status_code == 400, response.data
    assert parser_collection.documents.count() == 0
    assert parser_collection.chunk_count == 0


def test_jpeg_avatar_applies_orientation_and_strips_metadata(authenticated_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    source = Image.new('RGB', (320, 160), 'blue')
    exif = Image.Exif()
    exif[274] = 6  # Rotate 90 degrees clockwise when displayed.
    exif[270] = 'private fixture metadata'
    output = BytesIO()
    source.save(output, format='JPEG', exif=exif)
    response = authenticated_client.post(
        '/api/v1/auth/user/avatar/',
        {'avatar': SimpleUploadedFile('oriented.jpg', output.getvalue(), content_type='image/jpeg')},
        format='multipart',
    )
    assert response.status_code == 200, response.data
    files = list(tmp_path.rglob('*.png'))
    assert len(files) == 1
    with Image.open(files[0]) as stored:
        stored.load()
        assert stored.format == 'PNG'
        assert stored.height == AVATAR_SIZE[1]
        assert stored.width == stored.height // 2
        assert not stored.getexif()
        assert 'private fixture metadata' not in str(stored.info)


def test_truncated_png_avatar_preserves_existing_image(authenticated_client, user, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user.avatar = 'https://example.test/existing.png'
    user.save(update_fields=['avatar'])
    output = BytesIO()
    Image.new('RGB', (32, 32), 'blue').save(output, format='PNG')
    response = authenticated_client.post(
        '/api/v1/auth/user/avatar/',
        {'avatar': SimpleUploadedFile('truncated.png', output.getvalue()[:40], content_type='image/png')},
        format='multipart',
    )
    assert response.status_code == 400, response.data
    user.refresh_from_db()
    assert user.avatar == 'https://example.test/existing.png'
    assert not list(tmp_path.rglob('*'))
