#!/usr/bin/env python3
"""Audit saved validation outputs and render reproducible CNN/ViT error panels.

No training, checkpoint execution, test inference, or edits to source results.
"""
import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FP_COLOR = (0, 187, 222)
FN_COLOR = (226, 65, 152)
TP_COLOR = (220, 220, 220)
BG_COLOR = (30, 35, 39)
FIXED_COLOR = (85, 205, 125)
WORSE_COLOR = (255, 162, 50)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_masks(*masks):
    if (not masks or any(not isinstance(m, np.ndarray) or m.ndim != 2 or
                         not m.size or m.dtype != np.bool_ for m in masks) or
            any(m.shape != masks[0].shape for m in masks)):
        raise ValueError('Equal nonempty 2D boolean masks required')


def metrics(prediction, target):
    tp = int(np.count_nonzero(prediction & target))
    fp = int(np.count_nonzero(prediction & ~target))
    fn = int(np.count_nonzero(~prediction & target))
    return dict(tp=tp, fp=fp, fn=fn, pixels=int(target.size),
                dice=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.)


def compare_masks(cnn, vit, target):
    validate_masks(cnn, vit, target)
    a, b = metrics(cnn, target), metrics(vit, target)
    return dict(cnn=a, vit=b, delta_dice=b['dice']-a['dice'],
                corrected_pixels=int(np.count_nonzero((cnn != target) & (vit == target))),
                worsened_pixels=int(np.count_nonzero((cnn == target) & (vit != target))),
                changed_pixels=int(np.count_nonzero(cnn != vit)))


def select_cases(rows):
    """Largest positive/negative image-macro Dice delta; lexical ID breaks ties."""
    if any(not math.isfinite(r['delta_dice']) for r in rows):
        raise ValueError('Nonfinite case delta')
    positive = sorted((r for r in rows if r['delta_dice'] > 0),
                      key=lambda r: (-r['delta_dice'], r['id']))
    negative = sorted((r for r in rows if r['delta_dice'] < 0),
                      key=lambda r: (r['delta_dice'], r['id']))
    return dict(improved=positive[0]['id'] if positive else None,
                worsened=negative[0]['id'] if negative else None)


def select_crop(cnn, vit, target, direction, *, size=128, step=32):
    """Maximize signed net corrected pixels, not local Dice; xyxy, exclusive end."""
    validate_masks(cnn, vit, target)
    if direction not in ('improved', 'worsened') or type(size) is not int or type(step) is not int or min(size, step) <= 0:
        raise ValueError('Valid direction and positive integer crop size/step required')
    height, width = target.shape
    w, h = min(width, size), min(height, size)
    xs = sorted(set(range(0, width-w+1, step)) | {width-w})
    ys = sorted(set(range(0, height-h+1, step)) | {height-h})
    change = (cnn != target).astype(np.int32) - (vit != target).astype(np.int32)
    if direction == 'worsened':
        change = -change
    integral = np.pad(change, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    best_score, best = None, None
    for y in ys:
        for x in xs:
            score = int(integral[y+h, x+w]-integral[y, x+w]-integral[y+h, x]+integral[y, x])
            if best_score is None or score > best_score:
                best_score, best = score, [x, y, x+w, y+h]
    return best


def error_rgb(prediction, target):
    validate_masks(prediction, target)
    result = np.empty((*target.shape, 3), np.uint8)
    result[:] = BG_COLOR
    result[prediction & target] = TP_COLOR
    result[prediction & ~target] = FP_COLOR
    result[~prediction & target] = FN_COLOR
    return result


def render_panel(path, rgb, cnn, vit, target, *, bbox=None, crop=False):
    """Nearest-neighbor display only; quantitative pixels remain native resolution."""
    fixed, worse = (cnn != target) & (vit == target), (cnn == target) & (vit != target)
    change = (rgb.astype(float)*.35).astype(np.uint8)
    change[fixed], change[worse] = FIXED_COLOR, WORSE_COLOR
    panels = [rgb, np.repeat((target*255).astype(np.uint8)[..., None], 3, axis=2),
              error_rgb(cnn, target), error_rgb(vit, target), change]
    if crop:
        x0, y0, x1, y1 = bbox
        panels = [p[y0:y1, x0:x1] for p in panels]
    width = 384 if crop else rgb.shape[1]
    height = round(panels[0].shape[0]*width/panels[0].shape[1])
    sheet = Image.new('RGB', (width*5, height+40), (247, 248, 249))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 17)
    except OSError:
        font = ImageFont.load_default()
    for i, (array, label) in enumerate(zip(panels, ['H&E image', 'Ground truth', 'CNN: FP / FN', 'ViT: FP / FN', 'Corrected / worsened'])):
        panel = Image.fromarray(array).resize((width, height), Image.Resampling.NEAREST)
        if bbox and not crop:
            x0, y0, x1, y1 = bbox
            ImageDraw.Draw(panel).rectangle((x0, y0, x1-1, y1-1), outline=(255, 209, 70), width=2)
        sheet.paste(panel, (i*width, 40))
        draw.text((i*width+8, 10), label, fill=(25, 42, 54), font=font)
    sheet.save(path)


def _trusted_auditor():
    path = Path(__file__).with_name('run_model_comparison.py')
    spec = importlib.util.spec_from_file_location('trusted_pair_auditor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze(run, data, output, *, provenance_label):
    run, data, out = Path(run).resolve(), Path(data).resolve(), Path(output).resolve()
    if out.exists():
        raise FileExistsError(out)
    if provenance_label not in ('development-reference', 'user-codespaces'):
        raise ValueError('Explicit provenance label required')
    if any(out.is_relative_to(p) or p.is_relative_to(out) for p in (run, data)):
        raise ValueError('Output overlaps source run or dataset')
    auditor = _trusted_auditor()
    audited = auditor.summarize(run, data_override=data)
    manifest = auditor.read(data/'manifest.json')
    reports = [auditor.read(run/arm/'training.json') for arm in auditor.ARCHITECTURES]
    inputs = {str(run/'protocol.json'): sha(run/'protocol.json'),
              str(data/'manifest.json'): sha(data/'manifest.json')}
    rows, images = [], {}
    for index, record in enumerate(r for r in manifest['records'] if r['split'] == 'validation'):
        paths = [data/record['image'], data/record['mask']]
        with Image.open(paths[0]) as im:
            rgb = np.asarray(im.convert('RGB'))
        with Image.open(paths[1]) as im:
            target = np.asarray(im.convert('L')) > 0
        predictions = []
        regional = {}
        for arm, report in zip(auditor.ARCHITECTURES, reports):
            saved = report['validation']['rows'][index]
            if saved['id'] != record['id']:
                raise ValueError('Validation image IDs differ')
            path = run/arm/saved['prediction']
            paths.extend([path, run/arm/'training.json'])
            predictions.append(np.load(path, allow_pickle=False) >= report['threshold'])
            regional[arm] = saved['metrics']
        if rgb.shape[:2] != target.shape:
            raise ValueError('RGB and GT dimensions differ')
        inputs.update({str(p): sha(p) for p in paths})
        result = compare_masks(*predictions, target)
        for arm, model in zip(auditor.ARCHITECTURES, ('cnn', 'vit')):
            if any(result[model][k] != regional[arm]['all'][k] for k in result[model]):
                raise ValueError('Recounted pixels differ from audited metrics')
        rows.append(dict(id=record['id'], group_id=record['group_id'], **result,
                         metrics_by_region=regional))
        images[record['id']] = (rgb, *predictions, target)
    selection = select_cases(rows)
    if any(sha(path) != digest for path, digest in inputs.items()):
        raise ValueError('Inputs changed during analysis')
    out.mkdir(parents=True)
    cases = []
    try:
        for direction, identity in selection.items():
            if identity is None:
                continue
            rgb, cnn, vit, target = images[identity]
            bbox = select_crop(cnn, vit, target, direction)
            x0, y0, x1, y1 = bbox
            crop_counts = compare_masks(cnn[y0:y1, x0:x1], vit[y0:y1, x0:x1], target[y0:y1, x0:x1])
            render_panel(out/f'{direction}-full.png', rgb, cnn, vit, target, bbox=bbox)
            render_panel(out/f'{direction}-crop.png', rgb, cnn, vit, target, bbox=bbox, crop=True)
            cases.append(dict(direction=direction, id=identity, crop_xyxy=bbox, crop_counts=crop_counts,
                              full_image=next(r for r in rows if r['id'] == identity),
                              full_panel=f'{direction}-full.png', crop_panel=f'{direction}-crop.png'))
        result = dict(schema_version=1, status='completed', provenance_label=provenance_label,
                      source_run=str(run), source_commit=auditor.read(run/'protocol.json')['source_commit'],
                      seed=audited['seed'], checkpoints={r['architecture']: r['model_sha256'] for r in audited['rows']},
                      thresholds={r['architecture']: r['threshold'] for r in audited['rows']},
                      scope='Previously used validation, 10 images / 2 case groups; selected checkpoint and threshold.',
                      case_selection='Largest positive and negative full-image Dice(ViT)-Dice(CNN); lexical ID tie break; absent directions omitted.',
                      crop_selection='128px square, 32px scan plus image endpoints; maximum signed net corrected pixels; first y/x tie. xyxy ends exclusive.',
                      rows=rows, cases=cases, input_hashes=inputs,
                      prediction_audit_regions=audited['validation_metric_regions_checked'],
                      model_inference_run=False, test_evaluation_run=False,
                      limitation='Post-hoc selected examples explain pixel errors, not prevalence or biological causes. Pixel changes are not nucleus counts. No independent test, external or clinical evidence.')
        (out/'report.json').write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
        _write_html(out, result)
        if any(sha(path) != digest for path, digest in inputs.items()):
            raise ValueError('Inputs changed while rendering')
        return result
    except BaseException as exc:
        (out/'status.json').write_text(json.dumps(dict(status='failed', error=str(exc)))+'\n')
        raise


def _write_html(out, result):
    body = ['<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>CNN–ViT 저장 결과 오류 분석</title><style>body{font:16px/1.6 system-ui;margin:24px;color:#213440;max-width:1500px}table{border-collapse:collapse}td,th{border-bottom:1px solid #ccd5dc;padding:6px 16px;text-align:right}td:first-child,th:first-child{text-align:left}.figure{overflow-x:auto;border:1px solid #ccd5dc}.figure img{display:block;width:100%;min-width:1000px;height:auto}h2{margin-top:36px}small{color:#516671}a{color:#05669b}</style>',
            '<h1>CNN–ViT 저장 결과 오류 분석</h1>',
            f'<p><b>실행 출처: {html.escape(result["provenance_label"])}</b> · seed {result["seed"]} · 검증 10장 / 2개 그룹</p>',
            '<p>저장된 확률과 정답으로 다시 계산한 결과입니다. 이 보고서는 모델을 다시 실행하지 않았습니다. 전체·경계·내부 수치는 <a href="report.json">원본 JSON</a>에서 확인할 수 있습니다.</p>',
            '<p>Dice는 높을수록 좋습니다. Δ는 ViT − CNN이며 이미지 전체 점수입니다. 검증 데이터에서 epoch·threshold를 선택했으므로 독립적인 성능 검증으로 해석하지 않습니다.</p>',
            '<table><thead><tr><th>이미지</th><th>CNN Dice</th><th>ViT Dice</th><th>Δ</th><th>교정 px</th><th>악화 px</th></tr></thead><tbody>']
    for row in result['rows']:
        body.append(f'<tr><td>{html.escape(row["id"])}</td><td>{row["cnn"]["dice"]:.6f}</td><td>{row["vit"]["dice"]:.6f}</td><td>{row["delta_dice"]:+.6f}</td><td>{row["corrected_pixels"]}</td><td>{row["worsened_pixels"]}</td></tr>')
    body.append('</tbody></table><p>오류 지도: <b style="color:#009ab5">청록 = FP (정답에는 없는 예측)</b>, <b style="color:#cc3686">분홍 = FN (놓친 정답)</b>, 회색 = 일치한 전경. 변화 지도: 초록 = 교정, 주황 = 악화. 모두 픽셀 수이며 핵 개수가 아닙니다.</p>')
    for case in result['cases']:
        direction = '전체 Dice 최대 상승' if case['direction'] == 'improved' else '전체 Dice 최대 하락'
        c = case['crop_counts']
        body.extend([f'<h2>{html.escape(case["id"])} · {direction}</h2>',
                     f'<p>공통 확대 위치 xyxy: {case["crop_xyxy"]} (끝 좌표 제외). 선택 영역 Dice {c["cnn"]["dice"]:.4f} → {c["vit"]["dice"]:.4f}; 교정 {c["corrected_pixels"]}px / 악화 {c["worsened_pixels"]}px.</p>',
                     f'<div class="figure"><img src="{case["full_panel"]}" alt="동일 위치 전체 이미지, 정답, CNN과 ViT 오류 및 변화 지도"></div>',
                     f'<p>노란 상자의 동일 영역 확대 — 최근접 보간 표시, 집계는 원본 픽셀 기준</p><div class="figure"><img src="{case["crop_panel"]}" alt="동일 관심 영역 확대 비교"></div>'])
    body.append('<h2>검토할 내용</h2><p>점수 차이가 FP 감소인지 FN 감소인지 먼저 확인하세요. 핵의 크기·밀집·염색 차이는 영상에서 관찰하고 별도로 검증할 가설입니다. 이 그림만으로 실패 원인을 확정하거나 개선된 핵의 개수를 주장하지 않습니다.</p><small>이미지: TNBC v1.1, CC-BY-4.0, DOI 10.5281/zenodo.2579118. 연구·교육용.</small></html>')
    (out/'index.html').write_text('\n'.join(body), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provenance-label', choices=('development-reference', 'user-codespaces'), required=True)
    args = parser.parse_args()
    result = analyze(args.run, args.data, args.output, provenance_label=args.provenance_label)
    print(json.dumps(dict(output=str(args.output), cases=[dict(id=c['id'], direction=c['direction'], crop_xyxy=c['crop_xyxy']) for c in result['cases']],
                          inference_run=False, prediction_audit_regions=result['prediction_audit_regions'])))


if __name__ == '__main__':
    main()
