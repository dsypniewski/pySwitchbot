import os
import shutil
import stat
import sys
import subprocess


def register(schema: str, destination: tuple[str, int]):
    if sys.platform == "linux":
        register_linux(schema, destination)
    elif sys.platform == "darwin":
        register_macos(schema, destination)
    elif sys.platform == "win32":
        register_windows(schema, destination)
    else:
        raise RuntimeError("Unsupported platform")


def cleanup(schema: str):
    if sys.platform == "linux":
        cleanup_linux(schema)
    elif sys.platform == "darwin":
        cleanup_macos(schema)
    elif sys.platform == "win32":
        cleanup_windows(schema)
    else:
        raise RuntimeError("Unsupported platform")


def _get_inline_command(destination, after, executable=sys.executable):
    lines = [
        "import sys",
        "from multiprocessing.connection import Client",
        f"c = Client({destination})",
        "c.send(sys.argv[2])",
        "c.close()",
    ]
    script = "; ".join(lines)
    return f'{executable} -c "{script}" - {after}'


def register_linux(schema, destination):
    applications_dir = os.path.expanduser("~/.local/share/applications/")
    handler_path = os.path.join(applications_dir, f"{schema}_url_handler.desktop")
    with open(handler_path, "w+") as f:
        f.write(f"""[Desktop Entry]
Name={schema} URL Handler
Exec={_get_inline_command(destination, '"%u"')}
NoDisplay=true
Type=Application
Terminal=false
MimeType=x-scheme-handler/{schema};
""")
    subprocess.call(["update-desktop-database", applications_dir])


def cleanup_linux(schema: str):
    applications_dir = os.path.expanduser("~/.local/share/applications/")
    handler_path = os.path.join(applications_dir, f"{schema}_url_handler.desktop")
    if os.path.isfile(handler_path):
        os.remove(handler_path)
        subprocess.call(["update-desktop-database", applications_dir])


def register_macos(schema, destination):
    app_dir = f"/Applications/{schema}_url_handler.app"
    os.makedirs(os.path.join(app_dir, "Contents", "MacOS"))
    with open(os.path.join(app_dir, "Contents", "Info.plist"), "w+") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>script.py</string>
    <key>CFBundleIdentifier</key>
    <string>pl.dsypniewski.{schema}_url_handler</string>
    <key>CFBundleName</key>
    <string>{schema} URL Handler</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>CFBundleURLTypes</key>
    <array>
        <dict>
            <key>CFBundleURLName</key>
            <string>{schema}</string>
            <key>CFBundleURLSchemes</key>
            <array>
                <string>{schema}</string>
            </array>
        </dict>
    </array>
</dict>
</plist>
""")
    script_path = os.path.join(app_dir, "Contents", "MacOS", "script.py")
    with open(script_path, "w+") as f:
        f.write(f"""#!/usr/bin/python
import struct
from multiprocessing.connection import Client

from AppKit import NSAppleEventManager, NSObject, NSApp, NSApplication
from PyObjCTools import AppHelper


class AppDelegate(NSObject):
    def applicationWillFinishLaunching_(self, _):
        manager = NSAppleEventManager.sharedAppleEventManager()
        event_class = event_id = struct.unpack(">l", b"GURL")[0]
        manager.setEventHandler_andSelector_forEventClass_andEventID_(self, "openURL:withReplyEvent:", event_class, event_id)

    def openURL_withReplyEvent_(self, event, _):
        descriptor = struct.unpack(">l", b"----")[0]
        url = event.descriptorForKeyword_(descriptor).stringValue()
        client = Client({destination})
        client.send(url)
        client.close()
        NSApp().terminate_(self)


if __name__ == '__main__':
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
""")
    os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    subprocess.call(["/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister", "-f", app_dir])


def cleanup_macos(schema: str):
    app_dir = f"/Applications/{schema}_url_handler.app"
    if os.path.isdir(app_dir):
        shutil.rmtree(app_dir)


def register_windows(schema, destination):
    import winreg
    root = winreg.ConnectRegistry(None, winreg.HKEY_CLASSES_ROOT)
    schema_key = winreg.CreateKey(root, schema)
    winreg.SetValue(schema_key, "", winreg.REG_SZ, f"URL:{schema} Protocol")
    winreg.SetValue(schema_key, "URL Protocol", winreg.REG_SZ, "")
    command_key = winreg.CreateKey(winreg.CreateKey(winreg.CreateKey(schema_key, "shell"), "open"), "command")
    winreg.SetValue(command_key, "", winreg.REG_SZ, _get_inline_command(destination, '"%1"'))


def cleanup_windows(schema):
    import winreg
    root = winreg.ConnectRegistry(None, winreg.HKEY_CLASSES_ROOT)
    key = f"{schema}\\shell\\open\\command"
    paths = [key]
    while "\\" in key:
        key, _ = key.rsplit("\\", 1)
        paths.append(key)
    for key in paths:
        winreg.DeleteKey(root, key)
