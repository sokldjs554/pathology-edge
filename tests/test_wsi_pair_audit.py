import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize('damage',['missing_prediction','missing_input','missing_model','redirected_path'])
def test_incomplete_or_redirected_comparison_cannot_pass_audit(damage):
    spec=importlib.util.spec_from_file_location('pair_runner',Path(__file__).parents[1]/'scripts/evaluate_wsi_pairs.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    protocol={'cases':[{'case_id':f'case{i}'} for i in range(3)],'expected_model_sha256':{'small_vit':'a','small_vit_refined':'b'}}
    report={'rows':[],'predictions':{},'means':{}}
    for item in protocol['cases']:
        inputs={}
        for rendition in ('original','provided'):
            inputs[rendition]={}
            for model in protocol['expected_model_sha256']:
                name=f'predictions/{item["case_id"]}-{rendition}-{model}.npz'
                inputs[rendition][model]={'probability':name,'metrics':dict(all={},boundary={},interior={})}
                report['predictions'][name]='sha'
        report['rows'].append(dict(case_id=item['case_id'],inputs=inputs))
    report['means']={i:{m:dict(all=0,boundary=0,interior=0) for m in protocol['expected_model_sha256']} for i in ('original','provided')}
    module.validate_result_layout(report,protocol)
    if damage=='missing_prediction':report['predictions'].pop(next(iter(report['predictions'])))
    if damage=='missing_input':report['rows'][0]['inputs'].pop('provided')
    if damage=='missing_model':report['rows'][0]['inputs']['original'].pop('small_vit_refined')
    if damage=='redirected_path':report['rows'][0]['inputs']['original']['small_vit']['probability']='../wrong.npz'
    with pytest.raises(ValueError):module.validate_result_layout(report,protocol)
