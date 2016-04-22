import cbor
import hashlib
import logging
import zlib

from .common import *  # NOQA

LOG = logging.getLogger(__name__)


class DemuxError(Exception):
    pass


class InvalidBlock(DemuxError):
    pass


class IntegrityError(DemuxError):
    pass


def cbor_iter(data):
    while True:
        try:
            obj = cbor.load(data)
            yield obj
        except EOFError:
            break


def hexify(s):
    return ''.join('%02x' % ord(x) for x in s)


class FileReader(object):
    def __init__(self, bos, fileiter):
        self.bos = bos
        self.fileiter = fileiter
        self.eos = {}
        self.metadata = {}
        self.ctx = None

        if 'hashalgo' in bos:
            self.ctx = getattr(hashlib, bos['hashalgo'])()

    def __iter__(self):
        compressed = self.bos.get('compress')

        for block in self.fileiter:
            if block['blktype'] == blktype_data:
                if self.ctx is not None:
                    self.ctx.update(block['data'])

                if compressed:
                    yield zlib.decompress(block['data'])
                else:
                    yield block['data']
            elif block['blktype'] == blktype_metadata:
                self.metadata = block['metadata']
            elif block['blktype'] == blktype_eos:
                self.eos = block
                if self.ctx is not None:
                    if self.ctx.digest() != self.eos['digest']:
                        raise IntegrityError('invalid checksum')
                    else:
                        LOG.info('integrity check successful')
                break
            else:
                raise InvalidBlock('expected <data>, <metadata>, or <eos>, '
                                   'got {blktype}'.format(**block))


class StreamReader(object):
    def __init__(self, stream):
        self.stream = stream

    def __iter__(self):
        blocks = cbor_iter(self.stream)
        stream = 0

        for block in blocks:
            if block['blktype'] == blktype_bos:
                LOG.debug('reading from stream %d', stream)
                yield FileReader(block, blocks)
                stream += 1
            else:
                raise InvalidBlock('expected <bos>, '
                                   'got {blktype}'.format(**block))
