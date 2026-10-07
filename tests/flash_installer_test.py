#!/usr/bin/env python3
"""Host-only installer checks: no real serial ports or firmware writes are used."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("flash_installer_under_test", ROOT / "tools/flash_prebuilt.py")
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def port(device, description="USB Serial", vid=None):
    return SimpleNamespace(device=device, description=description, vid=vid)


class PortSelectionTests(unittest.TestCase):
    def test_known_mac_and_linux_ports_exclude_bluetooth(self):
        devices = [
            "/dev/cu.usbmodem1101", "/dev/cu.usbserial-0001",
            "/dev/cu.wchusbserial110", "/dev/cu.SLAB_USBtoUART",
            "/dev/ttyACM0", "/dev/ttyUSB0",
        ]
        bluetooth = port("/dev/cu.Bluetooth-Incoming-Port", "Bluetooth")
        for device in devices:
            with self.subTest(device=device), mock.patch.object(Path, "exists", return_value=True):
                self.assertEqual(INSTALLER.select_port(None, [bluetooth, port(device)]), device)

    def test_usb_vid_supports_unfamiliar_device_name(self):
        with mock.patch.object(Path, "exists", return_value=True):
            self.assertEqual(INSTALLER.select_port(None, [port("/dev/cu.vendorbridge", vid=0x303A)]),
                             "/dev/cu.vendorbridge")

    def test_bluetooth_is_excluded_even_if_it_has_usb_vid(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            INSTALLER.select_port(None, [port("/dev/cu.Bluetooth-Incoming-Port", "Bluetooth", 0x1234)])

    def test_no_usb_device_stops(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            INSTALLER.select_port(None, [port("/dev/cu.debug-console", "Built-in serial")])

    def test_multiple_usb_devices_stop_instead_of_guessing(self):
        with mock.patch.object(Path, "exists", return_value=True), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            INSTALLER.select_port(None, [port("/dev/cu.usbmodem1101"), port("/dev/cu.usbserial-0001")])

    def test_mac_tty_alias_is_deduplicated_and_cu_is_preferred(self):
        cu_device = "/dev/cu.usbmodem1101"
        with mock.patch.object(sys, "platform", "darwin"), mock.patch.object(Path, "exists", return_value=True):
            self.assertEqual(INSTALLER.select_port(None, [port("/dev/tty.usbmodem1101"), port(cu_device)]), cu_device)

    def test_duplicate_entries_do_not_create_ambiguity(self):
        device = "/dev/cu.usbmodem1101"
        with mock.patch.object(Path, "exists", return_value=True):
            self.assertEqual(INSTALLER.select_port(None, [port(device), port(device)]), device)

    def test_nonexistent_explicit_path_is_rejected(self):
        with mock.patch.object(Path, "exists", return_value=False), self.assertRaises(SystemExit):
            INSTALLER.select_port("/dev/cu.usbmodem-absent", [])

    def test_pasted_command_is_not_accepted_as_port(self):
        command = '"$HOME/n9-install/.flash-env/bin/python" -m serial.tools.miniterm - 115200'
        with mock.patch.object(Path, "exists", return_value=False), self.assertRaises(SystemExit):
            INSTALLER.select_port(command, [])

    def test_explicit_existing_port_resolves_ambiguity(self):
        selected = "/dev/cu.usbmodem1101"
        with mock.patch.object(Path, "exists", return_value=True):
            self.assertEqual(INSTALLER.select_port(selected, [port(selected), port("/dev/cu.usbserial-0001")]), selected)


class InstallerFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="n9-installer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.release_root = Path(self.temporary.name)
        self.bin_root = self.release_root / "bin"
        self.bin_root.mkdir()
        self.source_patch = mock.patch.object(INSTALLER, "__file__", str(self.release_root / "tools/flash_prebuilt.py"))
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)
        self.manifest = {"version": "host-fixture", "flash_mode": "dio", "images": []}
        for number, offset in enumerate(["0x0", "0x8000", "0xe000", "0x10000"]):
            name = "fixture-%d.bin" % number
            data = ("not-real-firmware-%d" % number).encode()
            (self.bin_root / name).write_bytes(data)
            self.manifest["images"].append({"file": name, "offset": offset, "size": len(data),
                                            "sha256": hashlib.sha256(data).hexdigest()})
        (self.bin_root / "release.json").write_text(json.dumps(self.manifest))

        self.esptool = ModuleType("esptool")
        self.esptool.main = mock.Mock()
        serial = ModuleType("serial")
        serial.__path__ = []
        serial_tools = ModuleType("serial.tools")
        serial_tools.__path__ = []
        self.list_ports = ModuleType("serial.tools.list_ports")
        self.list_ports.comports = mock.Mock(return_value=[port("/dev/cu.usbmodem1101", vid=0x303A)])
        serial.tools = serial_tools
        serial_tools.list_ports = self.list_ports
        modules_patch = mock.patch.dict(sys.modules, {"esptool": self.esptool, "serial": serial,
                                                      "serial.tools": serial_tools,
                                                      "serial.tools.list_ports": self.list_ports})
        modules_patch.start()
        self.addCleanup(modules_patch.stop)

    def run_installer(self, *arguments):
        with mock.patch.object(sys, "argv", ["flash_prebuilt.py", *arguments]), redirect_stdout(io.StringIO()):
            INSTALLER.main()

    def test_verify_only_does_not_enumerate_or_flash(self):
        self.run_installer("--verify-only")
        self.list_ports.comports.assert_not_called()
        self.esptool.main.assert_not_called()

    def test_corrupt_image_blocks_flash_before_serial_access(self):
        (self.bin_root / self.manifest["images"][0]["file"]).write_bytes(b"corrupt")
        with self.assertRaises(SystemExit):
            self.run_installer()
        self.list_ports.comports.assert_not_called()
        self.esptool.main.assert_not_called()

    def test_auto_selected_flash_preserves_release_command(self):
        with mock.patch.object(INSTALLER, "select_port", return_value="/dev/cu.usbmodem1101"):
            self.run_installer()
        expected = ["--chip", "esp32s3", "--port", "/dev/cu.usbmodem1101", "--baud", "460800",
                    "--after", "watchdog-reset", "write-flash", "--flash-mode", "dio",
                    "--flash-freq", "80m", "--flash-size", "16MB"]
        for item in self.manifest["images"]:
            expected.extend([item["offset"], str(self.bin_root / item["file"])])
        self.esptool.main.assert_called_once_with(expected)

    def test_monitor_works_without_manifest_and_never_flashes(self):
        (self.bin_root / "release.json").unlink()
        with mock.patch.object(INSTALLER, "select_port", return_value="/dev/cu.usbmodem1101"), mock.patch("subprocess.run") as run:
            self.run_installer("--monitor")
        run.assert_called_once_with([sys.executable, "-m", "serial.tools.miniterm",
                                     "/dev/cu.usbmodem1101", "115200"], check=True)
        self.esptool.main.assert_not_called()

    def test_ambiguous_devices_never_flash(self):
        self.list_ports.comports.return_value = [port("/dev/cu.usbmodem1101"), port("/dev/cu.usbserial-0001")]
        with mock.patch.object(Path, "exists", return_value=True), self.assertRaises(SystemExit):
            self.run_installer()
        self.esptool.main.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
