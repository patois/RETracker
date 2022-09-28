import hexdump
import tracker.tracker as tracker
import argparse
import tools.asm as asm
from importlib import import_module
from datetime import datetime


# ------------------------------------------------------------------
def brk(ti, args):
    success = ti.brk()
    print("brk!" if success else "Failed. Try again?")

# ------------------------------------------------------------------
def cont(ti, args):
    success = ti.cont()
    print("cont!" if success else "Failed. Try again?")

# ------------------------------------------------------------------
def dumphex(ti, args):
    addr = int(args.hexdump[0],16)
    size = int(args.hexdump[1],16)
    print("Dumping %08x-%08x\n" % (addr, addr+size))
    data = ti.read_mem(addr, size)
    if data:
        print(hexdump.hexdump(data, addr))
    else:
        print("Dumping memory failed")

# ------------------------------------------------------------------
def disassemble(ti, args):
    addr_and_mode = int(args.disassemble[0],16)
    addr = addr_and_mode & (~1)
    mode = addr_and_mode & 1
    size = int(args.disassemble[1],16)
    print("Disassembling %08x-%08x in %s mode\n" % (addr, addr+size, "Thumb" if mode else "ARM"))
    code = ti.read_mem(addr, size)
    if code:
        d = asm.Disassembler()
        d.disassemble(code, addr_and_mode)
        print(d.get())
    else:
        print("Reading memory failed")

# ------------------------------------------------------------------
def readmem(ti, args):
    addr = int(args.readmem[0], 16)
    size = int(args.readmem[1], 16)
    filename = args.readmem[2]
    try:
        f = open(filename,"wb")
    except:
        print("Error creating output file. Aborting")
        return
    print("Dumping %08x-%08x\n" % (addr, addr+size))
    data = ti.read_mem(addr, size)
    if data:
        f.write(data)
        f.close()
    print("Reading memory was %ssuccessful" % ("" if data else "un"))

# ------------------------------------------------------------------
def writemem(ti, args):
    addr = int(args.writemem[0], 16)
    data = bytes.fromhex(args.writemem[1])
    print("Writing data to address %x" % addr)
    success = ti.write_mem(addr, data)
    print("Writing to memory %ssuccessful" % ("" if success else "un"))

# ------------------------------------------------------------------
def transfer(ti, args):
    srcfile = args.transfer[0]
    dstfile = args.transfer[1]
    print("File transfer in progress")
    with open(srcfile, "rb") as f:
        data = f.read()
        start = datetime.now()
        success = ti.write_file(dstfile, data)
        end = datetime.now()
        print("File transfer %ssuccessful (time: %s)" % ("" if success else "un", end-start))

# ------------------------------------------------------------------
def exec(ti, args):
    addr = int(args.exec[0], 16)
    print("Running code at address %x" % addr)
    print("Returned buffer:\n%s" % hexdump.hexdump(ti.exec(addr)))

# ------------------------------------------------------------------
def assemble(ti, args):
        mod = import_module(args.assemble[0])
        polyp = mod.get_polyp(ti)
        if not polyp:
            print("Current firmware not supported. Aborting.")
            return

        patches = polyp.get_patches()
        i = 0
        for patch in patches:
            i += 1
            print("Assembling patch #%d" % i)
            for patch_loc in patch.PatchLocs:
                a = asm.Assembler(
                    patch_loc.entry,
                    patch_loc.code,
                    symbols=patch_loc.symbols,
                    thumb=patch_loc.thumbmode)
                print("Description: \"%s\"" % patch.description)
                print("Target address: %08X" % patch_loc.entry)
                print("Mode: %s" % ("thumb" if patch_loc.thumbmode else "arm"))
                if not a.assemble():
                    print("Failed! Aborting...")
                    return
                data = a.get_as_hex_string()          
                print("Patching memory")
                ti.write_mem(patch_loc.entry, bytes.fromhex(data))
        print("Running code...")
        args = args.polypargs
        success = polyp.run(args)
        print("Done" if success else "Failure")

# ------------------------------------------------------------------
def main():
    epilog = """Examples:
Dump memory to file:        %(prog)s -r 70100000 4f0 dump.bin
Write data to memory:       %(prog)s -w 70100000 \"41 EC FA414142c0\"
Hex-dump:                   %(prog)s -x 0 ffff
Disassemble:                %(prog)s -d 3c01 c000
Assemble and run Polyp:     %(prog)s -a polyp.scroller --polypargs \"hi there!\"
Run code in Thumb mode:     %(prog)s -e 70100001
Run code in ARM mode:       %(prog)s -e 70100000
Transfer file to Tracker:   %(prog)s -t PolyendTracker_1.5.0.ptf Firmware/PolyendTracker_cstm.ptf
"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog)
    x = parser.add_mutually_exclusive_group()

    x.add_argument("-b",
        action="store_true",
        help="break")
    x.add_argument("-c",
        action="store_true",
        help="continue")
    x.add_argument("-r", "--readmem",
        nargs=3,
        metavar=("ADDRESS", "SIZE", "FILE"),
        help="Save memory to local file")
    x.add_argument("-w", "--writemem",
        nargs=2,
        metavar=("ADDRESS", "DATA"),
        help="Write hex-encoded data to memory ADDRESS")
    x.add_argument("-x", "--hexdump",
        nargs=2,
        metavar=("ADDRESS", "SIZE"),
        help="Create hex-dump of memory")
    x.add_argument("-d", "--disassemble",
        nargs=2,
        metavar=("ADDRESS", "SIZE"),
        help="Disassemble code at ADDRESS (ARM/Thumb aware)")
    x.add_argument("-a", "--assemble",
        nargs=1,
        metavar=("POLYP"),
        help="Assemble and execute POLYP patchfile")
    parser.add_argument("--polypargs",
        nargs="+",
        help="Optional arguments that can be passed to a POLYP")
    x.add_argument("-e", "--exec",
        nargs=1,
        metavar=("ADDRESS"),
        help="Execute code at ADDRESS (ARM/Thumb aware)")
    x.add_argument("-t", "--transfer",
        nargs=2,
        metavar=("SRC_FILENAME", "DST_FILENAME"),
        help="Transfer SRC_FILENAME to Tracker's DST_FILENAME")
    args = parser.parse_args()

    ti = tracker.Tracker()
    if not ti.open():
        print("Polyend Tracker not attached")
        return
    print("Connected to Polyend Tracker")

    ver = ti.get_version()
    if not ver:
        print("Firmware version not supported or interface currently claimed")
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
            patch_ver[1] >= 3):
        print("Version not supported. aborting")
        return

    # TODO
    if args.b:
        if not (patch_ver[1] >= 3 and patch_ver[2] >= 3):
            print("Error: option requres new RETracker firmware")
            return
        brk(ti, args)
    if args.c:
        if not (patch_ver[1] >= 3 and patch_ver[2] >= 3):
            print("Error: option requres new RETracker firmware")
            return
        cont(ti, args)
    elif args.hexdump:
        dumphex(ti, args)
    elif args.disassemble:
        disassemble(ti, args)
    elif args.readmem:
        readmem(ti, args)
    elif args.writemem:
        writemem(ti, args)
    elif args.transfer:
        transfer(ti, args)
    elif args.exec:
        exec(ti, args)
    elif args.assemble:
        assemble(ti, args)

# ------------------------------------------------------------------
if __name__ == "__main__":
    main()