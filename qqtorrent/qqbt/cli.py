"""Command-line interface entry point."""
import sys
import argparse
import logging

from qqbt.client import QqbtClient


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('torrent', help='.torrent metainfo file')
    parser.add_argument('-t', '--torrent2',
                        help='other .torrent metainfo file')
    parser.add_argument('--outdir', type=str, help='output directory')
    parser.add_argument('--hello', default=False, action='store_true')
    parser.add_argument('--verbose', '-v', default=False, action='store_true')
    args = parser.parse_args(argv)

    if (args.hello):
        print('hello')
        return

    if (args.verbose):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    client = QqbtClient(outdir=args.outdir)
    client.add_torrent(args.torrent)
    if args.torrent2:
        client.add_torrent(args.torrent2)
    client.start_torrents()


if __name__ == '__main__':
    main()
