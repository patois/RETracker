from http.client import NON_AUTHORITATIVE_INFORMATION
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

font_20bit = {
    "A": 0b11110110101111011010,
    "B": 0b11100101101101011110,
    "C": 0b01110110001100001110,
    "D": 0b11100110101101011100,
    "E": 0b11110111001100011110,
    "F": 0b11110111001100011000,
    "G": 0b11110110001101011110,
    "H": 0b11010111101111011010,
    "I": 0b11110011000110011110,
    "J": 0b00110001101011011110,
    "K": 0b11010111001110011010,
    "L": 0b11000110001100011110,
    "M": 0b11011111111010110001,
    "N": 0b11010110101011010110,
    "O": 0b01100110101101001100,
    "P": 0b11110110101111011000,
    "Q": 0b01100100101011001110,
    "R": 0b11100110101110011010,
    "S": 0b11110110000011011110,
    "T": 0b11110011000110001100,
    "U": 0b11010110101111011110,
    "V": 0b11010110100111000100,
    "W": 0b10001101011111111011,
    "X": 0b11010011000110011010,
    "Y": 0b11010110100110001100,
    "Z": 0b11110001101100011110,
    " ": 0b00000000000000000000,
    "0": 0b01100110101101001100,
    "!": 0b10101101010000010101,
    "?": 0b11100001000000001000,
    ".": 0b00000000000000010000
}

NUM_PAD_ROWS = 4
NUM_PADS_PER_ROW = 12
NUM_PADS_TOTAL = NUM_PAD_ROWS * NON_AUTHORITATIVE_INFORMATION
CHAR_WIDTH = 5
CHAR_DISTANCE = CHAR_WIDTH + 1

class Scroller(Polyp):
    def __init__(self, ti, patches):
        super().__init__(ti, patches)
        self.frame = NUM_PADS_TOTAL*[0]
    
    def _clear_frame(self):
        for i in range(len(self.frame)):
            self.frame[i] = 0

    def _set_pad(self, idx, state, brightness=0xa):
        if idx >= 0 and idx < NUM_PADS_TOTAL:
            self.ti.exec(DST_ADDR | 1, struct.pack("<IIH", idx, 1 if state else 0, brightness))

    def _set_pixel(self, idx, state):
        self.frame[idx] = state

    def _draw_frame(self):
        for i in range(12):
            self._set_pad(
                i,
                self.frame[i])
            self._set_pad(
                i + NUM_PADS_PER_ROW,
                self.frame[i+NUM_PADS_PER_ROW])
            self._set_pad(
                i + NUM_PADS_PER_ROW * 2,
                self.frame[i+NUM_PADS_PER_ROW*2])
            self._set_pad(
                i + NUM_PADS_PER_ROW * 3,
                self.frame[i+NUM_PADS_PER_ROW*3])

    def _draw_char(self, c, x_coord, neg=False):
        shift_mask = 0b10000
        pt1 = (c >> (3 * CHAR_WIDTH)) & 0b11111
        pt2 = (c >> (2 * CHAR_WIDTH)) & 0b11111
        pt3 = (c >> (1 * CHAR_WIDTH)) & 0b11111
        pt4 = c & 0b11111
        # for all 5 bits
        for _x in range(x_coord, x_coord+CHAR_WIDTH):
            if _x >= 0 and _x < 0xc:
                self._set_pixel(
                    _x,
                    ((pt1 & shift_mask) != 0) & ~neg)
                self._set_pixel(
                    _x + 0xc,
                    ((pt2 & shift_mask) != 0) & ~neg)
                self._set_pixel(
                    _x + 2*0xc,
                    ((pt3 & shift_mask) != 0) & ~neg)
                self._set_pixel(
                    _x + 3*0xc,
                    ((pt4 & shift_mask) != 0) & ~neg)
            shift_mask >>= 1

    def _print(self, s, x=0, delay=0.001):
        s = s.upper()
        offs = 0

        self._clear_frame()
        for c in s:
            self._draw_char(font_20bit[c], x+offs)
            offs += CHAR_DISTANCE

        self._draw_frame()
        sleep(delay)

    def _scroll(self, s, delay=0.001):
        for x in range (0xc, CHAR_DISTANCE-(len(s)+1)*CHAR_DISTANCE, -1):
            self._print(s, x, delay=delay)

    def run(self):
        try:
            while True:
                self._scroll("RETracker")
        except:
            self._clear_frame()
            self._draw_frame()
            self._print("OK", 1)

def get_polyp(ti):
    trk_ver, fw_ver = ti.get_version()
    # require tracker firmware v1.5.0, patch v0.3
    if (trk_ver[0] == 1 and
        trk_ver[1] == 5 and
        trk_ver[2] == 0 and
        fw_ver[1] >= 3):

        polyp = Scroller(
            ti,
            [Patch(
                "Text scroller on the Tracker's pads",
                imp_set_pad,
                DST_ADDR,
                symbols=SYMBOLS)]
        )
        return polyp
    return None
