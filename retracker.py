import hexdump
import tracker.tracker as tracker
import argparse
import tools.asm as asm
from importlib import import_module
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    x = parser.add_mutually_exclusive_group()
    x.add_argument("-r", "--readmem",
        nargs=3,
        metavar=("ADDRESS", "SIZE", "FILE"),
        help="Save memory to local file. Example: %(prog)s -r 70100000 4f0 dump.bin")
    x.add_argument("-w", "--writemem",
        nargs=2,
        metavar=("ADDRESS", "DATA"),
        help="Write memory. Example: %(prog)s -w 70100000 4141ACAB4141")
    x.add_argument("-x", "--hexdump",
        nargs=2,
        metavar=("ADDRESS", "SIZE"),
        help="Create hex-dump of memory. Example: %(prog)s -x 0 ffff")
    x.add_argument("-d", "--disassemble",
        nargs=2,
        metavar=("ADDRESS", "SIZE"),
        help="Disassemble code at ADDRESS (ARM/Thumb aware). Example: %(prog)s -d 3c01 c000")
    x.add_argument("-a", "--assemble",
        nargs=1,
        metavar=("POLYP"),
        help="Load POLYP patchfile Example: %(prog)s -a polyp.flashscreen")
    x.add_argument("-e", "--exec",
        nargs=1,
        metavar=("ADDRESS"),
        help="Execute code at ADDRESS (ARM/Thumb aware). Example: %(prog)s -e 70100001")
    x.add_argument("-t", "--transfer",
        nargs=2,
        metavar=("SRC_FILENAME", "DST_FILENAME"),
        help="Transfer SRC_FILENAME to Tracker's DST_FILENAME. Example: %(prog)s -t PolyendTracker_1.5.0.ptf Firmware/PolyendTracker_cstm.ptf")
    args = parser.parse_args()

    ti = tracker.Tracker()
    if not ti.open():
        print("Polyend Tracker not attached")
        return
    print("Connected to Polyend Tracker")

    ver = ti.get_version()
    if not ver:
        print("Firmware version not supported")
        return
    tracker_ver, patch_ver = ver
    print("Detected fw patch v%d.%d.%d on Tracker firmware v%d.%d.%d\n" % (
        patch_ver[0],
        patch_ver[1],
        patch_ver[2],
        tracker_ver[0],
        tracker_ver[1],
        tracker_ver[2]))

    if not (tracker_ver[0] >= 1 and
            tracker_ver[1] >= 5 and
            tracker_ver[2] >= 0 and
            patch_ver[0] >= 0 and
            patch_ver[1] >= 3):
        print("Version not supported. aborting")
        return

    if args.hexdump:
        addr = int(args.hexdump[0],16)
        size = int(args.hexdump[1],16)
        print("Dumping %08X-%08X\n" % (addr, addr+size))
        data = ti.read_mem(addr, size)
        if data:
            print(hexdump.hexdump(data, addr))
        else:
            print("Dumping memory failed")
    elif args.disassemble:
        addr_and_mode = int(args.disassemble[0],16)
        addr = addr_and_mode & (~1)
        mode = addr_and_mode & 1
        size = int(args.disassemble[1],16)
        print("Disassembling %08X-%08X in %s mode\n" % (addr, addr+size, "Thumb" if mode else "ARM"))
        code = ti.read_mem(addr, size)
        if code:
            d = asm.Disassembler()
            d.disassemble(code, addr_and_mode)
            print(d.get())
        else:
            print("Reading memory failed")
    elif args.readmem:
        addr = int(args.readmem[0], 16)
        size = int(args.readmem[1], 16)
        filename = args.readmem[2]
        try:
            f = open(filename,"wb")
        except:
            print("Error creating output file. Aborting")
            return
        print("Dumping %08X-%08X\n" % (addr, addr+size))
        data = ti.read_mem(addr, size)
        if data:
            f.write(data)
            f.close()
        print("Reading memory was %ssuccessful" % ("" if data else "un"))
    elif args.writemem:
        addr = int(args.writemem[0], 16)
        data = bytes.fromhex(args.writemem[1])
        print("Writing data to address %x" % addr)
        success = ti.write_mem(addr, data)
        print("Writing to memory %ssuccessful" % ("" if success else "un"))
    elif args.transfer:
        srcfile = args.transfer[0]
        dstfile = args.transfer[1]
        print("File transfer in progress")
        with open(srcfile, "rb") as f:
            data = f.read()
            start = datetime.now()
            success = ti.write_file(dstfile, data)
            end = datetime.now()
            print("File transfer %ssuccessful (time: %s)" % ("" if success else "un", end-start))
    elif args.exec:
        addr = int(args.exec[0], 16)
        print("Running code at address %x" % addr)
        print("Returned buffer:\n%s" % hexdump.hexdump(ti.exec(addr)))
    elif args.assemble:
        mod = import_module(args.assemble[0])
        polyp = mod.get_polyp(ti)
        if not polyp:
            print("Current firmware not supported. Aborting")
            return

        patches = polyp.get_patches()
        i = 0
        for patch in patches:
            i += 1
            print("Assembling patch #%d" % i)
            a = asm.Assembler(
                patch.entry,
                patch.code,
                symbols=patch.symbols,
                thumb=patch.thumbmode)
            print("Description: \"%s\"" % patch.description)
            print("Target address: %08X" % patch.entry)
            print("Mode: %s" % ("thumb" if patch.thumbmode else "arm"))
            if not a.assemble():
                print("Failed! Aborting...")
                return
            data = a.get_as_hex_string()          
            print("Patching memory")
            ti.write_mem(patch.entry, bytes.fromhex(data))

        print("Running code...")
        polyp.run()
        print("Done")

if __name__ == "__main__":
    main()