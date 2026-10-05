import socket
import time
import json
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"Provide TSS IP. Format: python3 tss_client.py <TSS IP>")
    
    SERVER_IP = sys.argv[1]     # Server IP
    PORT = 14142   # for the first team

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 0))
    sock.settimeout(2)   # time out after 2 secs of not receiving data
    server_address = (SERVER_IP, PORT)

    while True:
        request = bytearray([0,0,0,0,0,0,0,0])
        try:
            sock.sendto(request, server_address)
            reply = sock.recv(9999)
            data = json.loads(reply.decode(errors='replace'))
            o2_val = data['telemetry']['oxy_pri_storage']
            print(f"Primary O2 Storage: {o2_val:.2f}%\n")
        except OSError:
            print("Connection lost. Check if the server is still running.")
        except (ValueError, TypeError, KeyError):
            print("Bad data format from TSS - can't extract Primary O2 level")

        time.sleep(1)
