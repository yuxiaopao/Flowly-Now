# -*- coding: utf-8 -*-
"""Tests for CUMCM Markdown → Word export."""

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from nl_to_workflow.cumcm_docx import markdown_to_docx


SAMPLE_MD = """# 资源分配优化研究

> 生成时间：2026-08-31

## 摘要

建立线性规划模型求解运输成本最小化问题。

**关键词**：线性规划；灵敏度分析；运输优化

## 一、问题重述与分析

**问题一**：建立运输成本最小化模型。

## 四、模型求解

### 主要数值结果汇总

| 子问题 | 求解类型 | 目标值/指标 | 状态 |
|---|---|---|---|
| 问1 | integer_programming | 1250 | ok |

## 参考文献

[1] 张三. 运筹学基础[M]. 北京: 高等教育出版社, 2020.
"""


class CumcmDocxTests(SimpleTestCase):
    def test_markdown_to_docx_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'paper' / 'main.docx'
            written = markdown_to_docx(SAMPLE_MD, out)
            self.assertTrue(written.is_file())
            self.assertGreater(written.stat().st_size, 1000)

    def test_docx_contains_sections(self):
        from docx import Document

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'main.docx'
            markdown_to_docx(SAMPLE_MD, out)
            doc = Document(str(out))
            texts = [p.text for p in doc.paragraphs if p.text.strip()]
            joined = '\n'.join(texts)
            self.assertIn('摘要', joined)
            self.assertIn('关键词', joined)
            self.assertIn('参考文献', joined)
