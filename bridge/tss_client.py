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
        except OSError:
            print("Connection lost. Check if the server is still running.")
        else:
            data = json.loads(reply.decode(errors='replace'))
            print(f"Primary O2 Storage: {data['telemetry']['oxy_pri_storage']:.2f}%\n")
        
        time.sleep(1)
