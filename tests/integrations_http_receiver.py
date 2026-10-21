"""Loopback-only receiver for real HTTP browser tests; logs no authorization token."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_TOKEN = 'integrations-qa-token'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--output', type=Path, default=ROOT / '.cache' / 'integrations-received.jsonl')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, data):
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        def do_GET(self):
            if self.headers.get('Authorization') != f'Bearer {TEST_TOKEN}':
                self.reply(401, {'message': 'invalid token'})
                return
            data = {'id': 'qa-user'} if self.path == '/github/user' else [
                {'id': 'qa-repo', 'full_name': 'flowly/connector-verification'}]
            self.reply(200, data)

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            record = {'path': self.path, 'body': json.loads(body), 'signature': self.headers.get('X-Webhook-Signature')}
            with args.output.open('a', encoding='utf8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
            self.reply(403 if self.path == '/reject' else 200, {'accepted': self.path != '/reject'})

        def log_message(self, *args):
            return

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
