#!/usr/bin/env python

import sys
import argparse
import logging
import contextlib

from muxdemux.reader import StreamReader, IntegrityError

LOG = logging.getLogger('demux')


@contextlib.contextmanager
def output_handler(filename=None):
    if not filename or filename == '-':
        fd = sys.stdout
    else:
        fd = open(filename, 'w')

    try:
        yield fd
    finally:
        if fd is not sys.stdout:
            fd.close()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--output-template', '-o',
                   default='stream-{strno}.out')
    p.add_argument('--stdout',
                   action='store_true')
    p.add_argument('--list', '-l',
                   action='store_true')
    p.add_argument('--continue', '-c',
                   dest='_continue',
                   action='store_true')

    p.add_argument('--verbose', '-v',
                   action='store_const',
                   dest='loglevel',
                   const='INFO')
    p.add_argument('--debug',
                   action='store_const',
                   dest='loglevel',
                   const='DEBUG')

    p.add_argument('streams',
                   nargs='*')

    p.set_defaults(loglevel='WARNING')

    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel)

    strno = 0
    s = StreamReader(sys.stdin)

    for stream in s:
        if args.list:
            skip = True
        elif str(strno) in args.streams:
            skip = False
        elif 'name' in stream.bos and stream.bos['name'] in args.streams:
            skip = False
        elif not args.streams:
            skip = False
        else:
            skip = True

        try:
            if skip:
                for chunk in stream:
                    pass
            else:
                name = stream.bos.get('name', 'stream%d' % strno)
                output_name = ('<stdout>' if args.stdout
                               else args.output_template.format(
                                   strno=strno, name=name))

                LOG.info('processing stream %d to %s', strno, output_name)
                with output_handler(None if args.stdout else output_name) as fd:
                    for chunk in stream:
                        fd.write(chunk)
        except IntegrityError as err:
            if skip or args._continue:
                LOG.warning('integrity check failed on stream {}: {}'.format(
                    strno, err))
            else:
                raise

        if args.list:
            print '[%d]: size=%d, name=%s' % (
                strno, stream.eos['size'], stream.bos.get('name', '(none)'))
        strno += 1

if __name__ == '__main__':
    main()
