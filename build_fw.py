from intelhex import IntelHex
import tools.asm as asm
import tracker.firmware as firmware
import argparse
import hashlib

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="Input path/filename of Polyend Tracker firmware")
    parser.add_argument("outfile", help="Output path/filename of customized firmware")
    args = parser.parse_args()

    fi = open(args.infile, "rb")
    data = fi.read()
    fi.close()
    digest = hashlib.md5(data).hexdigest()
    print("MD5: %s" % digest)
    patches = firmware.get_patches(digest)
    if not patches:
        print("This firmware currently is not supported")
        return
    count = len(patches)
    print("Found %d patch%s" % (count, "es" if count > 1 else ""))
    n = 0
    for patch in patches:
        n += 1
        print("Assembling patch #%d\nDescription: \"%s\"" % (n, patch.description))
        a = asm.Assembler(
                patch.entry,
                patch.code,
                symbols=patch.symbols,
                max_size=patch.max_size,
                thumb=patch.thumbmode)
        success = a.assemble()
        if not success:
            print("Error: could not assemble patch")
            return

        patches = {
            a.get_entry():a.get_as_hex_string()
        }
        print("Reading input file")
        fw = IntelHex(args.infile)
        print("Applying patch")
        for k,v in patches.items():
            fw.puts(k, bytes.fromhex(v))
        print("Creating output file")
        fw.write_hex_file(args.outfile, write_start_addr=False)
        print("Done")
    return

if __name__ == "__main__":
    main()