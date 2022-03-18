import usb.core
import usb.util
import struct

class Tracker():
    def __init__(self):
        self.ep_in = None
        self.ep_out = None

    def open(self):
        # find Polyend Tracker
        dev = usb.core.find(idVendor=0x16d0, idProduct=0x0e9f)

        if dev is None:
            return False

        usb.util.claim_interface(dev, 3)
        # print("detected %s %s (%s)" % (dev.manufacturer, dev.product, dev.serial_number))

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        dev.set_configuration()

        # get an endpoint instance
        cfg = dev.get_active_configuration()
        intf = cfg[(3,0)]

        self.ep_in = usb.util.find_descriptor(
            intf,
            # match the first IN endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN)

        self.ep_out = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

        return self.ep_in != None and self.ep_out != None

    def read_mem(self, addr, count):
        data = b""
        offs = 0
        bytes_left = count
        try:
            while bytes_left:
                chunk_size = 0x3c if bytes_left > 0x3c else bytes_left
                if bytes_left % 1024 == 0:
                    print("Reading memory: %d%%" % (100.0 * (offs/count)),end="\r")
                pkt = struct.pack("<HHII52s", 0xf1, 0, addr+offs, chunk_size, b"")
                self.ep_out.write(pkt)
                buf = self.ep_in.read(0x40)
                bytes_read = struct.unpack("<I", buf.tobytes()[0:4])[0]
                if bytes_read != chunk_size:
                    data = None
                    break
                offs += chunk_size
                bytes_left -= chunk_size
                data += buf[4:chunk_size+4].tobytes()
        except:
            data = None
        pkt = struct.pack("<H", 0xff)
        pkt += b'\x00' * (0x40-len(pkt))
        self.ep_out.write(pkt)
        return data

    def write_mem(self, addr, data):
        success = True
        offs = 0
        total = len(data)
        bytes_left = total
        try:
            while bytes_left:
                chunk_size = 0x34 if bytes_left > 0x34 else bytes_left
                if bytes_left % 1024 == 0:
                    print("Writing memory: %d%%" % (100.0 * (offs/total)),end="\r")
                chunk = data[offs:offs+chunk_size]
                pkt = struct.pack("<HHII52s", 0xf2, 0, addr+offs, chunk_size, chunk)
                self.ep_out.write(pkt)
                buf = self.ep_in.read(0x40)
                bytes_written = struct.unpack("<I", buf.tobytes()[0:4])[0]
                if bytes_written != chunk_size:
                    data = None
                    break
                offs += chunk_size
                bytes_left -= chunk_size
        except:
            success = False
        pkt = struct.pack("<H62s", 0xff, b"")
        self.ep_out.write(pkt)
        return success

    def write_file(self, filename, data):
        """ length of filename currently restricted to 59 characters """
        if len(filename) > 59:
            return False
        success = True
        pkt = struct.pack("<HH59sb", 0xf5, 0, bytes(filename, "utf-8"), 0)
        self.ep_out.write(pkt)

        total = len(data)
        bytes_left=total
        offs = 0
        try:
            while bytes_left:
                chunk_size = 0x3c if bytes_left > 0x3c else bytes_left
                if bytes_left % 1024 == 0:
                    print("progress: %d%%" % (100.0 * (offs/total)),end="\r")
                chunk = data[offs:offs+chunk_size]
                pkt = struct.pack("<HH60s", 0xf6, chunk_size, chunk)
                self.ep_out.write(pkt)
                offs += chunk_size
                bytes_left -= chunk_size
                buf = self.ep_in.read(0x40)
                if buf[0] == 0xf6:
                    bytes_written = struct.unpack("<I", buf.tobytes()[4:8])[0]
                    if bytes_written != chunk_size:
                        success = False
                        break
                else:
                    # this shouldn't ever happen
                    raise ValueError("bug in write_file()")
        except:
            success = False
        # tell tracker to close file
        pkt = struct.pack("<H62s", 0xf7, b"")
        self.ep_out.write(pkt)
        return success

    def exec(self, addr, data=b""):
        pkt = struct.pack("<HHI56s", 0xf8, 0, addr, data)
        self.ep_out.write(pkt)
        data = self.ep_in.read(0x40)
        return data

    def brk(self):
        pkt = struct.pack("<HH60s", 0xfa, 0, b"")
        self.ep_out.write(pkt)
        data = self.ep_in.read(0x40)
        return data[0] == 0xfa

    def cont(self):
        pkt = struct.pack("<HH60s", 0xfb, 0, b"")
        self.ep_out.write(pkt)
        data = self.ep_in.read(0x40)
        return data[0] == 0xfb

    def get_version(self):
        """returns tuple of (tracker_fw_version, patch_version)"""
        pkt = struct.pack("<H62s", 0xf3, b"")
        self.ep_out.write(pkt)
        data = self.ep_in.read(0x40)
        if data[0] != 0xf3:
            return None
        ppatch, pminor, pmajor, _, cpatch, cminor, cmajor, _ = struct.unpack("bbbbbbbb", data[4:4+8])
        return ((pmajor, pminor, ppatch), (cmajor, cminor, cpatch))