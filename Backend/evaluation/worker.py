"""CPU child without database configuration, inherited credentials or sockets."""
import json
from pathlib import Path
import socket
import sys


def deny_network(*args, **kwargs):
    raise PermissionError('模型评测子进程禁止访问外部网络。')


class OfflineSocket(socket.socket):
    connect = deny_network
    connect_ex = deny_network
    sendto = deny_network
    bind = deny_network
    listen = deny_network


def main():
    socket.socket = OfflineSocket
    socket.create_connection = deny_network
    socket.getaddrinfo = deny_network
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
        from PIL import Image
        from evaluation.constants import MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        import torch
        torch.set_num_threads(1)
        from evaluation.evaluators import evaluate_request
        result = {'success': True, 'metrics': evaluate_request(request)}
    except Exception as exc:
        result = {'success': False, 'error': str(exc), 'error_type': type(exc).__name__}
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return 0 if result['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
