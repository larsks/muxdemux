This project implements a set of tools for multiplexing several chunks
of data together in a single stream, and then taking them apart again.
This project consists of two commands, `mux` and `demux`.

## Mux

    usage: mux [-h] [--blocksize BLOCKSIZE] [--checksum] [--hashalgo HASHALGO]
               [--name NAME] [--metadata METADATA] [--verbose] [--debug]
               [path]

The `mux` commands reads from `stdin` or from a single optional path,
and produces a `mux` stream on `stdout`.  You can concatenate multiple
`mux` strings together and feed them to the `demux` command.

## Demux

    usage: demux [-h] [--output-template OUTPUT_TEMPLATE] [--stdout] [--list]
                 [--verify] [--verbose] [--debug]
                 [streams [streams ...]]


The `demux` command reads a `mux` stream on `stdin` and by default
will extract each stream to a file named `stram-<N>.out`, where `<N>`
is the index of the stream.

## Examples

The following will run `ps -fe`, `ip addr` and `ip route` on the
remote system, producing a mux stream from the `stdout` of each
process.  We pass this to `demux` on the localhost, producing three
files containing the output:

    $ ssh remote.example.com 'ps -fe | mux; ip addr | mux; ip route | mux' |
      demux -o remote-info-{strno}.txt

    $ ls
    remote-info-0.txt
    remote-info-1.txt
    remote-info-2.txt

It is also possible to assign names to streams:

    $ ssh remote.example.com 'ps -fe | mux -n ps; ip addr | mux -n interfaces' |
      demux -o remote-{name}.txt
    $ ls
    remote-ps.txt
    remote-interfaces.txt

You can list the contents of a mux stream:

    $ ssh remote.example.com 'ps -fe | mux -n ps; ip addr | mux -n interfaces' > remote.mux
    $ demux -l < remote.mux
    [0]: size=47058, name=ps
    [1]: size=6373, name=interfaces

And you can extract only selected streams, using either stream indexes:

    $ demux -v 1 < remote.mux
    INFO:demux:processing stream 1 to stream-1.out
    $ ls
    stream-1.out

Or names:

    $ demux -v interfaces < remote.mux
    INFO:demux:processing stream 1 to stream-1.out
    $ ls
    stream-1.out

You can compute a checksum for each input to ensure data integrity by
adding `-k` to the `mux` command:

    $ echo hello world | mux -k | demux -v --stdout
    INFO:demux:processing stream 0 to <stdout>
    hello world
    INFO:muxdemux.reader:integrity check successful

## Stream format

`mux` encodes streams by wrapping the input in [cbor][] encoded
chunks.  A stream has the following format:

[cbor]: http://cbor.io/

    +----------------------+
    | Beginning Of Stream  |
    +----------------------+
    |  Metadata (optional) |
    +----------------------+
    |      Data 0          |
    +----------------------+
    |      Data 1          |
    +----------------------+
    |                      |
    //      ...           //
    |                      |
    +----------------------+
    |      Data N          |
    +----------------------+
    |     End of Stream    |
    +----------------------+

