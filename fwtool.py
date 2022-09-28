from intelhex import IntelHex
import tools.asm as asm
import tracker.firmware as firmware
import argparse
import hashlib

def read_infile(infile):
    try:
        fi = open(infile, "rb")
        data = fi.read()
        fi.close()
    except:
        data = None
    return data

def pack(infile, outfile):
    print("Opening %s" % infile)
    fw = IntelHex()
    fw.loadbin(infile)    
    print("Packing to %s" % outfile)
    fw.write_hex_file(outfile, write_start_addr=False)
    print("Done")

def unpack(infile, outfile):
    print("Opening %s" % infile)
    fw = IntelHex(infile)
    print("Unpacking to %s" % outfile)
    fw.tobinfile(outfile)
    print("Done")

def build(infile, outfile):
    print("Opening %s" % infile)
    data = read_infile(infile)
    if not data:
        print("Input file could not be opened")
        return
    digest = hashlib.md5(data).hexdigest()
    print("MD5: %s" % digest)
    patches = firmware.get_patches(digest)
    if not patches:
        print("This firmware currently is not supported")
        return
    count = len(patches)
    print("Found %d patch%s" % (count, "es" if count > 1 else ""))

    if not count:
        print("No patch available. Aborting.")
        return

    print("Decoding input file")
    fw = IntelHex(infile)

    n = 0
    for patch in patches:
        code_snippets = []
        n += 1
        print("\nPatch #%d\nDescription: \"%s\"" % (n, patch.description))
        apply_patch = input("Would you like to apply this patch (y/n)? ")
        if apply_patch.upper() != "Y":
            print("Skipping patch #%d" % n)
            continue
        for loc in patch.PatchLocs:
            a = asm.Assembler(
                    loc.entry,
                    loc.code,
                    symbols=loc.symbols,
                    max_size=loc.max_size,
                    thumb=loc.thumbmode)
            success = a.assemble()
            if not success:
                print("Error: could not assemble patch. Aborting.")
                return

            code_snippets.append(a)

        print("Applying patch #%d" % n)
        for cs in code_snippets:
            fw.puts(cs.get_entry(), bytes.fromhex(cs.get_as_hex_string()))

    print("Creating output file: %s" % outfile)
    fw.write_hex_file(outfile, write_start_addr=False)
    print("Done")
    return

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="name/path of input file")
    parser.add_argument("outfile", help="name/path of output file")

    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "-b", "--build",
        help="apply RETracker patches to Tracker firmware",
        action="store_true")
    g.add_argument(
        "-u", "--unpack",
        help="unpack Tracker firmware (.ptf) to binary format",
        action="store_true")
    g.add_argument("-p", "--pack",
        help="create Tracker firmware (.ptf) from binary",
        action="store_true")
    args = parser.parse_args()

    if args.build:
        build(args.infile, args.outfile)
    elif args.unpack:
        unpack(args.infile, args.outfile)
    elif args.pack:
        pack(args.infile, args.outfile)
    else:
        parser.print_help()
        return

if __name__ == "__main__":
    main()