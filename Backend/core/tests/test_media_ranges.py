from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import RequestFactory, TestCase
from core.views.media_views import serve_media as serve


class MediaRangeTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data = bytes(range(256))
        (self.root / 'movie.mp4').write_bytes(self.data)
        self.factory = RequestFactory()

    def response(self, method='get', **headers):
        response = serve(getattr(self.factory, method)('/media/movie.mp4', **headers), 'movie.mp4', document_root=self.root)
        self.addCleanup(response.close)
        return response

    def body(self, response):
        return b''.join(response.streaming_content) if response.streaming else response.content

    def test_requested_bytes(self):
        response = self.response(HTTP_RANGE='bytes=100-200')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Range'], 'bytes 100-200/256')
        self.assertEqual(self.body(response), self.data[100:201])

    def test_open_and_suffix_ranges(self):
        self.assertEqual(self.body(self.response(HTTP_RANGE='bytes=250-')), self.data[250:])
        self.assertEqual(self.body(self.response(HTTP_RANGE='bytes=-10')), self.data[-10:])
        self.assertEqual(self.body(self.response(HTTP_RANGE='bytes=250-999')), self.data[250:])

    def test_invalid_ranges_and_empty_file(self):
        for value in ('bytes=256-', 'bytes=20-10', 'bytes=-0', 'bytes=-'):
            response = self.response(HTTP_RANGE=value)
            self.assertEqual(response.status_code, 416)
            self.assertEqual(response['Content-Range'], 'bytes */256')
        (self.root / 'movie.mp4').write_bytes(b'')
        self.assertEqual(self.response(HTTP_RANGE='bytes=0-').status_code, 416)

    def test_head_matches_range_without_body(self):
        response = self.response(method='head', HTTP_RANGE='bytes=10-19')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response['Content-Length'], '10')
        self.assertEqual(self.body(response), b'')

    def test_full_and_unsupported_multiple_ranges(self):
        for headers in ({}, {'HTTP_RANGE': 'bytes=0-2,4-6'}, {'HTTP_RANGE': 'invalid'}):
            response = self.response(**headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.body(response), self.data)
        head = self.response(method='head')
        self.assertEqual(head['Content-Length'], '256')
        self.assertEqual(self.body(head), b'')

    def test_if_range_preserves_resource_consistency(self):
        response = self.response(method='head')
        self.assertEqual(self.response(HTTP_RANGE='bytes=0-2', HTTP_IF_RANGE=response['ETag']).status_code, 206)
        self.assertEqual(self.response(HTTP_RANGE='bytes=0-2', HTTP_IF_RANGE=response['Last-Modified']).status_code, 206)
        self.assertEqual(self.response(HTTP_RANGE='bytes=0-2', HTTP_IF_RANGE='"stale"').status_code, 200)

    def test_path_traversal_and_missing_files(self):
        from django.http import Http404
        for path in ('../secret.mp4', 'missing.mp4'):
            with self.assertRaises(Http404):
                serve(self.factory.get('/media/' + path), path, document_root=self.root)

    def test_other_assets_keep_static_serving_and_post_is_rejected(self):
        (self.root / 'image.png').write_bytes(b'image')
        response = serve(self.factory.get('/media/image.png'), 'image.png', document_root=self.root)
        self.assertEqual(self.body(response), b'image')
        self.assertEqual(self.response(method='post').status_code, 405)
