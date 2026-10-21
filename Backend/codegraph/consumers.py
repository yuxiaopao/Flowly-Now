"""
WebSocket consumers for codegraph app.
"""

import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class CodeGraphConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer for real-time code graph updates.
    
    连接方式: ws://host/api/v1/codegraph/ws/<project_id>/
    
    消息格式:
    - 客户端发送:
        - {"type": "subscribe"} - 订阅项目更新
        - {"type": "unsubscribe"} - 取消订阅
        - {"type": "ping"} - 心跳检测
    
    - 服务器发送:
        - {"type": "graph_update", "event": "modified", "file": "path", "timestamp": "..."}
        - {"type": "full_refresh", "project_id": 1}
        - {"type": "error", "message": "..."}
        - {"type": "pong"} - 心跳响应
    """
    
    async def connect(self):
        """处理 WebSocket 连接"""
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'codegraph_{self.project_id}'
        self.user = self.scope.get('user')
        self.refresh_task = None
        
        # 检查权限
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # 加入频道组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 发送连接成功消息
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'project_id': self.project_id,
            'message': f'Connected to codegraph project {self.project_id}',
        }))
        
        logger.info(f"WebSocket connected: project_id={self.project_id}, user={self.user}")
    
    async def disconnect(self, close_code):
        """处理 WebSocket 断开"""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
        # 离开频道组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket disconnected: project_id={self.project_id}")
    
    async def receive(self, text_data):
        """处理接收到的消息"""
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                }))
            
            elif msg_type == 'subscribe':
                await self.send(text_data=json.dumps({
                    'type': 'subscribed',
                    'project_id': self.project_id,
                }))
            
            elif msg_type == 'unsubscribe':
                await self.send(text_data=json.dumps({
                    'type': 'unsubscribed',
                    'project_id': self.project_id,
                }))
            
            elif msg_type == 'request_refresh':
                # 触发后端重新分析
                await self.trigger_refresh()
            
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {msg_type}',
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format',
            }))
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e),
            }))
    
    async def trigger_refresh(self):
        """触发后端重新分析"""
        from .views import get_project_config
        
        config = get_project_config(int(self.project_id))
        if not config:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Project not found',
            }))
            return
        
        # 在后台任务中执行（避免阻塞 WebSocket）
        if not self.refresh_task or self.refresh_task.done():
            self.refresh_task = asyncio.create_task(self._refresh_analysis(config))
    
    async def _refresh_analysis(self, config: dict):
        """执行刷新分析"""
        from datetime import datetime

        def build_analysis():
            from .views import _code_parser, _project_cache
            from .services.analyzer import GraphAnalyzer

            project_id = int(self.project_id)
            _project_cache.invalidate(project_id)
            structure = _code_parser.build_structure(config.get('path', ''))
            analysis = GraphAnalyzer().analyze(structure, project_id, config.get('name', ''))
            _project_cache.set_structure(project_id, structure)
            _project_cache.set_analysis(project_id, analysis)
            return analysis
        
        try:
            analysis = await asyncio.to_thread(build_analysis)
            
            # 广播更新
            await self.channel_layer.group_send(
                f'codegraph_{self.project_id}',
                {
                    'type': 'graph_update',
                    'event': 'full_refresh',
                    'data': {
                        'project_id': self.project_id,
                        'stats': analysis.stats,
                        'last_updated': analysis.last_updated,
                    },
                    'timestamp': datetime.now().isoformat(),
                }
            )
            
            logger.info(f"Refresh completed for project {self.project_id}")
        
        except Exception as e:
            logger.error(f"Refresh failed for project {self.project_id}: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Refresh failed: {str(e)}',
            }))
    
    async def graph_update(self, event):
        """
        处理 graph_update 消息
        由 channel_layer.group_send 触发
        """
        await self.send(text_data=json.dumps({
            'type': 'graph_update',
            'event': event.get('event'),
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp'),
        }))
    
    async def full_refresh(self, event):
        """处理全量刷新消息"""
        await self.send(text_data=json.dumps({
            'type': 'full_refresh',
            'data': event.get('data', {}),
            'timestamp': event.get('timestamp'),
        }))


class FileWatchConsumer(AsyncWebsocketConsumer):
    """
    WebSocket Consumer for file system watching.
    当检测到文件变化时推送通知。
    """
    
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'codegraph_files_{self.project_id}'
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'project_id': self.project_id,
            'mode': 'file_watch',
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
            
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown type: {msg_type}',
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON',
            }))
    
    async def file_modified(self, event):
        """处理文件修改通知"""
        await self.send(text_data=json.dumps({
            'type': 'file_modified',
            'file': event.get('file'),
            'event_type': event.get('event_type'),
            'timestamp': event.get('timestamp'),
        }))
    
    async def file_created(self, event):
        """处理文件创建通知"""
        await self.send(text_data=json.dumps({
            'type': 'file_created',
            'file': event.get('file'),
            'timestamp': event.get('timestamp'),
        }))
    
    async def file_deleted(self, event):
        """处理文件删除通知"""
        await self.send(text_data=json.dumps({
            'type': 'file_deleted',
            'file': event.get('file'),
            'timestamp': event.get('timestamp'),
        }))
