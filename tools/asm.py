from dis import disassemble
import keystone as ks
import capstone as cs

class Assembler:
    def __init__(self, entry, code, symbols=None, max_size=0, thumb=True):
        self.entry = entry
        self.code = code
        self.symbols = symbols
        self.max_size = max_size
        self.thumb = thumb
        self.patch = None

    def assemble(self):
        def sym_resolver(symbol, value):
            sym = symbol.decode()
            handled = sym in self.symbols.keys()
            if handled:
                val = self.symbols[sym]
                value[0] = val
            else:
                print("Could not resolve symbol '%s'" % sym)
            return handled

        k = ks.Ks(
            ks.KS_ARCH_ARM,
            ks.KS_MODE_THUMB if self.thumb else ks.KS_MODE_ARM)
        if self.symbols:
            k.sym_resolver = sym_resolver
        self.patch, count = k.asm(self.code, addr=self.entry)
        return count != 0 and (True if not self.max_size else count <= self.max_size)

    def get_entry(self):
        return self.entry

    def get_as_hex_string(self):
        return "".join("%02X" % i for i in self.patch)

class Disassembler:
    def __init__(self):
        self.disassembly = None

    def disassemble(self, code, addr):
        mode = cs.CS_MODE_THUMB if addr & 1 else cs.CS_MODE_ARM
        d = cs.Cs(cs.CS_ARCH_ARM, mode)
        self.disassembly = d.disasm(code, addr & ~1)

    def get(self):
        return "\n".join("0x%08X:\t%s\t%s" % (i.address, i.mnemonic, i.op_str) for i in self.disassembly)