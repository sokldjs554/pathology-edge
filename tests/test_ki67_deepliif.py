import importlib,io,struct,zlib
import numpy as np
from PIL import Image
import pytest


def module():
    try:return importlib.import_module('pathology_edge.ki67_deepliif')
    except ModuleNotFoundError:pytest.fail('DeepLIIF reference adapter missing')


def mask():
    m=np.zeros((12,14,3),np.uint8);m[1:4,2:5]=[255,0,0];m[6:9,9:12]=[0,0,255];m[0,:]=[0,255,0]
    return m


def test_native_reference_centers_classes_and_green_exclusion():
    xy,c,a=module().segmentation_centers(mask())
    np.testing.assert_equal(xy,[[3.,2.],[10.,7.]]);np.testing.assert_equal(c,[0,1]);assert a['green_pixels']==14 and a['retained_components']==2


def test_diagonal_eight_connectivity_majority_noise_and_border():
    m=np.zeros((12,14,3),np.uint8);m[0:2,0:2]=[255,0,0];m[2:4,2:4]=[255,0,0];m[3,3]=[0,0,255];m[7:9,9:11]=[0,0,255]
    xy,c,a=module().segmentation_centers(m)
    np.testing.assert_allclose(xy,[[1.5,1.5]]);assert c.tolist()==[0];assert a['mixed_components']==1 and a['border_components']==1 and a['discarded_small_components']==1


def test_empty_reference_is_reported_without_fabricating_cells():
    xy,c,a=module().segmentation_centers(np.zeros((4,5,3),np.uint8));assert xy.shape==(0,2) and c.shape==(0,) and a['retained_components']==0


@pytest.mark.parametrize('bad',[np.zeros((3,4),np.uint8),np.ones((3,4,3),np.uint8),np.zeros((3,4,3),float)])
def test_unknown_reference_schema_rejected(bad):
    with pytest.raises(ValueError):module().segmentation_centers(bad)


def test_tied_mixed_reference_cannot_be_silently_labeled():
    m=np.zeros((6,6,3),np.uint8);m[1:3,1:4]=[255,0,0];m[1,1:4]=[0,0,255]
    with pytest.raises(ValueError,match='tie'):module().segmentation_centers(m)


def png(array):
    out=io.BytesIO();Image.fromarray(array).save(out,format='PNG');return out.getvalue()


def test_six_tile_pair_uses_only_first_rgb_and_last_reference():
    a=np.zeros((512,3072,3),np.uint8);a[:,:512]=[17,23,41];a[:,512:2560]=[99,3,7];a[30:35,2560+20:2560+25]=[0,0,255]
    rgb,xy,c,audit=module().decode_paired_png(png(a));assert rgb.shape==(512,512,3);np.testing.assert_equal(rgb[0,0],[17,23,41]);np.testing.assert_equal(xy,[[22.,32.]]);assert c.tolist()==[1]
    with pytest.raises(ValueError):module().decode_paired_png(png(np.zeros((512,512,3),np.uint8)))


class Response:
    def __init__(self,status=206,header='bytes 3-5/10',data=b'abc'):self.status=status;self.headers={'Content-Range':header};self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n):return self.data[:n]


@pytest.mark.parametrize('response',[Response(200),Response(header='bytes 2-4/10'),Response(data=b'ab'),Response(data=b'abcd')])
def test_range_refuses_full_wrong_truncated_or_extra_response(monkeypatch,response):
    m=module();monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k:response)
    with pytest.raises(ValueError):m.read_range('https://example.org/a',3,5,10)


def test_range_and_zip_integrity(monkeypatch):
    m=module();monkeypatch.setattr(m.urllib.request,'urlopen',lambda *a,**k:Response());assert m.read_range('https://example.org/a',3,5,10)==b'abc'
    raw=b'payload';co=zlib.compressobj(wbits=-15);compressed=co.compress(raw)+co.flush();name=b'test.png'
    header=struct.pack('<4s5H3L2H',b'PK\x03\x04',20,0,8,0,0,zlib.crc32(raw),len(compressed),len(raw),len(name),0)
    archive=header+name+compressed;entry=dict(name=name.decode(),offset=0,method=8,compressed_bytes=len(compressed),uncompressed_bytes=len(raw),crc32=zlib.crc32(raw))
    monkeypatch.setattr(m,'read_range',lambda url,lo,hi,total:archive[lo:hi+1])
    result,meta=m.fetch_zip_entry('url',entry,len(archive));assert result==raw and len(meta['sha256'])==64
    entry['crc32']+=1
    with pytest.raises(ValueError):m.fetch_zip_entry('url',entry,len(archive))


def test_same_fraction_population_cannot_improve_by_dropping_image():
    m=module();a=[dict(image='a',gt_fraction=.5,pred_fraction=.3),dict(image='b',gt_fraction=1.,pred_fraction=.7),dict(image='c',gt_fraction=.4,pred_fraction=None)]
    b=[dict(image='a',gt_fraction=.5,pred_fraction=.5),dict(image='b',gt_fraction=1.,pred_fraction=None),dict(image='c',gt_fraction=.4,pred_fraction=.4)]
    result=m.paired_fraction(a,b);assert result['reference_ids']==['a','b'] and result['missing_B_ids']==['b'] and not result['passed'] and result['B_mae_pp'] is None
    b[1]['pred_fraction']=.9;result=m.paired_fraction(a,b);assert result['passed'] and result['B_mae_pp']==pytest.approx(5.) and result['additional_B_ids']==['c']


def test_empty_fraction_population_and_mismatched_references_not_success():
    m=module();a=[dict(image='a',gt_fraction=None,pred_fraction=.1)];assert not m.paired_fraction(a,a)['passed']
    with pytest.raises(ValueError):m.paired_fraction(a,[dict(image='b',gt_fraction=None,pred_fraction=.1)])
    with pytest.raises(ValueError):m.paired_fraction(a,[dict(image='a',gt_fraction=.8,pred_fraction=.1)])


def test_derived_two_class_scores_count_nontumor_predictions_as_cells():
    m=module();row=dict(image='a',points=[[1,1],[8,8]],gt_points=[[1,1],[8,8]],gt_classes=[0,1],classes={'cnn':[2,3]})
    r=m.score_rows([row],'cnn',6);assert r['localization']['tp']==2 and r['two_class_macro_f1']==1 and r['per_image'][0]['pred_fraction']==.5


def test_registry_refuses_duplicated_or_unplanned_external_names():
    m=module();names=[f'DeepLIIF_Testing_Set/Lung_{i}.png' for i in range(597)];probe='DeepLIIF_Testing_Set/probe.png'
    p=dict(included_names=names,excluded_format_probe=probe,image_count=597)
    index=dict(entries=[dict(name=n) for n in [*names,probe]])
    assert len(m.validate_membership(p,index))==597
    index['entries'].append(dict(name=names[0]))
    with pytest.raises(ValueError):m.validate_membership(p,index)
    index['entries'].pop();p['included_names'][0]='unplanned.png'
    with pytest.raises(ValueError):m.validate_membership(p,index)
