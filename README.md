A command-line Python BitTorrent client supporting concurrent peer connections and multiple simultaneous torrent downloads.

Since the project was mainly an exercise to explore concurrent networking concepts, it includes three entirely separate implementations for managing the peer network connections:  
1. using a custom event loop with select/kqueue/epoll (via the Python selectors module)  
2. using Twisted, which is a library that provides everything in (1)  
3. using threads, with a separate thread for each connection to handle the
    blocking I/O, and the event loop reading back results through queues  

If you are thinking about writing a BitTorrent client yourself, see my blog post: http://blog.qqrs.us/blog/2016/05/22/writing-a-bittorrent-client/

## Overview

`cli.py`: Command-line interface entry point.

`client.py`: BitTorrent client class. Provides an interface to all operations needed to start, run, or a complete a torrent. All CLI or GUI entry points interface only with this class, and all file operations happen only within this class.

`config.py`: Configuration parameters.

`torrent.py`: A torrent to be downloaded/uploaded. Maintains state related to the torrent and coordinates operations needed for the download.

`tracker.py`: A tracker connection for a torrent. Makes the announce request to the tracker and decodes the response.

`torrent_metainfo.py`: A torrent metainfo file. Decodes the contents of a `.torrent` file.

`peer.py`: A peer available for download/upload of a torrent. Maintains state related to the peer and encodes/decodes peer protocol messages.

`conn.py`: An event loop for managing concurrent peer network connections.


## Setup

```
cd qqtorrent/qqtorrent
mkvirtualenv -p python3 qqbt
pip install -r requirements.txt
python setup.py develop
```

## Tests

```
nosetests
```


## Usage

```
workon qqbt
python qqbt/cli.py ../shared/<torrent_name>.torrent
```


## Example
```
$ python qqbt/cli.py ../shared/flagfromserver.torrent -v
INFO:requests.packages.urllib3.connectionpool:Starting new HTTP connection (1)
DEBUG:requests.packages.urllib3.connectionpool:"GET /announce?peer_id=QQ-0000-000000000000&uploaded=0&left=1277987&port=6881&downloaded=0&info_hash=%2B%15%CA%2B%FDH%CD%D7m9%ECU%A3%AB%1B%8AW%18%0A%09 HTTP/1.1" 200 105
DEBUG:qqbt.conn:PeerConnectionSelect.__init__: TorrentPeer(ip=<redacted>, port=6881)
INFO:qqbt.peer:TorrentPeer(ip=<redacted>, port=6881): handle_connection_failed
DEBUG:qqbt.conn:PeerConnectionSelect.__init__: TorrentPeer(ip=<redacted>, port=64173)
INFO:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): handle_connection_made
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_handshake
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): received_handshake
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=interested params={}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=5 type=bitfield payload=EF7FFDFBFFB7FFBFFFFE
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=00000003
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=00000008
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=00000016
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=0000001D
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=00000029
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=0000002C
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=4 type=have payload=00000039
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=1 type=unchoke payload=
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 0}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000000000000000FFD8FFE127AB4578696600004D4D002A00000008000A01120003000000010000...
DEBUG:qqbt.torrent:handle_completed_piece: 0
<qqbt.torrent.Torrent object at 0x101bac6a0>: 1 / 79 (1.3%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 1}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=000000010000000020E80BF1F99A68B4923FFFD3F7E91630096425C29C7CBDE98A76C8AB23200146...
DEBUG:qqbt.torrent:handle_completed_piece: 1
<qqbt.torrent.Torrent object at 0x101bac6a0>: 2 / 79 (2.5%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 2}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000000200000000700D3D4334822DD86503073D7348A11426E42463273C91FCA9C097549A257003...
DEBUG:qqbt.torrent:handle_completed_piece: 2
<qqbt.torrent.Torrent object at 0x101bac6a0>: 3 / 79 (3.8%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 3}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000000300000000007AFB9F6A732AC8CF049BC2A2957217691919183F4A7C2CC91CCD2ED668FF00...
DEBUG:qqbt.torrent:handle_completed_piece: 3
<qqbt.torrent.Torrent object at 0x101bac6a0>: 4 / 79 (5.1%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 4}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=000000040000000000CDDBE6E3F1C2F107ED55F063E2BDD59F803C57A1F8F3C29F10756BC8DEDBC3...
DEBUG:qqbt.torrent:handle_completed_piece: 4
<qqbt.torrent.Torrent object at 0x101bac6a0>: 5 / 79 (6.3%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 5}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000000500000000964202E082BF2E0818383F534299106C32B10C3721C74F6A744D236730974270...
DEBUG:qqbt.torrent:handle_completed_piece: 5
<qqbt.torrent.Torrent object at 0x101bac6a0>: 6 / 79 (7.6%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 6}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000000600000000F99B0411DFD69ECEBB55701423908C1720E71FE18A6C8373EDC82594E006E98E...
DEBUG:qqbt.torrent:handle_completed_piece: 6
...
<qqbt.torrent.Torrent object at 0x101bac6a0>: 74 / 79 (93.7%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 74}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000004A00000000000000285D2258052E4C5D285D2258052E4C5D3C0000005B5DD6589E2E535D5B...
DEBUG:qqbt.torrent:handle_completed_piece: 74
<qqbt.torrent.Torrent object at 0x101bac6a0>: 75 / 79 (94.9%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 75}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000004B0000000073175FEA3CDE734A73175FEA3CDE733C000000D9749C61543DE774D9749C6154...
DEBUG:qqbt.torrent:handle_completed_piece: 75
<qqbt.torrent.Torrent object at 0x101bac6a0>: 76 / 79 (96.2%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 76}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000004C0000000026BC39A43BCB28C326BC393C000000EF1E42145A14061EEF1E42145A14061E3C...
DEBUG:qqbt.torrent:handle_completed_piece: 76
<qqbt.torrent.Torrent object at 0x101bac6a0>: 77 / 79 (97.5%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 16384, 'begin': 0, 'index': 77}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000004D0000000017F914F50B21183C000000B717EF14F40BB217B717EF14F40BB2173C000000CA...
DEBUG:qqbt.torrent:handle_completed_piece: 77
<qqbt.torrent.Torrent object at 0x101bac6a0>: 78 / 79 (98.7%) complete
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): send_message: type=request params={'length': 35, 'begin': 0, 'index': 78}
DEBUG:qqbt.peer:TorrentPeer(ip=<redacted>, port=64173): receive_msg: id=7 type=piece payload=0000004E000000000000000000000000000000000000000000000000000000000000000000000000
DEBUG:qqbt.torrent:handle_completed_piece: 78
<qqbt.torrent.Torrent object at 0x101bac6a0>: 79 / 79 (100.0%) complete
INFO:qqbt.torrent:<qqbt.torrent.Torrent object at 0x101bac6a0>: handle_completed_torrent
Torrent completed!
INFO:qqbt.client:save_single_file: flag.jpg
```
