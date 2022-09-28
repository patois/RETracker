import struct

# TODO: optimize, annotate
handle_raw_hid = """
; #######################
; # entry:

    push.w  {r4,lr}

    mov     r2, #0x40
    mov     r4, r0
    mov     r1, #0
    bl      memset

    mov     r1, #0
    mov     r0, r4
    bl      usb_hid_read

    cmp     r0, #0
    ble     handler_exit

    mov     r0, r4
    bl      handle_cmd

handler_exit:
    pop.w   {r4,pc}

; #######################
; # handle_cmd()
; # input: r0 = ptr to hid buffer
; #
; # TODO: jmptables w/ keystone
handle_cmd:
    push.w  {r4,lr}

    mov     r4, r0

    ldrh    r3, [r4]
    cmp     r3, #0xf1
    blo     exit_cmdhandler
    bne     check_write

    mov     r0, r4
    bl      handle_readmem_cmd
    b       exit_cmdhandler

check_write:
    cmp     r3, #0xf2
    bne     check_getver

    mov     r0, r4
    bl      handle_writemem_cmd
    b       exit_cmdhandler

check_getver:
    cmp     r3, #0xf3
    bne     check_sdwrite

    bl      handle_getver_cmd
    b       exit_cmdhandler

check_sdwrite:
    ; # handle_sdwrite_cmd uses both f5 and f6
    cmp     r3, #0xf5
    bne     check_exec

    mov     r0, r4
    bl      handle_sdwrite_cmd
    b       exit_cmdhandler

check_exec:
    cmp     r3, #0xf8
    bne     check_break

    mov     r0, r4
    bl      handle_exec_cmd
    b       exit_cmdhandler

check_break:
    cmp     r3, #0xfa
    bne     check_cont
    mov     r0, r4
    bl      handle_brk_cmd
    b       exit_cmdhandler

check_cont:
    mov     r0, #0xfb
    bl      send_response

exit_cmdhandler:
    pop.w   {r4,pc}


; #######################
; 
handle_brk_cmd:
    push.w  {r5-r6,lr}

    mov     r4, r0

    mov     r0, #0xfa
    bl      send_response

wait_client:
    mov     r1, #2000
    mov     r0, r4
    bl      usb_hid_read

    cmp     r0, #0
    ble     wait_client

    ldrh    r1, [r4]
    cmp     r1, #0xfb
    beq     ret_brk

    cmp     r1, #0xfa
    bne     do_handle
    mov     r0, r1
    bl      send_response
    b       wait_client

do_handle:
    mov     r0, r4
    bl      handle_cmd
    b       wait_client

ret_brk:
    mov     r0, r1
    bl      send_response

    pop.w   {r5-r6,pc}

; # TODO
send_response:
    push.w  {r5, lr}
    sub     sp, sp, #0x50

    mov     r5, r0

    mov     r2, #0x40
    mov     r0, sp
    mov     r1, #0
    bl      memset

    str     r5, [sp]
    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write

    add     sp, sp, #0x50
    pop.w   {r5, pc}

; ########## f3 #########
handle_getver_cmd:
    push.w  {r4-r6,lr}
    sub     sp, sp, #0x50

    ; # return version information
    ; # init response buf
    mov     r2, #0x40
    mov     r0, sp
    mov     r1, #0
    bl      memset

    ; # return 0xf3, tracker version, custom firmware version
    mov     r3, #0xf3
    str     r3, [sp]
    ldr     r5, =TRACKER_FIRMWARE_VERSION
    ldr     r6, =CUSTOM_FIRMWARE_VERSION
    strd    r5, r6, [sp, #4]
    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write

    add     sp, sp, #0x50
    pop.w   {r4-r6,pc}

; ########## f8 #########
handle_exec_cmd:
    push.w  {r4-r6,lr}
    sub     sp, sp, #0x50

    ; # HID input buf
    mov     r4, r0

    ; # init response buf
    mov     r2, #0x40
    mov     r0, sp
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
    add     r1, sp
    blx     r5

    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write

    add     sp, sp, #0x50
    pop.w   {r4-r6,pc}

; ######### f5 #########
handle_sdwrite_cmd:
    push.w  {r4-r6,lr}
    sub     sp, sp, #0x160

    mov     r4, r0

    ; # init reponse buf
    mov     r2, #0x40
    mov     r0, sp
    mov     r1, #0
    bl      memset

    ; # init fd struct
    mov     r2, #0x104
    add     r0, sp, #0x50
    mov     r1, #0
    bl      memset

    ; # create file
    mov     r2, #0xb
    add     r1, r4, #4
    add     r0, sp, #0x50
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
    add     r0, sp, #0x50
    add     r1, r4, #0x4
    ldrh    r2, [r4, #0x2]
    mov     r6, r2
    bl      sd_write_file
    cmp     r0, #0
    ble     sd_err

    ; # return number of bytes written
    strd    r5, r6, [sp]
    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write
    b       read_data

sd_err:
    ; # return 0xf6, 0 (error)
    mov     r5, #0xf6
    mov     r6, #0x00
    strd    r5, r6, [sp]
    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write

sd_close:
    ; # close file
    add     r0, sp, #0x50
    bl      sd_close_file

    add     sp, sp, #0x160
    pop.w   {r4-r6,pc}

; ######### f2 #########
handle_writemem_cmd:
    push.w  {r4-r6,lr}
    sub     sp, sp, #0x50

    mov     r4, r0

write_more:
    ; # init response buf
    mov     r0, sp
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

    ; # copy a maximum number of
    ; #0x3c bytes at a time
    mov     r5, #0
    cmp     r2, #0x34
    bhi     skip_write

    mov     r5, r2
    cpsid   i
    bl      memcpy
    cpsie   i

skip_write:
    str     r5, [sp]

    ; # send response
    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write

    ; # get next packet
    mov     r1, #2000
    mov     r0, r4
    bl      usb_hid_read
    cmp     r0, #0x40
    bne     ret_write

    ; # go on until client aborts
    ldrh    r3, [r4]
    cmp     r3, #0xf2
    beq     write_more

ret_write:
    add     sp, sp, #0x50
    pop.w   {r4-r6,pc}

; ######### f1 #########
handle_readmem_cmd:
    push.w  {r4-r6,lr}
    sub     sp, sp, #0x50

    mov     r4, r0

read_more:
    ; # init response buf
    mov     r0, sp
    mov     r1, #0
    mov     r2, #0x40
    bl      memset

    ; # set up memcpy() arguments
    ; # r0 = dst: response buf + 4
    ; # r1 = src: *(hid data + 4)
    ; # r2 = n *(hid data + 8)
    add     r0, sp, #4
    ldr     r1, [r4, #0x4]
    ldr     r2, [r4, #8]

    ; # copy a maximum number of
    ; #0x3c bytes at a time
    mov     r5, #0
    cmp     r2, #0x3c
    bhi     skip_copy

    mov     r5, r2
    cpsid   i
    bl      memcpy
    cpsie   i

skip_copy:
    str     r5, [sp]

    ; # send response
    mov     r0, sp
    mov     r1, #2000
    bl      usb_hid_write

    ; # get next packet
    mov     r1, #2000
    mov     r0, r4
    bl      usb_hid_read
    cmp     r0, #0x40
    bne     ret_read

    ; # go on until client aborts
    ldrh    r3, [r4]
    cmp     r3, #0xf1
    beq     read_more

ret_read:
    add     sp, sp, #0x50
    pop.w   {r4-r6,pc}
"""

alt_color_scheme = "cmp r1, #0"

def pack_version(major, minor, patch):
    return ((major & 0xff) << 16) | ((minor & 0xff) << 8) | (patch & 0xff)

class PatchLoc:
    def __init__(self, code, entry, max_size=0, symbols=None, thumbmode=True):
        self.code = code
        # file offset of where to apply patch
        self.entry = entry
        self.max_size = max_size
        self.symbols = symbols
        self.thumbmode = thumbmode

class Patch:
    def __init__(self, description, PatchLocs):
        self.description = description
        self.PatchLocs = PatchLocs if isinstance(PatchLocs, list) else [PatchLocs]

fw_150_hid_patch = Patch(
    "Memory dumping/patching/code execution/file transfer via USB",
    PatchLoc(
        handle_raw_hid,
        # hid handler file offset / address
        0x00002D44,
        # hid handler end address - hid handler start address
        max_size = 0x000031EC - 0x00002D44,
        # symbols
        symbols = {
            "TRACKER_FIRMWARE_VERSION": pack_version(1,5,0),
            "CUSTOM_FIRMWARE_VERSION": pack_version(0,3,3),
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
)
fw_150_alt_color_patch = Patch(
    "Alternative color scheme",
    PatchLoc(
        alt_color_scheme,
        # file offset / address to patch
        0x00001f376,
        max_size = 2,
        # symbols
        symbols = {},
        thumbmode = True
    )
)

FIRMWARE_PATCHES = {
    "ce894299bc35996186528364951c901e": [fw_150_hid_patch, fw_150_alt_color_patch]
}

def get_patches(md5digest):
    return FIRMWARE_PATCHES[md5digest] if md5digest in FIRMWARE_PATCHES else None