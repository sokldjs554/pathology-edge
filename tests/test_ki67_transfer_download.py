import importlib
import io
import zipfile
import urllib.error
import pytest


def api():return importlib.import_module('pathology_edge.ki67_transfer_download')


def fixture():
    f=io.BytesIO()
    with zipfile.ZipFile(f,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('test.png',b'pixels'*100)
    raw=f.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        i=z.infolist()[0];entry=dict(name=i.filename,offset=i.header_offset,compressed_bytes=i.compress_size,uncompressed_bytes=i.file_size,crc32=i.CRC,method=i.compress_type)
    return raw,entry


def test_one_request_crc_verified_entry(monkeypatch):
    m=api();raw,e=fixture();calls=[]
    def read(url,lo,hi,total):calls.append((lo,hi));return raw[lo:hi+1]
    monkeypatch.setattr(m,'read_range',read)
    data,meta=m.fetch_entry_once('https://example.invalid',e,len(raw))
    assert data==b'pixels'*100 and len(calls)==1 and meta['crc32']==e['crc32']
    bad={**e,'crc32':0}
    with pytest.raises(ValueError):m.fetch_entry_once('x',bad,len(raw))


def test_retry_after_is_honored_without_real_wait(monkeypatch):
    m=api();calls=[];sleeps=[]
    def fetch(*args):
        calls.append(1)
        if len(calls)==1:raise urllib.error.HTTPError('x',429,'rate limited',{'Retry-After':'75'},None)
        return b'ok',{}
    monkeypatch.setattr(m,'fetch_entry_once',fetch);monkeypatch.setattr(m.time,'sleep',sleeps.append)
    assert m.download('x',{},100)==(b'ok',{})
    assert sum(sleeps)>=75 and max(sleeps)<=30 and len(calls)==2


def test_bad_crc_is_not_retried(monkeypatch):
    m=api();calls=[]
    def fetch(*args):calls.append(1);raise ValueError('CRC mismatch')
    monkeypatch.setattr(m,'fetch_entry_once',fetch)
    with pytest.raises(ValueError):m.download('x',{},100)
    assert len(calls)==1


def test_every_request_attempt_and_next_entry_keep_two_second_spacing(monkeypatch):
    m=api();clock=[0.];starts=[]
    monkeypatch.setattr(m.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(m.time,'sleep',lambda seconds:clock.__setitem__(0,clock[0]+seconds))
    monkeypatch.setattr(m,'_last_request_start',-float('inf'),raising=False)
    def fetch(*args):
        starts.append(clock[0])
        if len(starts)==1:raise urllib.error.HTTPError('x',429,'limited',{'Retry-After':'1'},None)
        return b'ok',{}
    monkeypatch.setattr(m,'fetch_entry_once',fetch)
    m.download('x',{},100);m.download('x',{},100)
    assert len(starts)==3 and all(b-a>=2 for a,b in zip(starts,starts[1:]))
