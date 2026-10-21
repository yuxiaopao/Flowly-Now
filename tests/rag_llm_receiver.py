"""Controlled OpenAI-compatible HTTP boundary for browser integration tests only."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        question = json.loads(payload['messages'][-1]['content'])['question']
        if '故障模拟' in question:
            self.send_response(503)
            self.end_headers()
            return
        data = {'id': 'controlled-rag-test', 'object': 'chat.completion', 'created': 0, 'model': payload['model'],
                'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': '先查看执行历史，再检查失败节点的错误日志。[1]'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 20, 'completion_tokens': 15, 'total_tokens': 35}}
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *args):
        return


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8767), Handler).serve_forever()
