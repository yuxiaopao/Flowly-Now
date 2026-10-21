"""Account profile upload policy."""

AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_MAX_PIXELS = 16 * 1024 * 1024
AVATAR_SIZE = (256, 256)
AVATAR_FORMATS = frozenset({'JPEG', 'PNG'})
AVATAR_STORAGE_DIRECTORY = 'avatars'
AVATAR_MESSAGES = {
    'size': '头像大小不能超过 2 MB',
    'format': '请选择有效的 JPG 或 PNG 图片',
    'pixels': '头像分辨率过大，请缩小图片后重试',
}

AVATAR_SHAPES = ('cercle', 'galet', 'squircle', 'capsule', 'triangle', 'hexagone', 'nuage', 'goutte')
AVATAR_COLORS = ('encre', 'brun', 'rouge', 'orange', 'ambre', 'vert', 'turquoise', 'bleu', 'violet', 'rose', 'gris', 'creme')
AVATAR_EXPRESSIONS = ('neutre', 'attentif', 'surpris', 'excite', 'heureux', 'hilare', 'colere', 'triste', 'effraye', 'mefiant', 'confus', 'curieux', 'fier', 'timide', 'blase', 'somnolent')
AVATAR_STATES = ('idle', 'thinking', 'wink', 'wide', 'alert', 'notify', 'exclaim', 'sleep', 'egg', 'hexagon', 'play', 'orbit', 'burst', 'comet')
AVATAR_MAX_BLOCKS = 200
AVATAR_MIN_DURATION = 0.1
AVATAR_MAX_DURATION = 10
