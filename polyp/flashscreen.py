from tracker.firmware import Patch
from tracker.memory import Polyp
import struct

SYMBOLS = {"addr_screen_brightness":0x2000566a}

DST_ADDR_GET_BRIGHTNESS = 0x70100020
imp_get_brightness = """
ldr     r6, =addr_screen_brightness
ldrb    r2, [r6, #1]
strb    r2, [r1]
bx      lr
"""

DST_ADDR_SET_BRIGHTNESS = 0x70100060
imp_set_brightness = """
push    {lr}
ldr     r1, [r0, #8]
ldr     r6, =addr_screen_brightness
lsl     r1, r1, #8
add     r1, r1, 1
strh    r1, [r6]
pop     {pc}
"""

class FlashScreen(Polyp):
    def _get_brightness(self):
        data = self.ti.exec(DST_ADDR_GET_BRIGHTNESS | 1)
        return data[0]

    def _set_brightness(self, val):
        self.ti.exec(DST_ADDR_SET_BRIGHTNESS | 1, struct.pack("<I", val))

    def _flash_screen(self):
        brightness = self._get_brightness()
        for i in range(brightness, 0, -1):
            self._set_brightness(i)
        for repetitions in range(4):
            for i in range(0x80):
                self._set_brightness(i)
            for j in range(0x80, 0, -1):
                self._set_brightness(j)
        for i in range(brightness):
            self._set_brightness(i)

    def run(self):
        self._flash_screen()

def get_polyp(ti):
    trk_ver, fw_ver = ti.get_version()
    # require tracker firmware v1.5.0, patch v0.3
    if (trk_ver[0] == 1 and
        trk_ver[1] == 5 and
        trk_ver[2] == 0 and
        fw_ver[1] >= 3):

        polyp = FlashScreen(
            ti,
            [Patch(
                "Get screen brightness",
                imp_get_brightness,
                DST_ADDR_GET_BRIGHTNESS,
                max_size=0,
                symbols=SYMBOLS,
                thumbmode=True),
            Patch(
                "Set screen brightness",
                imp_set_brightness,
                DST_ADDR_SET_BRIGHTNESS,
                max_size=0,
                symbols=SYMBOLS,
                thumbmode=True)]
        )
        return polyp
    return None