#!/usr/bin/env python

import sys
import argparse
import logging
import contextlib

from muxdemux.reader import StreamReader, IntegrityError

LOG = logging.getLogger('demux')


@contextlib.contextmanager
def output_handler(filename, use_stdout=False):
    if use_stdout:
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


def consume(stream):
    '''Consume a stream, returning False if there is an integrity 
    failure, True otherwise.'''

    try:
        for chunk in stream:
            pass
        return True
    except IntegrityError:
        return False


def main():
    args = parse_args()
    logging.basicConfig(level=args.loglevel)
    reader = StreamReader(sys.stdin)

    for strno, stream in enumerate(reader):
        if args.list:
            valid = consume(stream)
            print '[%03d]: size=%d, name=%s, hashalgo=%s, valid=%s' % (
                strno, stream.eos['size'],
                stream.bos.get('name', '(none)'),
                stream.bos.get('hashalgo', '(none)'),
                valid,
            )
            if stream.metadata:
                for k, v in stream.metadata.items():
                    print '       %s = %s' % (k, v)
            continue

        # Figure out if we want to write out this stream or not.
        if str(strno) in args.streams:
            skip = False
        elif 'name' in stream.bos and stream.bos['name'] in args.streams:
            skip = False
        elif not args.streams:
            skip = False
        else:
            skip = True

        # If we're skipping the stream, we still need to consume
        # all the data.
        if skip:
            consume(stream)
            continue

        name = stream.bos.get('name', 'stream%d' % strno)
        output_name = ('<stdout>' if args.stdout
                       else args.output_template.format(
                           strno=strno, name=name))

        LOG.info('writing stream %d%s to %s',
                 strno,
                 (' (name=%s)' % name if name else ''),
                 output_name)

        try:
            with output_handler(output_name, args.stdout) as fd:
                for chunk in stream:
                    fd.write(chunk)
        except IntegrityError as err:
            if skip or args._continue:
                LOG.warning('integrity check failed on stream {}: {}'.format(
                    strno, err))
            else:
                raise


if __name__ == '__main__':
    main()
