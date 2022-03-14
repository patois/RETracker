from tracker.firmware import Patch
from tracker.memory import Polyp
from hexdump import hexdump
import struct
from time import sleep

SYMBOLS = {
    "set_pad":0x0002B99C+1,
    "pads_struct": 0x20005D48}

DST_ADDR = 0x70100000
imp_set_pad = """
push    {lr}
mov     r4, r0
ldr     r0, =pads_struct
ldr     r1, [r4,#8]
ldr     r2, [r4,#0xc]
ldrb.w  r3, [r4,#0x10]
ldr     r5, =set_pad
blx     r5
pop     {pc}
"""

class PadsDemo(Polyp):
    def _set_pad(self, idx, on, brightness=3):
        self.ti.exec(DST_ADDR | 1, struct.pack("<IIH", idx, 1 if on else 0, brightness))

    def _all_pads_off(self):
        # turn off all pads
        for i in range(0x30):
            self._set_pad(i, 0)

    def _knight_rider(self, repetitions=2):
        """this can probably be written in a mathematically more elegant way, but... :D"""
        self._all_pads_off()
        for _ in range(repetitions):
            for x in range(12):
                for y in range(0x4):
                    self._set_pad(x+y*12, 1, 0x10)
                    if x:
                        self._set_pad(x+y*12-1, 1, 0x8)
                        if x > 1:
                            self._set_pad(x+y*12-2, 1, 0x4)
                        if x > 2:
                            self._set_pad(x+y*12-3, 0)
            self._all_pads_off()

            for x in range(11, -1, -1):
                for y in range(0x4):
                    self._set_pad(x+y*12, 1, 0x10)
                    if x<11:
                        self._set_pad(x+y*12+1, 1, 0x8)
                        if x < 10:
                            self._set_pad(x+y*12+2, 1, 0x4)
                        if x < 9:
                            self._set_pad(x+y*12+3, 0)
            self._all_pads_off()
        return

    def _one_pad_after_another(self):
        self._all_pads_off()
        for j in range(3):
            for i in range(0x30):
                self._set_pad(i, 1, 3+(j*2))
                sleep(0.01)
            for i in range(0x30, 0, -1):
                self._set_pad(i, 0, 3+(j*2))
                sleep(0.01)

    def _fade_all(self):
        for brightness in range(0xa):
            for i in range(0x30):
                self._set_pad(i, 1, brightness)

        for brightness in range(0xa, 0, -1):
            for i in range(0x30):
                self._set_pad(i, 1, brightness)

    def _flash_all(self):
        for j in range(3):
            for i in range(0x30):
                self._set_pad(i, 0, 3+j)
            sleep(0.5)
            for i in range(0x30):
                self._set_pad(i, 1, 3+j)
            sleep(0.5)

    def run(self):
        # storyboard :D
        self._knight_rider()
        self._one_pad_after_another()

        self._all_pads_off()
        sleep(0.5)
        self._fade_all()
        self._flash_all()
        self._all_pads_off()

def get_polyp(ti):
    trk_ver, fw_ver = ti.get_version()
    # require tracker firmware v1.5.0, patch v0.3
    if (trk_ver[0] == 1 and
        trk_ver[1] == 5 and
        trk_ver[2] == 0 and
        fw_ver[1] >= 3):

        polyp = PadsDemo(
            ti,
            [Patch(
                "Pads demo",
                imp_set_pad,
                DST_ADDR,
                symbols=SYMBOLS)]
        )
        return polyp
    return None