from tracker.firmware import Patch
from tracker.memory import Polyp
from hexdump import hexdump

# dst address of where below assembly
# routine will be written to
DST_ADDR = 0x70100000

imp_return_acab = """
; # r0 = ptr to hid input (0x40 bytes)
; #   can freely be used as input arguments
; # r1 = ptr to hid output (0x40 bytes)
; #   can freely be used for returning
; #   data to the client/caller

mov     r2, #0xabac
movt    r2, #0xacab
str     r2, [r1]
bx      lr
"""
# symbols used by above assembly routine
sym = {"addr_screen_brightness":0x2000566a}

class ExamplePolyp(Polyp):
    # an instance of the memory.Polyp class should
    # implement a run() method at a minimum
    # "args" is a list of optional arguments that
    # can be passed to Polyps by providing the
    # "--polypargs" option to retracker.py
    def run(self, args):
        """this method is run after successful assembly of all patches"""
        print("arguments provided: %s" % args)
        # setting the lowest bit causes the code
        # to be executed in thumb mode (clearing it, in ARM mode)
        data = self.ti.exec(DST_ADDR | 1)
        print("Data returned:\n%s" % hexdump(data))

def get_polyp(ti):
    """returns instance of memory.Polyp"""

    trk_ver, fw_ver = ti.get_version()
    # require tracker firmware v1.5.0, patch v0.3
    if (trk_ver[0] == 1 and
        trk_ver[1] == 5 and
        trk_ver[2] == 0 and
        fw_ver[1] >= 3):

        polyp = ExamplePolyp(
            ti,
            [Patch(
                "Simple example",
                imp_return_acab,
                DST_ADDR)]
        )
        return polyp
    return None