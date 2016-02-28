import sys
import argparse

from pgbt.client import PgbtClient


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('torrent', help='.torrent metainfo file')
    parser.add_argument('--hello', default=False, action='store_true')
    #parser.add_argument('--commit', default=False, action='store_true',
                        #help='commit the changes')
    args = parser.parse_args(argv)

    if (args.hello):
        print('hello')
        return

    client = PgbtClient()
    client.add_torrent(args.torrent)


if __name__ == '__main__':
    sys.exit(main())
