# TSS Setup Guide (Windows)

How to install and run NASA's **Telemetry Stream Server (TSS)** on your computer.
The TSS pretends to be a spacesuit: it generates fake telemetry (oxygen, battery, heart rate, switch positions, location) that our HUD reads.

> **Important:** The TSS goes in its **own folder**, NOT inside our `nasa-suits-hud` repo. We only run NASA's code, we never edit it.

---

## Part 1: One-time setup

### Step 1. Install WSL (Linux inside Windows)
The TSS only runs on Linux/Mac, so on Windows we need WSL.

1. Open **PowerShell as Administrator** (Start menu → type "PowerShell" → right-click → *Run as administrator*).
2. Run:
   ```
   wsl --install
   ```
3. **Restart your computer.**
4. After restarting, an Ubuntu window opens and asks you to create a **Linux username and password**. Remember the password: you'll need it for `sudo` commands.

### Step 2. Open the WSL terminal
Press the **Windows key**, type `wsl` (or `Ubuntu`), and press Enter.

You'll see a prompt like `yourname@LAPTOP:~$`. The `~` means you're in your Linux home folder.

### Step 3. Create a project folder and download the TSS
```
cd ~
mkdir nasa_suits
cd nasa_suits
git clone https://github.com/SUITS-Techteam/TSS2027.git
cd TSS2027
```

### Step 4. Install the build tools
Check if you already have the C compiler (GCC):
```
gcc --version
```
- If it prints a version number → skip to Step 5.
- If it says `command not found` → install it:
  ```
  sudo apt update
  sudo apt install build-essential
  ```
  Type your Linux password when asked (nothing shows while typing, that's normal), and `y` to confirm.

### Step 5. Build the server
```
chmod +x ./build.bat
./build.bat
```
---

## Part 2: Run the server

### Step 6. Start the TSS
```
./server.exe
```
You should see:
```
Launching Server at IP: xxx.xx.xxx.xx:14141
Configuring Local Address...
Creating HTTP Socket...
Binding HTTP Socket...
Listening to HTTP Socket...
```

### Step 7. Open the TSS web page
Copy the address from the first line (`xxx.xx.xxx.xx:14141`) into your browser (Chrome/Edge).
In the VS Code terminal you can also **Ctrl + click** it.

✅ **Done when:** the TSS page loads and shows telemetry numbers.

### Stopping the server
Click the terminal and press **Enter**. (Closing the terminal also stops it.)

---

## Every time after (quick start)
No need to rebuild. Just:
```
cd ~/nasa_suits/TSS2027
./server.exe
```
Then open the printed address in your browser.

**Updating the TSS** (NASA is still releasing updates):
```
cd ~/nasa_suits/TSS2027
git pull
./build.bat
```