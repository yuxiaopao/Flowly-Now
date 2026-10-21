"""
执行上下文 - 管理工作流执行过程中的变量和数据
"""

import re
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExecutionContext:
    """
    执行上下文
    
    管理工作流执行过程中的变量、输入输出和元数据。
    
    Attributes:
        input_data: 外部输入数据
        variables: 变量存储
        node_outputs: 节点输出缓存
        metadata: 元数据
        started_at: 执行开始时间
        ended_at: 执行结束时间
    """
    
    # 输入数据
    input_data: Dict[str, Any] = field(default_factory=dict)
    
    # 变量存储
    variables: Dict[str, Any] = field(default_factory=dict)
    
    # 节点输出缓存 (node_id -> output)
    node_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 执行时间
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化开始时间"""
        if self.started_at is None:
            self.started_at = datetime.now()
    
    def set_var(self, name: str, value: Any) -> None:
        """
        设置变量
        
        Args:
            name: 变量名
            value: 变量值
        """
        self.variables[name] = value
    
    def get_var(self, name: str, default: Any = None) -> Any:
        """
        获取变量
        
        优先级: variables -> input_data -> default
        
        Args:
            name: 变量名
            default: 默认值
            
        Returns:
            变量值或默认值
        """
        # 先从 variables 获取
        if name in self.variables:
            return self.variables[name]
        
        # 再从 input_data 获取
        if name in self.input_data:
            return self.input_data[name]
        
        # 从节点输出获取
        for output in self.node_outputs.values():
            if isinstance(output, dict) and name in output:
                return output[name]
        
        return default
    
    def has_var(self, name: str) -> bool:
        """
        检查变量是否存在
        
        Args:
            name: 变量名
            
        Returns:
            是否存在
        """
        return (
            name in self.variables or 
            name in self.input_data or
            any(
                isinstance(output, dict) and name in output
                for output in self.node_outputs.values()
            )
        )
    
    def set_node_output(self, node_id: str, output: Any) -> None:
        """
        设置节点输出
        
        Args:
            node_id: 节点 ID
            output: 节点输出
        """
        self.node_outputs[node_id] = output
        
        # 如果输出是字典，自动提取变量。
        # 注意：并行分镜会写出同名 image_prompt / images；全局 variables 仍 last-wins，
        # 真正的分支隔离由 WorkflowExecutor._build_node_execution_context 负责。
        # 这里仍写入，兼容线性链路；读取时以 _branch_upstream 覆盖为准。
        if isinstance(output, dict):
            for key, value in output.items():
                # 跳过内部键
                if not key.startswith('_'):
                    self.variables[key] = value
    
    def get_node_output(self, node_id: str, default: Any = None) -> Any:
        """
        获取节点输出
        
        Args:
            node_id: 节点 ID
            default: 默认值
            
        Returns:
            节点输出或默认值
        """
        return self.node_outputs.get(node_id, default)
    
    def interpolate(self, text: str) -> str:
        """
        变量插值
        
        支持 {{variable}} 语法，会从 variables、input_data 中查找变量。
        
        Args:
            text: 包含变量的文本
            
        Returns:
            插值后的文本
            
        Example:
            >>> ctx = ExecutionContext()
            >>> ctx.set_var('name', 'Alice')
            >>> ctx.interpolate('Hello {{name}}!')
            'Hello Alice!'
        """
        pattern = r'\{\{([^}]+)\}\}'
        
        def replacer(match):
            var_path = match.group(1).strip()
            
            # 支持点号访问，如 {{user.name}}
            if '.' in var_path:
                return self._get_nested_value(var_path)
            
            value = self.get_var(var_path)
            if value is None:
                return match.group(0)
            
            return str(value)
        
        return re.sub(pattern, replacer, text)
    
    def _get_nested_value(self, path: str) -> str:
        """
        获取嵌套值
        
        Args:
            path: 点号分隔的路径，如 "user.name"
            
        Returns:
            值或原始路径
        """
        keys = path.split('.')
        value = None
        
        # 尝试从 variables 获取
        value = self.variables
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return f'{{{{{".".join(keys)}}}}}'
        
        if value is not None:
            return str(value)
        
        return f'{{{{{".".join(keys)}}}}}'
    
    def interpolate_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归插值字典中的所有字符串
        
        Args:
            data: 需要插值的字典
            
        Returns:
            插值后的字典
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.interpolate(value)
            elif isinstance(value, dict):
                result[key] = self.interpolate_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.interpolate(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        设置元数据
        
        Args:
            key: 元数据键
            value: 元数据值
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据
        
        Args:
            key: 元数据键
            default: 默认值
            
        Returns:
            元数据值或默认值
        """
        return self.metadata.get(key, default)
    
    def mark_end(self) -> None:
        """标记执行结束"""
        self.ended_at = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """获取执行耗时（秒）"""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        
        Returns:
            包含所有数据的字典
        """
        return {
            'input_data': self.input_data,
            'variables': self.variables,
            'node_outputs': {
                k: v if not callable(v) else str(v)
                for k, v in self.node_outputs.items()
            },
            'metadata': self.metadata,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration': self.duration
        }
    
    def get_all_outputs(self) -> Dict[str, Any]:
        """
        获取所有输出（用于返回给调用方）
        
        Returns:
            合并后的输出字典
        """
        result = {}
        
        # 合并所有变量
        result.update(self.variables)
        
        # 合并输入数据
        for key, value in self.input_data.items():
            if key not in result:
                result[key] = value
        
        # 添加 last_output 引用
        if self.node_outputs:
            last_output = list(self.node_outputs.values())[-1]
            if isinstance(last_output, dict):
                result['last_output'] = last_output.get('text', last_output)
            else:
                result['last_output'] = last_output
        
        return result
    
    def clone(self) -> 'ExecutionContext':
        """
        创建上下文的深拷贝
        
        Returns:
            新的 ExecutionContext 实例
        """
        return ExecutionContext(
            input_data=self.input_data.copy(),
            variables=self.variables.copy(),
            node_outputs=self.node_outputs.copy(),
            metadata=self.metadata.copy()
        )
