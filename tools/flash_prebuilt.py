#!/usr/bin/env python3
"""Verify and flash this exact FNK0104B release; leave NVS and data sectors intact."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

def select_port(explicit, ports):
    if explicit:
        if sys.platform != 'win32' and not Path(explicit).exists():
            raise SystemExit('Serial port does not exist. Use the phone device path, such as /dev/cu.usbmodem1101; do not enter a Terminal command as the port.')
        return explicit
    candidates = {}
    prefixes = ('/dev/cu.usbmodem', '/dev/cu.usbserial', '/dev/cu.wchusbserial',
                '/dev/cu.SLAB_USBtoUART', '/dev/tty.usbmodem', '/dev/tty.usbserial',
                '/dev/tty.wchusbserial', '/dev/tty.SLAB_USBtoUART',
                '/dev/ttyUSB', '/dev/ttyACM')
    for item in ports:
        device = item.device
        if 'bluetooth' in (device + ' ' + item.description).lower():
            continue
        if getattr(item, 'vid', None) is None and not device.startswith(prefixes):
            continue
        if sys.platform == 'darwin' and device.startswith('/dev/tty.'):
            callout = '/dev/cu.' + device[len('/dev/tty.'):]
            if Path(callout).exists():
                device = callout
        candidates[device] = item.description
    if len(candidates) != 1:
        for device, description in sorted(candidates.items()):
            print(device, description)
        if not candidates:
            raise SystemExit('No USB serial device found. Connect the phone with a USB data cable, then retry.')
        raise SystemExit('More than one USB serial device found. Disconnect the other devices, or pass --port followed by the phone device path.')
    return next(iter(candidates))

def main():
    parser=argparse.ArgumentParser(description='Verify and flash the bundled N9 firmware to Freenove FNK0104B (N16R8).')
    parser.add_argument('--port',help='Phone serial device path; one USB serial device is selected automatically')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--verify-only',action='store_true',help='Check bundled binary hashes without accessing a device')
    mode.add_argument('--monitor',action='store_true',help='Open USB diagnostics at 115200 baud without flashing')
    args=parser.parse_args()
    if args.monitor:
        try:
            from serial.tools import list_ports
        except ImportError:
            raise SystemExit('Install the flash tools with: python3 -m pip install esptool==5.1.0')
        port=select_port(args.port,list_ports.comports())
        print('Opening diagnostic output on ' + port, flush=True)
        subprocess.run([sys.executable,'-m','serial.tools.miniterm',port,'115200'],check=True)
        return
    root=Path(__file__).resolve().parents[1]/'bin'
    release=root/'release.json'
    if not release.exists():
        raise SystemExit('Firmware images are missing. Extract the complete firmware ZIP.')
    manifest=json.loads(release.read_text())
    if len(manifest['images'])!=4 or [i['offset'] for i in manifest['images']]!=['0x0','0x8000','0xe000','0x10000']:
        raise SystemExit('Invalid firmware manifest; download and extract the complete ZIP.')
    for item in manifest['images']:
        data=(root/item['file']).read_bytes()
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise SystemExit('Checksum mismatch: '+item['file']+'. Extract a fresh copy of the release.')
    print('All four firmware image checksums verified.')
    if args.verify_only: return
    try:
        import esptool
        from serial.tools import list_ports
    except ImportError:
        raise SystemExit('Install the flash tools with: python3 -m pip install esptool==5.1.0')
    port=select_port(args.port,list_ports.comports())
    print('Flashing verified firmware to ' + port, flush=True)
    command=['--chip','esp32s3','--port',port,'--baud','460800','--after','watchdog-reset','write-flash',
             '--flash-mode',manifest['flash_mode'],'--flash-freq','80m','--flash-size','16MB']
    for item in manifest['images']:
        command += [item['offset'],str(root/item['file'])]
    esptool.main(command)
    print('Flashed ' + manifest['version'] + '. Restart the board and test its functions.')
if __name__=='__main__': main()
