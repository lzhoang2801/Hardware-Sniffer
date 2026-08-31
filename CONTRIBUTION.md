# How to Submit Your Updates to the Hardware-Sniffer Project

So you've made some improvements and want to share them with the community. Here's how to get your changes into the main project.

## Step 1: Fork the repo

Head over to [github.com/lzhoang2801/Hardware-Sniffer](https://github.com/lzhoang2801/Hardware-Sniffer) and hit the **Fork** button (top right). Sign in if you need to. GitHub will create a copy of the repo under your account.

## Step 2: Clone your fork

Open PowerShell and run this (swap `YOUR-USERNAME` for your actual GitHub username):

```powershell
cd C:\Users\Conde\Downloads\Compressed
git clone https://github.com/YOUR-USERNAME/Hardware-Sniffer.git Hardware-Sniffer-Git
```

## Step 3: Copy your modified files over

You need to overwrite the cloned files with your updated ones. Either drag and drop the contents of `Hardware-Sniffer-main` into `Hardware-Sniffer-Git`, or run:

```powershell
Copy-Item -Path "Hardware-Sniffer-main\*" -Destination "Hardware-Sniffer-Git\" -Recurse -Force
```

## Step 4: Create a branch and commit

```powershell
cd Hardware-Sniffer-Git

git checkout -b feature/collecte-complete

git add .
git status
git commit -m "feat: Add RAM, MAC, USB/serial/parallel ports, SMBIOS collection

- RAM: memory modules (capacity, speed, manufacturer, type)
- Network: MAC address for each adapter
- BIOS: serial number and UUID
- USB Ports: all USB devices (hubs, peripherals)
- Serial Ports: COM ports
- Parallel Ports: LPT ports
- Fixes: motherboard() bug, get_latest_acpidump(), exception handling"
```

## Step 5: Push to GitHub

```powershell
git push -u origin feature/collecte-complete
```

## Step 6: Open a Pull Request

Go to your fork on GitHub. You should see a yellow banner saying **Compare & pull request** — click it. Add a short description of what you changed and why, then hit **Create pull request**.

That's it. The maintainer will review your changes and merge them if everything looks good.
