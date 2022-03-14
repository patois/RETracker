import struct


new_hid_handler = """
push.w  {r4-r8,lr}

mov     r2, #0x40
sub     sp, sp, #0x200
mov     r4, r0
mov     r1, #0
bl      memset

mov     r1, #0
mov     r0, r4
bl      usb_hid_read
cmp     r0, #0
ble     leave_func

ldrh    r3, [r4]
cmp     r3, #0xf1
beq     read_mem

cmp     r3, #0xf2
beq     write_mem

cmp     r3, #0xf3
beq     get_ver

; # sd_write uses both f5 and f6
cmp     r3, #0xf5
beq     sd_write

cmp     r3, #0xf8
beq     exec

b       leave_func

; #########A f3 #########
get_ver:
; # return version information
; # init response buf
mov     r2, #0x40
add     r0, sp, #0x50
mov     r1, #0
bl      memset

; # return 0xf3, tracker version, custom firmware version
mov     r3, #0xf3
str     r3, [sp, #0x50]
ldr     r5, =TRACKER_FIRMWARE_VERSION
ldr     r6, =CUSTOM_FIRMWARE_VERSION
strd    r5, r6, [sp, #0x54]
add     r0, sp, #0x50
mov     r1, #2000
bl      usb_hid_write
b       leave_func

; #########A f8 #########
exec:
; # init response buf
mov     r2, #0x40
add     r0, sp, #0x50
mov     r1, #0
bl      memset

; # r0 = hid_data
; # r1 = response buf (0x40 bytes)
; # set PC = [hid_data + 4]
; # anything from hid_data + 8 can be
; # considered as input arguments.
; # response buf can be used for
; # returning data to the client
mov     r0, r4
ldr     r5, [r4, #4]
add     r1, sp, #0x50
blx     r5

add     r0, sp, #0x50
mov     r1, #2000
bl      usb_hid_write

b       leave_func

; ######### f5 #########
sd_write:
; # init reponse buf
mov     r2, #0x40
add     r0, sp, #0x50
mov     r1, #0
bl      memset

; # init fd struct
mov     r2, #0x104
add     r0, sp, #0x100
mov     r1, #0
bl      memset

; # create file
mov     r2, #0xb
add     r1, r4, #4
add     r0, sp, #0x100
bl      sd_create_file
cmp     r0, #0
beq     sd_err

; # get data
read_data:
mov     r1, #2000
mov     r0, r4
bl      usb_hid_read
cmp     r0, #0x40
bne     sd_err

; # client may have aborted
ldrh    r5, [r4]
cmp     r5, #0xf6
bne     sd_err

; # write data to file
add     r0, sp, #0x100
add     r1, r4, #0x4
ldrh    r2, [r4, #0x2]
mov     r6, r2
bl      sd_write_file
cmp     r0, #0
ble     sd_err

; # return number of bytes written
strd    r5, r6, [sp, #0x50]
add     r0, sp, #0x50
mov     r1, #2000
bl      usb_hid_write
b       read_data

sd_err:
; # return 0xf6, 0 (error)
mov     r5, #0xf6
mov     r6, #0x00
strd    r5, r6, [sp, #0x50]
add     r0, sp, #0x50
mov     r1, #2000
bl      usb_hid_write

sd_close:
; # close file
add     r0, sp, #0x100
bl      sd_close_file
b       leave_func

; ######### f2 #########
write_mem:
; # init response buf
add     r0, sp, #0x50
mov     r1, #0
mov     r2, #0x40
bl      memset

; # set up memcpy() arguments
; # r0 = dst: *(hid data + 4)
; # r1 = src: (hid data + 0xc)
; # r2 = n *(hid data + 8)
ldr     r0, [r4, #4]
add.w   r1, r4, #0xc
ldr     r2, [r4, #8]

; # ensure that a maximum of 0x34 bytes
; # are written to memory at a time
mov     r5, #0
cmp     r2, #0x34
bhi     skip_write

mov     r5, r2
cpsid   i
bl      memcpy
cpsie   i

skip_write:
str     r5, [sp, #0x50]

; # send response
add     r0, sp, #0x50
mov     r1, #2000
bl      usb_hid_write

; # get next packet
mov     r1, #2000
mov     r0, r4
bl      usb_hid_read
cmp     r0, #0x40
bne     leave_func

; # go on until client aborts
ldrh    r3, [r4]
cmp     r3, #0xf2
beq     write_mem

b       leave_func

; ######### f1 #########
read_mem:
; # init response buf
add     r0, sp, #0x50
mov     r1, #0
mov     r2, #0x40
bl      memset

; # set up memcpy() arguments
; # r0 = dst: response buf + 4
; # r1 = src: *(hid data + 4)
; # r2 = n *(hid data + 8)
add     r0, sp, #0x54
ldr     r1, [r4, #0x4]
ldr     r2, [r4, #8]

; # ensure that a maximum of 0x3c bytes
; # are read from memory at a time
mov     r5, #0
cmp     r2, #0x3c
bhi     skip_copy

mov     r5, r2
cpsid   i
bl      memcpy
cpsie   i

skip_copy:
str     r5, [sp, #0x50]

; # send response
add     r0, sp, #0x50
mov     r1, #2000
bl      usb_hid_write

; # get next packet
mov     r1, #2000
mov     r0, r4
bl      usb_hid_read
cmp     r0, #0x40
bne     leave_func

; # go on until client aborts
ldrh    r3, [r4]
cmp     r3, #0xf1
beq     read_mem

; ########################
leave_func:
add     sp, sp, #0x200
pop.w   {r4-r8,pc}
"""

def pack_version(major, minor, patch):
    return ((major & 0xff) << 16) | ((minor & 0xff) << 8) | (patch & 0xff)

class Patch:
    def __init__(self, description, code, entry, max_size=0, symbols=None, thumbmode=True):
        self.description = description
        self.code = code
        # file offset of where to apply patch
        self.entry = entry
        self.max_size = max_size
        self.symbols = symbols
        self.thumbmode = thumbmode

fw_150_hid_patch = Patch(
    "Memory dumping/patching/code execution/file transfer via USB",
    new_hid_handler,
    # hid handler file offset / address
    0x00002D44,
    # hid handler end address - hid handler start address
    max_size = 0x000031EC - 0x00002D44,
    # symbols
    symbols = {
        "TRACKER_FIRMWARE_VERSION": pack_version(1,5,0),
        "CUSTOM_FIRMWARE_VERSION": pack_version(0,3,0),
        "memcpy": 0x00003384,
        "memset": 0x000A709C,
        "usb_hid_read": 0x0005D04,
        "usb_hid_write": 0x00005D78,
        "sd_create_file": 0x00019F70,
        "sd_write_file": 0x0001A038,
        "sd_close_file": 0x00019EEC
    },
    thumbmode = True
)

FIRMWARE_PATCHES = {
    "ce894299bc35996186528364951c901e": [fw_150_hid_patch]
}

def get_patches(md5digest):
    return FIRMWARE_PATCHES[md5digest] if md5digest in FIRMWARE_PATCHES else None