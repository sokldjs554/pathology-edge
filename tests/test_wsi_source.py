import hashlib
import io

import pytest

from pathology_edge.wsi_source import RangeReader, verify_stream


class Response:
    def __init__(self, data, status, content_range=None):
        self.content = data
        self.status_code = status
        self.headers = {} if content_range is None else {'Content-Range': content_range}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError('HTTP failure')


def fake_get(data, damage=None):
    def get(url, headers, timeout):
        start, end = map(int, headers['Range'][6:].split('-'))
        raw = data[start:end+1]
        return Response(raw[:-1] if damage == 'truncated' else raw,
                        200 if damage == 'ignored_range' else 206,
                        'bytes 1-2/3' if damage == 'wrong_range' else f'bytes {start}-{end}/{len(data)}')
    return get


def test_range_seek_cross_block_and_stream_digest():
    data = bytes(range(101))
    r = RangeReader('unused', len(data), get=fake_get(data), block_size=16)
    r.seek(13)
    assert r.read(28) == data[13:41]
    r.seek(-5, io.SEEK_END)
    assert r.read() == data[-5:]
    result = verify_stream((data[i:i+7] for i in range(0,len(data),7)), len(data), r.blocks,
                           hashlib.md5(data).hexdigest())
    assert result['sha256'] == hashlib.sha256(data).hexdigest()
    assert result['verified_ranges'] == len(r.blocks)


@pytest.mark.parametrize('damage', ['ignored_range', 'wrong_range', 'truncated'])
def test_invalid_http_range_is_not_accepted(damage):
    r = RangeReader('unused', 20, get=fake_get(bytes(range(20)), damage), block_size=8)
    with pytest.raises(ValueError):
        r.read(1)


@pytest.mark.parametrize('damage', ['short', 'long', 'changed_block', 'bad_md5'])
def test_original_stream_must_match_size_digest_and_each_cached_block(damage):
    raw = b'0123456789'
    data = raw[:-1] if damage=='short' else raw+b'0' if damage=='long' else raw
    blocks = {2: b'XX45' if damage=='changed_block' else b'2345'}
    md5 = '0'*32 if damage=='bad_md5' else hashlib.md5(raw).hexdigest()
    with pytest.raises(ValueError):
        verify_stream([data], 10, blocks, md5)


def test_tiled_roi_handles_partial_tiles_and_does_not_read_unneeded_tiles():
    import numpy as np
    from pathology_edge.wsi_source import decode_tiled_roi
    source = np.arange(5*7*3, dtype=np.uint8).reshape(5, 7, 3)
    chunks = []
    for y in range(0,5,4):
        for x in range(0,7,4):
            tile = np.zeros((4,4,3),np.uint8)
            part=source[y:y+4,x:x+4];tile[:part.shape[0],:part.shape[1]]=part
            chunks.append(tile.tobytes())
    class Page:
        is_tiled=True; imagewidth=7; imagelength=5; tilewidth=4; tilelength=4
        samplesperpixel=3; dtype=np.dtype('uint8'); planarconfig=1
        jpegtables=None; dataoffsets=[0,48,96,144]; databytecounts=[48]*4
        def decode(self, raw, index, jpegtables=None):
            return np.frombuffer(raw,np.uint8).reshape(1,4,4,3), (0,0,index//2*4,index%2*4,0), (1,4,4,3)
    image, indices = decode_tiled_roi(Page(),io.BytesIO(b''.join(chunks)), (3,1,7,5))
    assert np.array_equal(image,source[1:5,3:7]) and indices == [0,1,2,3]
    image, indices = decode_tiled_roi(Page(),io.BytesIO(b''.join(chunks)), (4,0,7,3))
    assert np.array_equal(image,source[:3,4:7]) and indices == [1]


def test_digest_failure_retains_observed_hashes_without_claiming_reference_match():
    from pathology_edge.wsi_source import SourceDigestMismatch
    with pytest.raises(SourceDigestMismatch) as error:
        verify_stream([b'abc'],3,{0:b'abc'},'0'*32)
    assert error.value.observed['md5']==hashlib.md5(b'abc').hexdigest()
    assert error.value.observed['reference_md5_verified'] is False


def test_unitless_content_range_requires_explicit_gdc_compatibility_flag():
    def get(url,headers,timeout):
        return Response(b'abc',206,'0-2/3')
    with pytest.raises(ValueError):
        RangeReader('unused',3,get=get).read()
    assert RangeReader('unused',3,get=get,allow_unitless_range=True).read()==b'abc'


@pytest.mark.parametrize('damage',['duplicate_dsa','duplicate_gdc','different_name','different_size'])
def test_source_catalog_requires_one_exact_slide_identity(damage):
    from pathology_edge.wsi_source import validate_source_item
    dsa=dict(name='TCGA-A2-A0ST-01Z-00-DX1.test.svs',size=100)
    gdc=dict(file_name=dsa['name'],file_size=100,access='open',md5sum='a'*32)
    item=dict(case_id='TCGA-A2-A0ST',dsa_files=[dsa],gdc_matching=[gdc])
    if damage=='duplicate_dsa':item['dsa_files'].append(dsa.copy())
    if damage=='duplicate_gdc':item['gdc_matching'].append(gdc.copy())
    if damage=='different_name':gdc['file_name']='TCGA-A2-A0ST-01A-01-TS1.other.svs'
    if damage=='different_size':gdc['file_size']=101
    with pytest.raises(ValueError):validate_source_item(item)
