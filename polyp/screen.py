from tracker.firmware import Patch
from tracker.memory import Polyp
import struct

SYMBOLS = {"addr_screen_brightness":0x2000566a}

DST_ADDR_SET_BRIGHTNESS = 0x70100060
imp_set_brightness = """
ldr     r1, [r0, #8]
ldr     r6, =addr_screen_brightness
lsl     r1, r1, #8
add     r1, r1, 1
strh    r1, [r6]
bx      lr
"""

class Screen(Polyp):
    def _set_brightness(self, val):
        self.ti.exec(DST_ADDR_SET_BRIGHTNESS | 1, struct.pack("<I", val))

    def run(self, args):
        if not args:
            print("Missing argument: brightness")
            return False
        self._set_brightness(int(args[0]))
        return True

def get_polyp(ti):
    trk_ver, fw_ver = ti.get_version()
    # require tracker firmware v1.5.0, patch v0.3
    if (trk_ver[0] == 1 and
        trk_ver[1] == 5 and
        trk_ver[2] == 0 and
        fw_ver[1] >= 3):

        polyp = Screen(
            ti,
            [Patch(
                "Set screen brightness",
                imp_set_brightness,
                DST_ADDR_SET_BRIGHTNESS,
                max_size=0,
                symbols=SYMBOLS,
                thumbmode=True)]
        )
        return polyp
    return None