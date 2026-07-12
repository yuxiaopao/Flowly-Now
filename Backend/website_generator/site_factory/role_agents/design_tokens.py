"""Design tokens derived from project profile and wizard."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional


TONE_PALETTES: Dict[str, Dict[str, str]] = {
    'friendly': {
        'primary': '#6366f1',
        'primaryHover': '#818cf8',
        'accent': '#a78bfa',
        'surface': '#18181f',
        'surfaceElevated': '#1f1f2e',
        'border': '#2e2e42',
        'text': '#f4f4f5',
        'textMuted': '#a1a1aa',
        'background': '#0f0f14',
    },
    'industrial_warning': {
        'primary': '#f59e0b',
        'primaryHover': '#fbbf24',
        'accent': '#fb923c',
        'surface': '#18181f',
        'surfaceElevated': '#1f1f2e',
        'border': '#2e2e42',
        'text': '#f4f4f5',
        'textMuted': '#a1a1aa',
        'background': '#0f0f14',
    },
    'alert_red': {
        'primary': '#ef4444',
        'primaryHover': '#f87171',
        'accent': '#dc2626',
        'surface': '#18181f',
        'surfaceElevated': '#1f1f2e',
        'border': '#2e2e42',
        'text': '#f4f4f5',
        'textMuted': '#a1a1aa',
        'background': '#0f0f14',
    },
    'quality_inspect': {
        'primary': '#06b6d4',
        'primaryHover': '#22d3ee',
        'accent': '#0891b2',
        'surface': '#18181f',
        'surfaceElevated': '#1f1f2e',
        'border': '#2e2e42',
        'text': '#f4f4f5',
        'textMuted': '#a1a1aa',
        'background': '#0f0f14',
    },
}


def build_design_tokens(
    profile: Optional[Dict[str, Any]] = None,
    wizard: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    profile = profile or {}
    wizard = wizard or {}
    tone = (profile.get('ui_tone') or 'industrial_warning').strip()
    palette = dict(TONE_PALETTES.get(tone, TONE_PALETTES['industrial_warning']))

    custom_primary = (wizard.get('primaryColor') or '').strip()
    if custom_primary and custom_primary.startswith('#') and len(custom_primary) == 7:
        palette['primary'] = custom_primary
        palette['primaryHover'] = custom_primary

    return {
        'version': '1.0',
        'ui_tone': tone,
        'site_name': wizard.get('siteName') or profile.get('scenario') or 'AI Site',
        'scenario': profile.get('scenario') or '',
        'domain': profile.get('domain') or '',
        'colors': palette,
        'typography': {
            'fontFamily': "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif",
            'fontSizeBase': '16px',
            'fontSizeSm': '14px',
            'fontSizeLg': '20px',
            'fontSizeXl': '28px',
            'lineHeight': '1.5',
        },
        'spacing': {
            'xs': '4px',
            'sm': '8px',
            'md': '16px',
            'lg': '24px',
            'xl': '40px',
        },
        'radius': {
            'sm': '8px',
            'md': '12px',
            'lg': '16px',
        },
        'copy_hints': profile.get('copy_hints') or [],
    }


def write_design_tokens(output_dir: str, tokens: Dict[str, Any]) -> str:
    flowly_dir = os.path.join(output_dir, '.flowly')
    os.makedirs(flowly_dir, exist_ok=True)
    path = os.path.join(flowly_dir, 'design_tokens.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)
    return path


def load_design_tokens(output_dir: str) -> Dict[str, Any]:
    path = os.path.join(output_dir, '.flowly', 'design_tokens.json')
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def tokens_to_css_variables(tokens: Dict[str, Any]) -> str:
    colors = (tokens.get('colors') or {})
    typo = (tokens.get('typography') or {})
    spacing = (tokens.get('spacing') or {})
    radius = (tokens.get('radius') or {})
    lines = [
        ':root {',
        f"  --color-primary: {colors.get('primary', '#f59e0b')};",
        f"  --color-primary-hover: {colors.get('primaryHover', '#fbbf24')};",
        f"  --color-accent: {colors.get('accent', colors.get('primary', '#f59e0b'))};",
        f"  --color-bg: {colors.get('background', '#0f0f14')};",
        f"  --color-surface: {colors.get('surface', '#18181f')};",
        f"  --color-surface-elevated: {colors.get('surfaceElevated', '#1f1f2e')};",
        f"  --color-border: {colors.get('border', '#2e2e42')};",
        f"  --color-text: {colors.get('text', '#f4f4f5')};",
        f"  --color-text-muted: {colors.get('textMuted', '#a1a1aa')};",
        f"  --font-family: {typo.get('fontFamily', 'sans-serif')};",
        f"  --font-size-base: {typo.get('fontSizeBase', '16px')};",
        f"  --font-size-sm: {typo.get('fontSizeSm', '14px')};",
        f"  --font-size-lg: {typo.get('fontSizeLg', '20px')};",
        f"  --font-size-xl: {typo.get('fontSizeXl', '28px')};",
        f"  --space-sm: {spacing.get('sm', '8px')};",
        f"  --space-md: {spacing.get('md', '16px')};",
        f"  --space-lg: {spacing.get('lg', '24px')};",
        f"  --space-xl: {spacing.get('xl', '40px')};",
        f"  --radius-sm: {radius.get('sm', '8px')};",
        f"  --radius-md: {radius.get('md', '12px')};",
        f"  --radius-lg: {radius.get('lg', '16px')};",
        '}',
    ]
    return '\n'.join(lines) + '\n'
