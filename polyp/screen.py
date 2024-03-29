from tracker.firmware import Patch, PatchLoc
from tracker.memory import Polyp
import struct

SYMBOLS = {"addr_screen_brightness":0x2000566a}

DST_ADDR_GET_BRIGHTNESS = 0x70100020
imp_get_brightness = """
ldr     r3, =addr_screen_brightness
ldrb    r2, [r3, #1]
strb    r2, [r1]
bx      lr
"""

DST_ADDR_SET_BRIGHTNESS = 0x70100040
imp_set_brightness = """
ldr     r1, [r0, #8]
ldr     r3, =addr_screen_brightness
lsl     r1, r1, #8
add     r1, r1, 1
strh    r1, [r3]
bx      lr
"""

class Screen(Polyp):
    def _get_screen_brightness(self):
        data = self.ti.exec(DST_ADDR_GET_BRIGHTNESS | 1)
        return data[0]

    def _set_screen_brightness(self, brightness):
        self.ti.exec(
            DST_ADDR_SET_BRIGHTNESS | 1,
            struct.pack("<I", brightness))

    def run(self, args):
        if not args:
            print("Missing argument: --polypargs <brightness>")
            print("Current brightness: %d" % self._get_screen_brightness())
            return True
        brightness = int(args[0])
        print("Setting brightness: %d" % (brightness))
        self._set_screen_brightness(brightness)
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
                PatchLoc(
                    imp_set_brightness,
                    DST_ADDR_SET_BRIGHTNESS,
                    max_size=0,
                    symbols=SYMBOLS,
                    thumbmode=True)
            ),
            Patch(
                "Get screen brightness",
                PatchLoc(
                    imp_get_brightness,
                    DST_ADDR_GET_BRIGHTNESS,
                    max_size=0,
                    symbols=SYMBOLS,
                    thumbmode=True)
            )]
        )
        return polyp
    return None