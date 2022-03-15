# RETracker

`RETracker` is a reverse engineering framework for the [Polyend Tracker](https://polyend.com/tracker/) written in Python.
It is based on unofficial patches that it applies to the vendor's stock firmware.
These patches replace the Tracker's MTP file transfer functionality ([disabled by Polyend with the introduction of firmware v1.4.0](https://github.com/polyend/TrackerBetaTesting/releases/tag/1.4.0)) with a custom USB HID handler.

The `RETracker's` custom USB handler introduces new, non-official features to the `Polyend Tracker` that can be controlled from a computer via USB.

![RETracker screenshot](rsrc/retracker.png)

The `RETracker` firmware's basic features comprise the following:
* Reading/dumping of memory
* Writing/patching of memory
* Execution of custom code/redirection of control flow
* Writing files to the tracker's SD card

These features are a solid base for adding further functions to the `Polyend Tracker` during run-time, by assembling position-independend code on the host, transferring it to the Tracker and having the new USB handler execute the freshly implanted code. There are a number of features available already that can be transferred dynamically to the device.
Make sure to [check them out](polyp/) and/or add your own!

Adding to that, the memory reading/writing functions allow the USB host to inspect the `Tracker's` memory by creating hex-dumps or by disassembling code in ARM or Thumb mode.

Finally, the file transfer function (currently the only direction implemented is *from* the USB host *to* the `Tracker's` SD card) allows new firmware files or `NES` roms to be copied to the Tracker, without having to go through the intended process of swapping the SD card between the `Tracker` and your computer.

HAPPY HACKING!
## Installation
First of all, RETracker requires a number of [dependencies](DEPENDENCIES.md) to be installed.
Please check them out and make sure you have them all installed before you go on.

Once all dependencies are installed, a patched firmware can be created by running [build_fw.py](build_fw.py).

```
# python build_fw.py
usage: build_fw.py [-h] infile outfile
build_fw.py: error: the following arguments are required: infile, outfile
```
Example:
```
# python build_fw.py PolyendTracker_1.5.0.ptf PolyendTracker_RETracker.ptf
MD5: ce894299bc35996186528364951c901e
Found 1 patch
Assembling patch #1
Description: "Memory dumping/patching/code execution/file transfer via USB"
Reading input file
Applying patch
Creating output file
Done
```
Once a `RETracker` firmware is successfully built, it should be copied to the `Tracker's` `"/firmware/"` folder on the root of its SD card.
The firmware flashing procedure is straight forward and doesn't differ from the ordinary process.

On the device
* press the `config` button
* go to the `Firmware` menu
* enter the `Firmware update` sub menu
* choose the firmware you would like to flash onto the `Polyend Tracker`

If the newly created firmware does not show up on the device, there may be a naming scheme for the firmware that must be followed (must start with `PolyendTracker_` and end with `.ptf`?).
If that is the case, renaming the file on your computer may help.
You're welcome! :D

ACHTUNG!!! It is normal for the UI to behave differently during the update process when flashing a patched firmware.
Please patiently wait for the update to finish until the device reboots.
In case something still went wrong, please consult the `Polyend Tracker` user manual, which explains the steps on how to enter the `emergency update procedure`.

## Supported Firmware Versions
RETracker currently supports `Polyend Tracker` in firmware version 1.5.0, which is the most recent firmware as of this writing.

## How does it work?
Polyend Tracker firmware images ship in intel hex format.
The [build_fw.py](build_fw.py) tool converts the firmware to its plain binary format, which holds all the firmware's code and data.
It then applies patches to the converted binary according to information found in [tracker/firmware.py](tracker/firmware.py) before converting the file back to intel-hex format again.
From there on, the `Polyend Tracker` can be communicated with by plugging it into a USB port of a computer running [retracker.py](retracker.py).

## RETracker Usage
The main workhorse of this project probably is `retracker.py`, which provides a command line interface to the user.
```
# python retracker.py -h
usage: retracker.py [-h] [-r ADDRESS SIZE FILE] [-w ADDRESS DATA] [-x ADDRESS SIZE] [-d ADDRESS SIZE] [-a POLYP]
                    [--polypargs POLYPARGS [POLYPARGS ...]] [-e ADDRESS] [-t SRC_FILENAME DST_FILENAME]

optional arguments:
  -h, --help            show this help message and exit
  -r ADDRESS SIZE FILE, --readmem ADDRESS SIZE FILE
                        Save memory to local file. Example: retracker.py -r 70100000 4f0 dump.bin
  -w ADDRESS DATA, --writemem ADDRESS DATA
                        Write memory. Example: retracker.py -w 70100000 4141ACAB4141
  -x ADDRESS SIZE, --hexdump ADDRESS SIZE
                        Create hex-dump of memory. Example: retracker.py -x 0 ffff
  -d ADDRESS SIZE, --disassemble ADDRESS SIZE
                        Disassemble code at ADDRESS (ARM/Thumb aware). Example: retracker.py -d 3c01 c000
  -a POLYP, --assemble POLYP
                        Assemble and execute POLYP patchfile Example: retracker.py -a polyp.scroller --polypargs "hi
                        there!"
  --polypargs POLYPARGS [POLYPARGS ...]
                        Optional arguments that can be passed to a POLYP
  -e ADDRESS, --exec ADDRESS
                        Execute code at ADDRESS (ARM/Thumb aware). Example: retracker.py -e 70100001
  -t SRC_FILENAME DST_FILENAME, --transfer SRC_FILENAME DST_FILENAME
                        Transfer SRC_FILENAME to Tracker's DST_FILENAME. Example: retracker.py -t
                        PolyendTracker_1.5.0.ptf Firmware/PolyendTracker_cstm.ptf
```
Examples:
```
# python retracker.py -d 0002B99d 100
Connected to Polyend Tracker
Detected fw patch v0.3.0 on Tracker firmware v1.5.0

Disassembling 0002B99C-0002BA9C in Thumb mode

0x0002B99C:     push    {r4}
0x0002B99E:     ldr     r4, [pc, #0x6c]
0x0002B9A0:     umull   ip, r4, r4, r1
0x0002B9A4:     lsrs    r4, r4, #3
0x0002B9A6:     add.w   r1, r1, r4, lsl #2
0x0002B9AA:     uxtb    r1, r1
0x0002B9AC:     cmp     r3, #0x1f
0x0002B9AE:     ite     ls
0x0002B9B0:     addls   r4, r0, r3
0x0002B9B2:     addhi.w r4, r0, #0x1f
0x0002B9B6:     adds    r3, r0, r1
0x0002B9B8:     ldrb    r4, [r4, #5]
0x0002B9BA:     strb.w  r4, [r3, #0xc8]
0x0002B9BE:     cbz     r2, #0x2b9e4
0x0002B9C0:     add.w   r2, r0, r1, lsr #3
```

```
# python retracker.py -x 0002B99d 100
Connected to Polyend Tracker
Detected fw patch v0.3.0 on Tracker firmware v1.5.0

Dumping 0002B99D-0002BA9D

0002b99d  b4 1b 4c a4 fb 01 c4 e4  08 01 eb 84 01 c9 b2 1f  |..L.............|
0002b9ad  2b 94 bf c4 18 00 f1 1f  04 43 18 64 79 83 f8 c8  |+........C.dy...|
0002b9bd  40 8a b1 00 eb d1 02 01  23 92 f8 b6 40 01 f0 07  |@.......#...@...|
0002b9cd  01 03 fa 01 f1 21 43 82  f8 b6 10 01 23 5d f8 04  |.....!C.....#]..|
0002b9dd  4b 80 f8 b5 30 70 47 00  eb d1 04 01 22 94 f8 b6  |K...0pG....."...|
0002b9ed  30 01 f0 07 01 02 fa 01  f1 23 ea 01 01 84 f8 b6  |0........#......|
0002b9fd  10 01 23 5d f8 04 4b 80  f8 b5 30 70 47 00 bf ab  |..#]..K...0pG...|
0002ba0d  aa aa aa 00 eb 01 0c 8c  f8 c8 30 82 b1 00 eb d1  |..........0.....|
0002ba1d  02 01 23 92 f8 b6 c0 01  f0 07 01 03 fa 01 f1 41  |..#............A|
0002ba2d  ea 0c 01 01 23 82 f8 b6  10 80 f8 b5 30 70 47 00  |....#.......0pG.|
0002ba3d  eb d1 0c 01 22 9c f8 b6  30 01 f0 07 01 02 fa 01  |...."...0.......|
0002ba4d  f1 23 ea 01 01 01 23 8c  f8 b6 10 80 f8 b5 30 70  |.#....#.......0p|
0002ba5d  47 00 bf 0f 49 00 23 30  b5 01 f1 3f 05 1c 46 4f  |G...I.#0...?..FO|
0002ba6d  f0 01 0e 01 e0 11 f8 01  3f c2 18 00 eb d3 0c 82  |........?.......|
0002ba7d  f8 c8 40 9c f8 b6 20 03  f0 07 03 0e fa 03 f3 22  |..@... ........"|
0002ba8d  ea 03 03 a9 42 8c f8 b6  30 ec d1 80 f8 b5 e0 30  |....B...0......0|
```

Whereas some of the more common command line options allow memory to be written, read and hex-dumped, the more exciting features are probably the `-e` and `-a` options.
They allow code to be executed on the device.
The `-e` option allows code to be branched to directly, for example after having written code/data to the device's memory using the `-w` option.
The lowest bit of an `address` argument passed to the `retracker.py` command line utility specifies whether or not to use Thumb mode (0: ARM mode, 1: Thumb mode).

The `-a` command line argument accepts so called `Polyps`, which are Python modules containing patches for the `Polyend Tracker` in the form of assembly routines and version-specific offsets and data.

Loading any of these modules using the `-a` command line option causes their assembly routines
* to be assembled on the fly
* transferred to the connected device
* executed on the connected device

Example:
```
# python retracker.py -a polyp.scroller
Connected to Polyend Tracker
Detected fw patch v0.3.0 on Tracker firmware v1.5.0

Assembling patch #1
Description: "Text scroller on the Tracker's pads"
Target address: 70100000
Mode: thumb
Patching memory
Running code...
Done
```

This does not only allow for convenient and sped-up development of custom code and features, it also does not require new firmware to be flashed onto the `Tracker` for new code to be tested (but a reboot in the worst case).

Please have a look at the available modules in the [polyp/](polyp/) folder, which contains a few initial demos that fade the `Tracker's` screen in and out or repurpose its pads as a text-scroller canvas.

## Reverse Engineering the Tracker
The `Polyend Tracker` is believed to be based on a µc similar to the Teensy 3.6 of which [data sheets and other tech info is available here](https://www.pjrc.com/store/teensy36.html).
Be sure to check out the [MK66FX](https://www.pjrc.com/teensy/K66P144M180SF5RMV2.pdf) manual for a memory map in order to avoid running into device crashes when dumping memory.
The `Tracker` firmware image is in intel-hex format and can be loaded directly by the [IDA Pro disassembler](https://hex-rays.com/ida-pro/ida-disassembler/) and probably others such as [GHIDRA](https://ghidra-sre.org/) or [Binary Ninja](https://binary.ninja/) using an ARM processor module in little-endian mode.
The firmware can be mapped to base address 0, with address 4 being a pointer to the reset vector (start disassembling there).
Most, if not all of its code runs in Thumb mode.
I've found address `0x70100000` and above to be a reliable address to plant a `Polyp` into and run its code from there.

## RETracker Wiki
The RETracker wiki can be found [here](https://github.com/patois/RETracker/wiki).

## Disclaimer
The author does not take any responsibility for any damage this project may cause to your Polyend Tracker.
By using RETracker or any information derived, you agree that you are using any of this project's code, data and other information at your own risk.