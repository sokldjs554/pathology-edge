import importlib
import numpy as np
import pytest


def api():return importlib.import_module('pathology_edge.ki67_transfer_reference')


def test_two_level_palette_noise_is_logged_without_mutating_original():
    mask=np.array([[[253,0,2],[0,0,255]],[[0,255,0],[0,0,0]]],dtype=np.uint8);old=mask.copy()
    clean,audit=api().normalize_reference(mask)
    assert np.array_equal(mask,old) and clean[0,0].tolist()==[255,0,0]
    assert audit['changed_pixels']==1 and audit['colors']==[{'from':[253,0,2],'to':[255,0,0],'pixels':1}]
    assert np.array_equal(api().independent_normalize(mask),clean)


@pytest.mark.parametrize('rgb',[[252,0,3],[127,0,127],[255,255,255],[0,80,175]])
def test_larger_or_ambiguous_palette_deviations_are_rejected(rgb):
    mask=np.array([[rgb]],dtype=np.uint8)
    with pytest.raises(ValueError):api().normalize_reference(mask)
    with pytest.raises(ValueError):api().independent_normalize(mask)


def test_canonical_palette_is_unchanged_and_zero_repair_recorded():
    mask=np.array([[[255,0,0],[0,0,255],[0,255,0],[0,0,0]]],dtype=np.uint8)
    clean,audit=api().normalize_reference(mask)
    assert np.array_equal(clean,mask) and audit['changed_pixels']==0 and audit['colors']==[]
