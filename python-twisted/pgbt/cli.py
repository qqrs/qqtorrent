from client import PgbtClient


def main():
    client = PgbtClient()
    client.add_torrent('../shared/flagfromserver.torrent')

if __name__ == '__main__':
    main()
