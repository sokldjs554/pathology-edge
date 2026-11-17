"""Read original bytes strictly and bind selected ranges to a whole-file hash."""
import hashlib
import io
import math
import re


class SourceDigestMismatch(ValueError):
    def __init__(self, observed, expected):
        super().__init__('Original MD5 differs from published reference')
        self.observed, self.expected = observed, expected


def validate_source_item(item):
    """A case ID alone does not identify a slide; require exact DX1 identity."""
    dsa, gdc = item['dsa_files'], item['gdc_matching']
    if len(dsa)!=1 or len(gdc)>1:
        raise ValueError('One original file and at most one exact GDC match required')
    file = dsa[0]
    if not file['name'].startswith(item['case_id']+'-') or '-DX1.' not in file['name'] or file['size']<=0:
        raise ValueError('Original does not match the specified DX1 case')
    if gdc and (gdc[0]['file_name']!=file['name'] or gdc[0]['file_size']!=file['size']
                or gdc[0]['access']!='open' or not re.fullmatch('[0-9a-f]{32}',gdc[0]['md5sum'])):
        raise ValueError('GDC and mirror original identities differ')


class RangeReader(io.RawIOBase):
    """Seekable cached HTTP reader for public original files, not rendered tiles."""

    def __init__(self, url, size, *, get=None, block_size=1024*1024, allow_unitless_range=False):
        if not isinstance(size, int) or size <= 0 or not isinstance(block_size, int) or block_size <= 0:
            raise ValueError('Positive integer size and block size required')
        if get is None:
            import requests
            get = requests.get
        self.url, self.size, self.get, self.block_size = url, size, get, block_size
        self.position, self.blocks, self.name = 0, {}, 'original.svs'
        self.allow_unitless_range = allow_unitless_range

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=io.SEEK_SET):
        if whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END):
            raise ValueError('Invalid seek mode')
        new = offset + (0 if whence == io.SEEK_SET else self.position if whence == io.SEEK_CUR else self.size)
        if not isinstance(new, int) or new < 0:
            raise ValueError('Invalid seek position')
        self.position = new
        return new

    def read(self, size=-1):
        end = self.size if size < 0 else min(self.size, self.position+size)
        chunks = []
        while self.position < end:
            start = self.position//self.block_size*self.block_size
            stop = min(self.size, start+self.block_size)
            if start not in self.blocks:
                r = self.get(self.url, headers={'Range': f'bytes={start}-{stop-1}',
                                               'Accept-Encoding': 'identity'}, timeout=(10, 45))
                r.raise_for_status()
                ranges = {f'bytes {start}-{stop-1}/{self.size}'}
                if self.allow_unitless_range:
                    ranges.add(f'{start}-{stop-1}/{self.size}')
                if (r.status_code != 206 or r.headers.get('Content-Range') not in ranges
                        or len(r.content) != stop-start):
                    raise ValueError('Server did not return the exact requested original byte range')
                self.blocks[start] = r.content
            take = min(end, stop)
            chunks.append(self.blocks[start][self.position-start:take-start])
            self.position = take
        return b''.join(chunks)


def verify_stream(chunks, expected_size, blocks, expected_md5=None):
    """Check all original bytes and every previously fetched range without a disk copy.

    `blocks` maps absolute byte offsets to fetched bytes. Overlaps are allowed.
    The stream may be arbitrarily chunked. No digest implies a reference match
    unless expected_md5 was supplied and verified.
    """
    md5, sha = hashlib.md5(), hashlib.sha256()
    position = 0
    checked = {offset: 0 for offset in blocks}
    if any(offset < 0 or not data or offset+len(data) > expected_size for offset, data in blocks.items()):
        raise ValueError('Invalid cached range')
    for chunk in chunks:
        end = position+len(chunk)
        if end > expected_size:
            raise ValueError('Original stream exceeds expected size')
        md5.update(chunk); sha.update(chunk)
        for offset, data in blocks.items():
            left, right = max(position, offset), min(end, offset+len(data))
            if left < right:
                if chunk[left-position:right-position] != data[left-offset:right-offset]:
                    raise ValueError('Range bytes differ from original stream')
                checked[offset] += right-left
        position = end
    if position != expected_size or any(checked[o] != len(d) for o, d in blocks.items()):
        raise ValueError('Original stream truncated or ranges not fully compared')
    result = dict(bytes=position, md5=md5.hexdigest(), sha256=sha.hexdigest(),
                  reference_md5_verified=expected_md5 is not None and md5.hexdigest()==expected_md5,
                  verified_ranges=len(blocks), verified_range_bytes=sum(checked.values()))
    if expected_md5 is not None and md5.hexdigest() != expected_md5:
        raise SourceDigestMismatch(result, expected_md5)
    return result


def decode_tiled_roi(page, reader, bounds):
    """Decode intersecting TIFF tiles only; return native RGB and tile indices.

    Caller supplies a tifffile page. No resizing, color profile, translation or
    annotation-driven registration is performed here. Bounds are half-open.
    """
    import numpy as np
    left, top, right, bottom = bounds
    if (not page.is_tiled or page.samplesperpixel != 3 or page.dtype != np.dtype('uint8')
            or page.planarconfig != 1 or any(not isinstance(v, int) for v in bounds)
            or not (0 <= left < right <= page.imagewidth and 0 <= top < bottom <= page.imagelength)):
        raise ValueError('Expected in-bounds integer crop of contiguous tiled RGB uint8 TIFF')
    output = np.empty((bottom-top, right-left, 3), np.uint8)
    across = math.ceil(page.imagewidth/page.tilewidth)
    indices = []
    for ty in range(top//page.tilelength, (bottom-1)//page.tilelength+1):
        for tx in range(left//page.tilewidth, (right-1)//page.tilewidth+1):
            index = ty*across+tx
            reader.seek(page.dataoffsets[index])
            raw = reader.read(page.databytecounts[index])
            if len(raw) != page.databytecounts[index]:
                raise ValueError('Truncated TIFF tile')
            tile, location, _ = page.decode(raw, index, jpegtables=page.jpegtables)
            y, x = ty*page.tilelength, tx*page.tilewidth
            if tile is None or tuple(location) != (0, 0, y, x, 0):
                raise ValueError('Unexpected TIFF tile coordinates')
            x0, x1, y0, y1 = max(left,x), min(right,x+page.tilewidth), max(top,y), min(bottom,y+page.tilelength)
            output[y0-top:y1-top,x0-left:x1-left] = tile[0,y0-y:y1-y,x0-x:x1-x,:]
            indices.append(index)
    return output, indices
