# 国赛 CUMCM 完整资源包（Modex 逆向复刻）

> **诚实说明**：本包包含 Modex-MH-Agent v1.7.3 中 `comp_cumcm` 工作流相关的**全部可验证原始资产**。
> **SKILL.md 正文无法在无 license 情况下解密** — 包内 `skills-encrypted/` 为原样 `.enc` 二进制，不是 AI 生成的替代品。

## 目录结构

| 路径 | 内容 | 可否直接使用 |
|------|------|-------------|
| `prompts/` | 8 个 backend 明文 prompt（100% Modex 原样） | ✅ |
| `style-profiles/` | `competition_zh.json` + `covers/cumcm.json` | ✅ |
| `format-reference/` | `reference_structure_comp_cumcm.md`（反汇编骨架+profile） | ✅ |
| `templates/cumcm/` | `cumcmthesis.cls` + 字体（可读） | ✅ |
| `workflows/` | `comp_cumcm.yaml` / `comp_cumcm_docx.yaml` | ✅ |
| `skills-encrypted/` | 全部 `.enc`（含 SKILL.md.enc） | ⚠️ 需解密 |
| `skills-metadata/` | 逆向扫描 JSON（产物路径、体积） | ✅ |
| `skill_prompt_map.json` | skill → runtime prompt 映射 | ✅ |
| `MANIFEST.json` | SHA256 校验清单 | ✅ |

## CUMCM 主流程（Modex 官方，LaTeX 路径）

```
comp-prob-analysis → comp-modeling → comp-code → comp-paper-zh → comp-compile-zh
```

产出：`PROBLEM_ANALYSIS.md` → `MODELING_REPORT.md` → `code/` → `paper/main.tex` → `paper/main.pdf`

## Word 导出路径（推断，params.output_format=docx）

```
comp-prob-analysis → comp-modeling → comp-code → paper-figure → comp-paper-zh-docx → docx-format-check → docx-export
```

`docx-export` 为 backend pyd 引擎步骤，不在 `skills/` 目录。

## 如何获得完整 SKILL.md（解密）

1. 在已激活 Modex license 的环境运行任意 comp 工作流
2. 或调用 `skill_crypto.set_decrypt_key(dk_hex)` → `skill_crypto.decrypt_skills_to_workspace()`
3. 解密后 SKILL.md 出现在 workspace `_utils/` 或 skills 目录
4. 将解密文件放入 Flowly `skills/<name>/SKILL.md` 即可

## 在 Flowly-Agent 中使用

```powershell
# 复制 workflow
Copy-Item packages\cumcm-full\workflows\comp_cumcm.yaml templates\workflows\

# 复制 prompts
Copy-Item packages\cumcm-full\prompts\* prompts\

# 复制格式 profile（docx 路径）
Copy-Item packages\cumcm-full\style-profiles\* tools\docx_style_profiles\ -Recurse
```

## 加密 SKILL 体积（供校验）

| Skill | SKILL.md.enc |
|-------|-------------|
| comp-prob-analysis | 77,993 B |
| comp-modeling | 41,137 B |
| comp-code | 59,759 B |
| comp-paper-zh | 112,924 B |
| comp-compile-zh | 44,150 B |
| comp-review | 6,381 B |
| comp-paper-zh-docx | 66,637 B |
| paper-figure | 85,334 B |
| docx-format-check | 23,232 B |

---
*由 `scripts/build_cumcm_pack.py` 从 `e:\Modex\Modex-MH-Agent` 打包，禁止将 Flowly 自研 prompt 冒充为本包内容。*
