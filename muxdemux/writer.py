import cbor
import hashlib
import logging
import zlib

from .common import *  # NOQA

LOG = logging.getLogger(__name__)

default_hashalgo = 'sha256'

state_bos = 0
state_metadata = 1
state_data = 2
state_eos = 3


class MuxError(Exception):
    pass


class InvalidState(MuxError):
    pass


class StreamWriter(object):
    '''Writes one part to a mux stream.

    A mux stream is a series for cbor-encoded dictionaries.  Each
    chunk has a 'type' attribute that identifies the chunk type.  A
    part has the following format:

        +----------------------------------------+
        | beginning-of-stream | blktype_bos      |
        +----------------------------------------+
        | metadata (optional) | blktype_metadata |
        +----------------------------------------+
        | data0               | blktype_data     |
        .                                        .
        .                                        .
        | dataN               | blktype_data     |
        +----------------------------------------+
        | end-of-stream       | blktype_eos      |
        +----------------------------------------+

    Multiple parts may be concatenated to form a stream.
    '''

    def __init__(self, fh,
                 name=None, hashalgo=None, writehash=False,
                 compress=False):
        self.fh = fh
        self.name = name
        self.hashalgo = hashalgo if hashalgo else default_hashalgo
        self.writehash = writehash
        self.compress = compress
        self.state = state_bos
        self.metadata = {}
        self.byteswritten = 0

        if self.writehash:
            self.ctx = self._get_hash_context()

    def _write_header(self):
        '''Writes out a header block.  The header block contains
        information about the stream:

        - version: the mux format version
        - name (optional): name of this stream
        - hashalgo (optional): hash algorithm used for checksums
        - compress (optional): true if data is compressed
        '''
        if self.state != state_bos:
            raise InvalidState()

        header = {'version': mux_version}
        if self.name:
            header['name'] = self.name
        if self.writehash:
            header['hashalgo'] = self.hashalgo
        if self.compress:
            header['compress'] = True

        self._write_block(blktype_bos, **header)
        self.state = state_metadata

    def _write_metadata(self):
        '''Writes out a metadata block.  A metadata block can
        contains arbitrary key/value pairs in the 'metadata' key.'''

        if self.state != state_metadata:
            raise InvalidState()

        if self.metadata:
            self._write_block(blktype_metadata,
                              metadata=self.metadata)

        self.state = state_data

    def _write_block(self, blktype, **kwargs):
        LOG.debug('writing block: type=%s, content=%s',
                  blktype, repr(kwargs))

        cbor.dump(dict(blktype=blktype, **kwargs), self.fh)

    def _get_hash_context(self):
        return getattr(hashlib, self.hashalgo)()

    def add_metadata(self, k, v):
        self.metadata[k] = v

    def write(self, data):
        '''Write a data block to the mux stream.'''

        # Write out the header if we haven't already.
        if self.state == state_bos:
            self._write_header()

        # Write out the metadata if we haven't already.
        if self.state == state_metadata:
            self._write_metadata()

        # Blow up if something is wrong.
        if self.state != state_data:
            raise InvalidState()

        if self.compress:
            data = zlib.compress(data)

        if self.writehash:
            self.ctx.update(data)

        self.byteswritten += len(data)
        self._write_block(blktype_data, data=data)

    def write_iter(self, data):
        '''Write data blocks to the mux stream from an iterator.'''

        for chunk in data:
            self.write(chunk)

    def finish(self):
        '''Close the stream by writing an end-of-stream block.'''

        if self.state == state_bos:
            self._write_header()

        if self.state == state_metadata:
            self._write_metadata()

        if self.state != state_data:
            raise InvalidState()

        hashargs = {}

        if self.writehash:
            hashargs['digest'] = self.ctx.digest()

        self._write_block(blktype_eos,
                          size=self.byteswritten,
                          **hashargs)

        self.state = state_eos
