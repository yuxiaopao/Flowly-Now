"""Parser resilience: incomplete end node / missing edges still parse."""
from nl_to_workflow.output_parser import WorkflowOutputParser


def test_parse_workflow_fills_end_and_edges():
    raw = '''
    {
      "name": "武侠短篇剧情工业化流水线",
      "description": "主题到成片",
      "nodes": [
        {"id": "node_1", "type": "start", "config": {}},
        {"id": "node_2", "type": "input", "name": "输入创作主题", "position": {"x": 280, "y": 200}, "config": {"input_name": "theme"}},
        {"id": "node_3", "type": "llm", "name": "世界观", "position": {"x": 460, "y": 200}, "config": {"model": "agnes-2.0-flash", "user_template": "{input}"}},
        {"id": "node_4", "type": "image_generation", "name": "生图", "position": {"x": 640, "y": 200}, "config": {"provider": "agnes", "prompt": "{prompt}"}},
        {"id": "node_5", "type": "video_generation", "name": "生视频", "position": {"x": 820, "y": 200}, "config": {"provider": "agnes", "inputImage": "{images.0.url}"}},
        {"id": "node_6", "type": "output", "name": "输出", "position": {"x": 1000, "y": 200}, "config": {}},
        {"id": "node_7", "type": "end"}
      ]
    }
    '''
    wf = WorkflowOutputParser.parse_workflow(raw)
    assert 'error' not in wf
    assert len(wf['nodes']) == 7
    end = next(n for n in wf['nodes'] if n['type'] == 'end')
    assert end.get('name')
    assert end.get('position')
    assert len(wf['edges']) >= 6
