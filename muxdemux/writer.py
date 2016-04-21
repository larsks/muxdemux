import cbor
import hashlib
import logging

from .common import *  # NOQA

LOG = logging.getLogger(__name__)

default_hashalgo = 'sha256'
mux_version = 1

state_bos = 0
state_metadata = 1
state_data = 2
state_eos = 3


class MuxError(Exception):
    pass


class InvalidState(MuxError):
    pass


class StreamWriter(object):
    def __init__(self, stream,
                 name=None, hashalgo=None, writehash=False):
        self.stream = stream
        self.name = name
        self.hashalgo = hashalgo if hashalgo else default_hashalgo
        self.writehash = writehash
        self.state = state_bos
        self.metadata = {}
        self.byteswritten = 0

        if self.writehash:
            self.ctx = self._get_hash_context()

    def _write_header(self):
        if self.state != state_bos:
            raise InvalidState()

        header = {'version': mux_version}
        if self.name:
            header['name'] = self.name
        if self.writehash:
            header['hashalgo'] = self.hashalgo

        self._write_block(blktype_bos, **header)
        self.state = state_metadata

    def _write_metadata(self):
        if self.state != state_metadata:
            raise InvalidState()

        if self.metadata:
            self._write_block(blktype_metadata,
                              metadata=self.metadata)

        self.state = state_data

    def _write_block(self, blktype, **kwargs):
        LOG.debug('writing block: type=%s, content=%s',
                  blktype, repr(kwargs))

        cbor.dump(dict(blktype=blktype, **kwargs), self.stream)

    def _get_hash_context(self):
        return getattr(hashlib, self.hashalgo)()

    def add_metadata(self, k, v):
        self.metadata[k] = v

    def write(self, data):
        if self.state == state_bos:
            self._write_header()

        if self.state == state_metadata:
            self._write_metadata()

        if self.state != state_data:
            raise InvalidState()

        if self.writehash:
            self.ctx.update(data)

        self.byteswritten += len(data)
        self._write_block(blktype_data, data=data)

    def write_iter(self, data):
        for chunk in data:
            self.write(chunk)

    def finish(self):
        if self.state != state_data:
            raise InvalidState()

        hashargs = {}

        if self.writehash:
            hashargs['digest'] = self.ctx.digest()

        self._write_block(blktype_eos,
                          size=self.byteswritten,
                          **hashargs)

        self.state = state_eos
