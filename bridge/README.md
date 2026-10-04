# Bridge

Python code that talks to NASA's TSS. For now it's one script.

## tss_client.py

Asks the TSS for telemetry once per second over UDP and prints the primary O2 level.

**Run it:**
1. Start the TSS (see [docs/setup.md](../docs/setup.md)) and note the IP it prints.
2. On the TSS web page, pick team 0 and start the EVA.
3. In a second terminal, from the repo root:
   ```
   python3 bridge/tss_client.py <TSS IP>
   ```
   Example: `python3 bridge/tss_client.py 172.22.251.151`

**You should see:**
```
Primary O2 Storage: 98.97%
```
The number drops slowly while the EVA runs.

**Good to know:**
- Reads team 0 (UDP port 14142).
- If the TSS is off, it prints "Connection lost" and recovers by itself when the TSS is back.
