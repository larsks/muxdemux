#!/usr/bin/env python

import sys
import argparse
import logging

from muxdemux.writer import StreamWriter

LOG = logging.getLogger('mux')


def chunker(fd, blocksize):
    while True:
        data = fd.read(blocksize)
        if not data:
            break

        yield data


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--blocksize', '-b',
                   default=1024,
                   type=int)
    p.add_argument('--checksum', '-k',
                   action='store_true')
    p.add_argument('--compress', '-z',
                   action='store_true')

    p.add_argument('--hashalgo', '-H')
    p.add_argument('--name', '-n')

    p.add_argument('--metadata', '-m',
                   action='append',
                   type=lambda x: x.split('=', 1),
                   default=[])

    p.add_argument('--verbose', '-v',
                   action='store_const',
                   dest='loglevel',
                   const='INFO')
    p.add_argument('--debug',
                   action='store_const',
                   dest='loglevel',
                   const='DEBUG')

    p.set_defaults(loglevel='WARNING')

    p.add_argument('path', nargs='?')

    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel)

    kwargs = {}
    if args.name:
        kwargs['name'] = args.name
    elif args.path:
        kwargs['name'] = args.path

    if args.checksum:
        kwargs['writehash'] = True
        kwargs['hashalgo'] = args.hashalgo

    if args.compress:
        kwargs['compress'] = True

    writer = StreamWriter(sys.stdout, **kwargs)
    for k, v in args.metadata:
        writer.add_metadata(k, v)

    with (open(args.path) if args.path else sys.stdin) as fd:
        writer.write_iter(chunker(fd, args.blocksize))

    writer.finish()


if __name__ == '__main__':
    main()
