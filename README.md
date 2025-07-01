# kmboxnet 🎉

[![PyPI version](https://img.shields.io/pypi/v/kmboxnet.svg)](https://pypi.python.org/pypi/kmboxnet)
[![Python Version](https://img.shields.io/pypi/pyversions/kmboxnet.svg)](https://pypi.org/project/kmboxnet/)

Welcome to `kmboxnet`! ✨ This is a fun, prototype library for controlling your **Kmbox Net** device, written in pure Python. No heavy dependencies—it's all built using the standard `socket` library, making it super lightweight and easy to use.

Certainly! Here’s a version with your requested addition, emphasizing that `kmboxnet` uses **only the Python standard library** and is **completely OS-independent**:

## Why Choose `kmboxnet`? A Pythonic Experience

`kmboxnet` is designed from the ground up to provide a smooth and intuitive developer experience, just like you'd expect from a modern Python library.

* **Pure Standard Library, No OS Dependencies**: `kmboxnet` is implemented *exclusively* using Python’s standard library—no external packages, no platform-specific hacks. This means your code will run the same way on Windows, macOS, and Linux, with zero extra installation steps and no hidden dependencies.

* **Intelligent Type Hinting & Autocomplete**: The library is fully type-hinted. Your IDE (like VS Code or PyCharm) will understand all the methods and parameters, giving you helpful autocompletion and reducing bugs before you even run your code.

* **Resilient and Pythonic Error Handling:**
Commands like `move()` or `left()` never crash your program—they simply return `False` if something goes wrong (such as the Kmbox being unplugged), letting your script run smoothly even if the device is temporarily unavailable. Only during initialization does the library raise a clear, Pythonic exception (`KmboxError`) if it cannot connect, so you’re immediately alerted to any critical setup issues.

This combination of features means you can write clean, readable, and robust automation scripts with confidence—**anywhere Python runs**.

## Installation 🛠️

```bash
pip install kmboxnet
```

## Quick Start 🚀

Let's see how easy it is to connect and move your mouse. Notice that we only need one `try...except` block for the initial connection.

```python
import time
from kmboxnet import KmboxNet, KmboxError

try:
    # Initialization is the only part that can raise a critical exception
    kmbox = KmboxNet(ip="192.168.2.177", port=3368, uuid="11223344")
    print("🎉 Connected to Kmbox!")

except KmboxError as e:
    print(f"Failed to connect: {e}")
    # Exit if connection fails, as nothing else will work
    exit()

# From here on, no more exceptions for command failures!
print("Wait 2 seconds before we start...")
time.sleep(2)

# Move the mouse 100 pixels to the right and 50 pixels down
print("Moving the mouse...")
if not kmbox.move(100, 50):
    print("Failed to move the mouse. Is the Kmbox still connected?")

time.sleep(0.5)

# Perform a left click
print("Click!")
kmbox.left(True)
time.sleep(0.1)
kmbox.left(False)

print("Script finished!")
```

## Known Issues & Contribution Opportunity

### The Blocking Issue

`kmboxnet` currently uses a synchronous design. This means that when a command like `move()` is sent, the main thread of your program **blocks (waits)** until it receives a confirmation from the Kmbox device.

-   **The Problem**: If the device is slow or disconnected, this can cause your program to "freeze" for up to 2 seconds (the default timeout). This is not ideal for high-performance, real-time applications like gaming bots.

### We Need Your Help!

The ideal solution to this problem is to implement a **command queue system**. This would involve:
1.  A dedicated worker thread to handle all communication with the Kmbox.
2.  `move()`, `left()`, etc., would become non-blocking, instantly adding their command to a queue.

This would make the library truly high-performance. **Contributions in this area are highly welcome!** If you're interested in tackling this, please feel free to open a pull request or start a discussion in the issues.

### About Untested Functions

While most major functions—including `move_auto` and `move_bezier`—are already tested, **the following functions have not been fully tested yet**:

* `set_config`
* `reboot`
* `debug`
* `lcd_color`
* `lcd_picture_bottom`
* `lcd_picture`
* `set_vid_pid`
* `trace_enable`

If you find any bugs or issues when using these functions, **please let me know by opening an issue**.
Your feedback and reports are greatly appreciated!

## Advanced `Monitor` Usage: The Secret of `monitor_timeout`

The `monitor_timeout` parameter is a powerful feature that changes how you receive physical mouse movement events. This is perfect for visualizing or reacting to raw hardware inputs.

### "Detect Mouse Stop" Mode (Default)
With the default `monitor_timeout=0.003`, the monitor will send a final `x=0, y=0` event when the mouse stops moving.

```python
# This code will print mouse movements and a "Mouse stopped!" message
# when you stop moving your physical mouse.

kmbox = KmboxNet(ip="...", port=..., uuid="...", monitor_port=5002)
print("Move your mouse...")

while True:
    try:
        # The event queue gives you every single hardware report
        event = kmbox.monitor.events.get(timeout=1.0)
        (x, y) = (event.mouse.x, event.mouse.y)

        if x == 0 and y == 0:
            print("Mouse stopped!")
        else:
            print(f"Mouse moved: dx={x}, dy={y}")

    except queue.Empty:
        # No events for 1 second
        pass
```

### "Raw Input" Mode
By setting `monitor_timeout=None`, you get only the pure, unfiltered hardware events.

```python
# This code will only print movement events when the mouse is actually moving.
# It will never print "x=0, y=0" unless the hardware itself sends it.

kmbox = KmboxNet(ip="...", port=..., uuid="...", monitor_port=5002, monitor_timeout=None)
print("Move your mouse (Raw Mode)...")

while True:
    try:
        event = kmbox.monitor.events.get(timeout=1.0)
        (x, y) = (event.mouse.x, event.mouse.y)
        print(f"Raw mouse event: dx={x}, dy={y}")
    except queue.Empty:
        pass
```

## License

This project is licensed under the MIT License.

