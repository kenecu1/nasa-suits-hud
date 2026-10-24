import json
import logging
import socket
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bridge")

CONFIG_PATH = Path(__file__).parent / "config.json"   # config.json next to this script
def load_config():
    if not CONFIG_PATH.exists():
        sys.exit("Missing bridge/config.json. Copy config.example.json and fill in your TSS IP.")
    with open(CONFIG_PATH) as f:
        return json.load(f)

def poll_once(sock, address):
    request = bytearray([0,0,0,0,0,0,0,0])
    sock.sendto(request, address)
    reply = sock.recv(9999)
    data = json.loads(reply.decode(errors='replace'))
    
    return data


if __name__ == "__main__":
    config = load_config()
    server_address = (config["tss_ip"], 14142 + config['tss_team'])

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 0))
    sock.settimeout(config['timeout_seconds'])   # time out after n secs of not receiving data

    last_data = None
    last_time = None
    connected = False
    while True:        
        try:
            data = poll_once(sock, server_address)
            data['telemetry']['oxy_pri_storage']    # check the data in reply has expected shape
        except OSError as e:
            connected = False
            log.warning("Connection lost: {}".format(e))
        except (ValueError, TypeError, KeyError) as e:
            connected = False
            log.warning(f"Bad data format from TSS: {e!r}")
        else:
            # only when the poll worked AND data looks correct
            last_data = data
            last_time = time.time()
            connected = True


        if last_data is None:
            log.warning(f"connected={connected}; no data yet")
        else:
            age = time.time() - last_time
            o2 = last_data['telemetry']['oxy_pri_storage']
            log.info(f"connected={connected}   age={age:.1f}s   O2={o2:.2f}%")

        time.sleep(1)
