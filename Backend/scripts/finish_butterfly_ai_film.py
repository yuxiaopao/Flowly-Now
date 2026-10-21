"""Finish and verify eight genuine AI video outputs without padding or repeats."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'output/butterfly-video/ai_60'
SPEC = ROOT / 'Backend/workflows/services/butterfly_ltx_spec.json'
FONT = 'Microsoft YaHei'
FINAL_NAME = '蝶羽共生纹-60秒-AI直接生成.mp4'


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration:stream=codec_name,width,height,nb_frames,r_frame_rate', '-of', 'json', str(path),
    ], text=True, timeout=30))


def validate_clips(spec, directory=OUTPUT):
    records = []
    for shot in spec['shots']:
        path = directory / 'clips' / (shot['id'] + '.mp4')
        record_path = path.with_suffix('.json')
        if not path.is_file() or not record_path.is_file():
            raise ValueError('Missing real model video or provenance: ' + shot['id'])
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if record.get('provider') not in ('ltx_local', 'ltx_public') or not record.get('model', '').startswith('Lightricks/'):
            raise ValueError('Unverified model origin: ' + shot['id'])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if record.get('sha256') != digest:
            raise ValueError('Clip differs from recorded model output: ' + shot['id'])
        metadata = probe(path)
        stream = metadata['streams'][0]
        if abs(float(metadata['format']['duration']) - spec['seconds']) > 0.05:
            raise ValueError('Short clip; padding is prohibited: ' + shot['id'])
        if stream['width'] != spec['width'] or stream['height'] != spec['height'] or stream['r_frame_rate'] != f'{spec["fps"]}/1':
            raise ValueError('Clip dimensions or frame rate differ from the finishing specification')
        records.append({'id': shot['id'], 'caption': shot['caption'], 'path': str(path.resolve()),
                        'provider': record['provider'], 'model': record['model'], 'sha256': digest, 'media': metadata})
    if len({row['sha256'] for row in records}) != len(spec['shots']):
        raise ValueError('Repeated video clip; cannot finish the film')
    return records


def ass_time(seconds):
    centiseconds = round(seconds * 100)
    return f'{centiseconds//360000}:{centiseconds//6000%60:02}:{centiseconds//100%60:02}.{centiseconds%100:02}'


def finish():
    spec = json.loads(SPEC.read_text(encoding='utf-8'))
    records = validate_clips(spec)
    encoded_directory = OUTPUT / 'encoded-clips'
    encoded_directory.mkdir(exist_ok=True)
    encoded_paths = []
    for row in records:
        encoded_path = encoded_directory / (row['id'] + '.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-i', row['path'], '-map', '0:v:0',
            '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
            '-pix_fmt', 'yuv420p', '-video_track_timescale', '15360',
            '-movflags', '+faststart', str(encoded_path),
        ], check=True, timeout=180)
        metadata = probe(encoded_path)
        if (metadata['streams'][0]['nb_frames'] != row['media']['streams'][0]['nb_frames']
                or metadata['streams'][0]['r_frame_rate'] != row['media']['streams'][0]['r_frame_rate']
                or abs(float(metadata['format']['duration']) - spec['seconds']) > 0.05):
            raise ValueError('Codec normalization changed the model frame count or timing')
        encoded_paths.append(encoded_path)
    concat = OUTPUT / 'ai-clips.txt'
    concat.write_text('\n'.join("file '" + str(path.resolve()).replace('\\', '/').replace("'", "'\\''") + "'" for path in encoded_paths) + '\n', encoding='utf-8')
    clean = OUTPUT / '蝶羽共生纹-60秒-AI纯画面.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(concat), '-an', '-c:v', 'copy', '-movflags', '+faststart', str(clean)], check=True, timeout=120)
    header = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1024\nPlayResY: 576\nWrapStyle: 2\n'
              '[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n'
              f'Style: Phase,{FONT},23,&H00FFFFFF,&H00FFFFFF,&H70332A22,&H70332A22,0,0,0,0,100,100,0,0,3,8,0,2,32,32,19,1\n'
              f'Style: Disclosure,{FONT},13,&H00665C50,&H00665C50,&H70FFFFFF,&H70FFFFFF,0,0,0,0,100,100,0,0,1,1,0,9,18,18,15,1\n'
              '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
    events = [f'Dialogue: 0,{ass_time(i*spec["seconds"])},{ass_time((i+1)*spec["seconds"])},Phase,,0,0,0,,{shot["caption"]}' for i, shot in enumerate(spec['shots'])]
    events.append('Dialogue: 1,0:00:00.00,0:01:00.00,Disclosure,,0,0,0,,AI 生成概念演示')
    subtitles = OUTPUT / 'ai-phases.ass'
    subtitles.write_text(header + '\n'.join(events) + '\n', encoding='utf-8')
    final = OUTPUT / FINAL_NAME
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(clean), '-vf', 'ass=ai-phases.ass', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-an', '-movflags', '+faststart', str(final)], cwd=OUTPUT, check=True, timeout=600)
    verification = probe(final)
    if abs(float(verification['format']['duration']) - 60) > 0.05 or int(verification['streams'][0]['nb_frames']) != 1800:
        raise ValueError('Final film must have 60 seconds and 1800 original model frames')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(final), '-f', 'null', '-'], check=True, capture_output=True, timeout=120)
    for seconds in (3, 11, 19, 26, 34, 41, 49, 57):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(seconds), '-i', str(final), '-frames:v', '1', str(OUTPUT / f'final-preview-{seconds:02}.png')], check=True, timeout=30)
    report = {'status': 'completed', 'video': str(final.resolve()), 'clean_video': str(clean.resolve()),
              'media': verification, 'full_decode': 'passed', 'duration_padding': False,
              'repeated_clips': False, 'clips': records, 'sha256': hashlib.sha256(final.read_bytes()).hexdigest()}
    (OUTPUT / 'ai-film-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)
    return report


if __name__ == '__main__':
    finish()
