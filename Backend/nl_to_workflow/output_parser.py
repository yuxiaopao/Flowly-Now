"""
LangChain Output Parser for structured workflow generation.

This module provides Pydantic-based output parsing that eliminates
the need for manual regex-based JSON parsing.
"""

import copy
import json
import logging
from typing import Dict, Any, Optional, List, Generator, Union, Tuple
from django.conf import settings

from langchain_core.output_parsers import JsonOutputParser, PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .schemas import (
    WorkflowSchema,
    WorkflowModificationSchema,
    WorkflowNode,
    WorkflowEdge,
    ValidationResult,
)
from .constants import (
    SUPPORTED_NODE_TYPES,
    ERROR_MESSAGES,
    VALIDATION_MESSAGES,
)

logger = logging.getLogger(__name__)


class WorkflowOutputParser:
    """
    LangChain-based output parser for workflow generation.

    Uses Pydantic models for type-safe parsing with automatic validation.
    Falls back to regex parsing if structured parsing fails.
    """

    # Primary parser - Pydantic-based
    _workflow_parser: Optional[PydanticOutputParser] = None
    _modification_parser: Optional[PydanticOutputParser] = None

    @classmethod
    def get_workflow_parser(cls) -> PydanticOutputParser:
        """Get or create the workflow schema parser."""
        if cls._workflow_parser is None:
            cls._workflow_parser = PydanticOutputParser(
                pydantic_object=WorkflowSchema
            )
        return cls._workflow_parser

    @classmethod
    def get_modification_parser(cls) -> PydanticOutputParser:
        """Get or create the modification schema parser."""
        if cls._modification_parser is None:
            cls._modification_parser = PydanticOutputParser(
                pydantic_object=WorkflowModificationSchema
            )
        return cls._modification_parser

    @classmethod
    def get_format_instructions(cls) -> str:
        """Get the format instructions for the parser."""
        parser = cls.get_workflow_parser()
        return parser.get_format_instructions()

    @classmethod
    def parse_workflow(
        cls,
        response: str,
        normalize: bool = True
    ) -> Dict[str, Any]:
        """
        Parse LLM response into workflow structure.

        Args:
            response: Raw LLM response text
            normalize: Whether to normalize missing fields

        Returns:
            Dict with workflow structure or error
        """
        # Prefer coerce-first path: salvage nearly-valid JSON before Pydantic.
        coerced = cls._try_load_and_coerce(response)
        if coerced and not coerced.get('error'):
            try:
                parsed = WorkflowSchema.model_validate(coerced)
                workflow = parsed.model_dump()
                if normalize:
                    workflow = cls._normalize_workflow(workflow)
                return workflow
            except Exception as e:
                logger.warning(f"Coerced JSON failed schema validate: {e}")

        # Try structured parsing first
        try:
            parser = cls.get_workflow_parser()
            parsed = parser.parse(response)

            workflow = parsed.model_dump()

            if normalize:
                workflow = cls._normalize_workflow(workflow)

            return workflow

        except OutputParserException as e:
            logger.warning(f"Structured parsing failed, falling back to regex: {e}")
            return cls._fallback_regex_parse(response)

        except Exception as e:
            logger.exception(f"Unexpected parsing error: {e}")
            return cls._fallback_regex_parse(response)

    @classmethod
    def _try_load_and_coerce(cls, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from LLM text and fill safe defaults."""
        import re

        text = (response or '').strip()
        if not text:
            return None

        candidates = []
        code_block = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
        if code_block:
            candidates.append(code_block.group(1).strip())
        raw = re.search(r'\{[\s\S]*\}', text)
        if raw:
            candidates.append(raw.group(0))
        candidates.append(text)

        data = None
        for candidate in candidates:
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        if not isinstance(data, dict):
            return None

        nodes = data.get('nodes')
        if not isinstance(nodes, list) or not nodes:
            return None

        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node.setdefault('id', f'node_{i + 1}')
            ntype = str(node.get('type') or 'llm')
            node['type'] = ntype
            if not str(node.get('name') or '').strip():
                defaults = {
                    'start': '开始', 'end': '结束', 'input': '输入', 'output': '输出',
                }
                node['name'] = defaults.get(ntype, ntype)
            if not isinstance(node.get('position'), dict):
                node['position'] = {'x': 100 + i * 180, 'y': 150}
            else:
                node['position'].setdefault('x', 100 + i * 180)
                node['position'].setdefault('y', 150)
            node.setdefault('config', {})

        if not isinstance(data.get('edges'), list):
            data['edges'] = []
        if not data['edges'] and len(nodes) >= 2:
            data['edges'] = [
                {
                    'id': f'edge_{i + 1}',
                    'source': nodes[i]['id'],
                    'target': nodes[i + 1]['id'],
                    'label': '',
                }
                for i in range(len(nodes) - 1)
            ]

        data.setdefault('name', 'Generated Workflow')
        data.setdefault('description', '')
        return data

    @classmethod
    def _extract_node_config(cls, node: Dict[str, Any]) -> Dict[str, Any]:
        """Read config from flat or VueFlow `data.config` shapes."""
        if not isinstance(node, dict):
            return {}
        cfg = node.get('config')
        if isinstance(cfg, dict) and cfg:
            return dict(cfg)
        data = node.get('data')
        if isinstance(data, dict):
            nested = data.get('config')
            if isinstance(nested, dict):
                return dict(nested)
        return {}

    @classmethod
    def _extract_node_label(cls, node: Dict[str, Any], fallback: str = 'Node') -> str:
        if not isinstance(node, dict):
            return fallback
        if node.get('name'):
            return str(node['name'])
        data = node.get('data') if isinstance(node.get('data'), dict) else {}
        return str(data.get('label') or data.get('name') or fallback)

    @classmethod
    def _merge_nodes_by_id(
        cls,
        current_nodes: List[Dict[str, Any]],
        incoming_nodes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge LLM node patches onto current nodes by id.

        Critical: empty incoming config must NOT wipe existing `data.config`.
        """
        current_by_id = {
            str(n.get('id')): n for n in (current_nodes or []) if isinstance(n, dict) and n.get('id')
        }
        if not incoming_nodes:
            return list(current_nodes or [])

        merged: List[Dict[str, Any]] = []
        seen = set()
        for raw in incoming_nodes:
            if not isinstance(raw, dict):
                continue
            nid = str(raw.get('id') or '')
            base = copy.deepcopy(current_by_id.get(nid) or {})
            incoming_cfg = cls._extract_node_config(raw)
            base_cfg = cls._extract_node_config(base)
            # Prefer non-empty incoming; otherwise keep base. Shallow-merge keys.
            if incoming_cfg and base_cfg:
                cfg = {**base_cfg, **incoming_cfg}
            elif incoming_cfg:
                cfg = incoming_cfg
            else:
                cfg = base_cfg

            ntype = (
                raw.get('type')
                or (raw.get('data') or {}).get('type')
                or base.get('type')
                or (base.get('data') or {}).get('type')
                or 'llm'
            )
            label = cls._extract_node_label(
                raw,
                fallback=cls._extract_node_label(base, fallback=str(ntype)),
            )
            position = raw.get('position') or base.get('position') or {'x': 0, 'y': 0}
            data = {}
            if isinstance(base.get('data'), dict):
                data.update(base['data'])
            if isinstance(raw.get('data'), dict):
                # merge data but re-apply resolved config/label below
                for k, v in raw['data'].items():
                    if k == 'config' and (not isinstance(v, dict) or not v):
                        continue
                    data[k] = v
            data['label'] = label
            data['type'] = ntype
            data['config'] = cfg
            if 'description' not in data:
                data['description'] = raw.get('description') or base.get('description') or ''

            node_out = {
                **base,
                **{k: v for k, v in raw.items() if k not in ('config', 'data', 'name', 'type', 'position')},
                'id': nid or raw.get('id') or base.get('id'),
                'type': ntype,
                'name': label,
                'position': position,
                'config': cfg,
                'data': data,
            }
            merged.append(node_out)
            if nid:
                seen.add(nid)

        # Keep current nodes that LLM omitted (partial patch responses)
        for nid, node in current_by_id.items():
            if nid not in seen:
                merged.append(copy.deepcopy(node))
        return merged

    @classmethod
    def parse_modification(
        cls,
        response: str,
        current_workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse modification response and merge with current workflow.

        Args:
            response: LLM response text
            current_workflow: Current workflow dict

        Returns:
            Updated workflow dict
        """
        try:
            parser = cls.get_modification_parser()
            parsed = parser.parse(response)
            modifications = parsed.model_dump(exclude_unset=True)

            # Merge only fields that LLM actually returned — preserve existing values for unset fields
            updated = copy.deepcopy(current_workflow) if isinstance(current_workflow, dict) else {}
            for key, value in modifications.items():
                if value is None:
                    continue
                if key == 'nodes' and isinstance(value, list):
                    updated['nodes'] = cls._merge_nodes_by_id(
                        current_workflow.get('nodes') or [],
                        value,
                    )
                else:
                    updated[key] = value

            # Normalize if nodes/edges changed
            if 'nodes' in modifications or 'edges' in modifications:
                updated = cls._normalize_workflow(updated)

            return updated

        except OutputParserException as e:
            logger.warning(f"Modification parsing failed: {e}")
            # Truncated LLM JSON is common — try regex/json recovery then merge
            try:
                recovered = cls._fallback_regex_parse(response)
                if isinstance(recovered, dict) and recovered.get('nodes'):
                    merged_nodes = cls._merge_nodes_by_id(
                        current_workflow.get('nodes') or [],
                        recovered.get('nodes') or [],
                    )
                    updated = copy.deepcopy(current_workflow) if isinstance(current_workflow, dict) else {}
                    updated['nodes'] = merged_nodes
                    if recovered.get('edges'):
                        updated['edges'] = recovered['edges']
                    if recovered.get('name'):
                        updated['name'] = recovered['name']
                    if recovered.get('description') is not None:
                        updated['description'] = recovered['description']
                    return cls._normalize_workflow(updated)
            except Exception as recover_err:
                logger.warning('Modification recovery failed: %s', recover_err)
            return current_workflow

        except Exception as e:
            logger.exception(f"Unexpected modification error: {e}")
            return current_workflow

    @classmethod
    def _normalize_workflow(cls, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize workflow structure with defaults and validation.

        Preserves VueFlow `data.config` / `data.label` so editor saves don't wipe configs.
        """
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])

        # Build node ID map for edge normalization
        node_id_map = {}
        normalized_nodes = []

        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node_id = node.get('id') or f'node_{i + 1}'
            node_id_map[node.get('id', node_id)] = node_id
            ntype = (
                node.get('type')
                or (node.get('data') or {}).get('type')
                or 'llm'
            )
            label = cls._extract_node_label(node, fallback=str(ntype))
            cfg = cls._extract_node_config(node)
            position = node.get('position') or {'x': 100 + i * 180, 'y': 150}
            data = dict(node.get('data') or {}) if isinstance(node.get('data'), dict) else {}
            data['label'] = label
            data['type'] = ntype
            data['config'] = cfg

            normalized_nodes.append({
                'id': node_id,
                'type': ntype,
                'name': label,
                'position': position,
                'config': cfg,
                'data': data,
            })

        # Normalize edges
        normalized_edges = []
        for i, edge in enumerate(edges):
            source = edge.get('source', '')
            target = edge.get('target', '')

            # Map old IDs to new IDs if they were generated
            mapped_source = node_id_map.get(source, source)
            mapped_target = node_id_map.get(target, target)

            normalized_edges.append({
                'id': edge.get('id', f'edge_{i + 1}'),
                'source': mapped_source,
                'target': mapped_target,
                'label': edge.get('label', '')
            })

        return {
            'name': workflow.get('name', 'Generated Workflow'),
            'description': workflow.get('description', ''),
            'nodes': normalized_nodes,
            'edges': normalized_edges
        }

    @classmethod
    def _fallback_regex_parse(cls, response: str) -> Dict[str, Any]:
        """
        Fallback regex-based parsing when structured parsing fails.

        This handles edge cases where LLM doesn't follow format instructions.
        """
        import re

        # Try to find JSON in code blocks first
        code_block_match = re.search(
            r'```(?:json)?\s*([\s\S]+?)\s*```',
            response
        )
        if code_block_match:
            json_str = code_block_match.group(1)
            try:
                data = json.loads(json_str)
                return cls._normalize_workflow(data)
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return cls._normalize_workflow(data)
            except json.JSONDecodeError:
                pass

        return {
            'error': ERROR_MESSAGES.get('parse_error', '无法解析工作流描述'),
            'raw_response': response[:500] if len(response) > 500 else response
        }

    @classmethod
    def validate_workflow(cls, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate workflow structure and add validation result.

        Returns:
            Workflow with 'validation' and 'estimated_cost' fields
        """
        errors = []
        warnings = []

        # Name validation
        if not workflow.get('name'):
            workflow['name'] = 'Generated Workflow'

        # Nodes validation
        nodes = workflow.get('nodes', [])
        if not nodes:
            errors.append(VALIDATION_MESSAGES.get('missing_nodes', '缺少节点'))

        node_types = [n.get('type') for n in nodes]

        # Start/end validation
        if 'start' not in node_types:
            warnings.append(
                VALIDATION_MESSAGES.get('missing_start', '缺少开始节点')
            )
        if 'end' not in node_types:
            warnings.append(
                VALIDATION_MESSAGES.get('missing_end', '缺少结束节点')
            )

        # Multiple starts
        start_count = node_types.count('start')
        if start_count > 1:
            errors.append(
                VALIDATION_MESSAGES.get('multiple_starts', f'有 {start_count} 个开始节点')
            )

        # Connected nodes validation
        connected = set()
        for edge in workflow.get('edges', []):
            if edge.get('source'):
                connected.add(edge.get('source'))
            if edge.get('target'):
                connected.add(edge.get('target'))

        node_ids = {n.get('id') for n in nodes}
        disconnected = node_ids - connected - {'start'}

        if disconnected:
            warnings.append(
                VALIDATION_MESSAGES.get(
                    'disconnected_nodes',
                    f'节点 {list(disconnected)[:3]} 未连接'
                )
            )

        # Cycle detection
        has_cycle, cycle_path = cls._detect_cycle(workflow)
        if has_cycle:
            cycle_str = ' -> '.join(cycle_path[:6])
            if len(cycle_path) > 6:
                cycle_str += ' -> ...'
            errors.append(f'工作流存在循环依赖: {cycle_str}')

        # Estimate cost
        estimated_cost = cls._estimate_cost(workflow)

        # Add validation result
        workflow['validation'] = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
        workflow['estimated_cost'] = estimated_cost

        return workflow

    @classmethod
    def _detect_cycle(cls, workflow: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Detect cycles using DFS."""
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])

        graph = {n.get('id'): [] for n in nodes}
        for edge in edges:
            source, target = edge.get('source'), edge.get('target')
            if source and target and source in graph and target in graph:
                graph[source].append(target)

        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> List[str]:
            if node_id not in graph:
                return []
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node_id)
            return []

        for node in nodes:
            node_id = node.get('id')
            if node_id and node_id not in visited:
                cycle = dfs(node_id)
                if cycle:
                    return True, cycle

        return False, []

    @classmethod
    def _estimate_cost(cls, workflow: Dict[str, Any]) -> float:
        """Estimate workflow execution cost."""
        weights = {
            'llm': 10.0, 'http': 3.0, 'tool': 3.0,
            'code': 2.0, 'email': 2.0, 'webhook': 2.0,
            'condition': 0.5, 'input': 0.5, 'output': 0.5,
            'start': 0.1, 'end': 0.1, 'prompt': 5.0
        }

        total = 0.0
        for node in workflow.get('nodes', []):
            node_type = node.get('type', 'unknown')
            cost = weights.get(node_type, 1.0)

            # Premium models cost more
            if node_type == 'llm':
                model = node.get('config', {}).get('model', '')
                if 'gpt-4' in model.lower() or 'claude' in model.lower():
                    cost *= 2.0

            total += cost

        # Edge overhead
        total += len(workflow.get('edges', [])) * 0.1

        # Complexity multiplier
        if len(workflow.get('nodes', [])) > 20:
            total *= 1.5
        elif len(workflow.get('nodes', [])) > 10:
            total *= 1.2

        return round(total, 2)


# Convenience functions
def parse_workflow_response(response: str) -> Dict[str, Any]:
    """
    Parse LLM response to workflow structure.

    Usage:
        response = llm.invoke(prompt)
        workflow = parse_workflow_response(response.content)
    """
    return WorkflowOutputParser.parse_workflow(response)


def validate_workflow_structure(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and enrich workflow with metadata."""
    return WorkflowOutputParser.validate_workflow(workflow)
