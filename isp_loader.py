import getopt
import sys
import time

import serial
from tqdm import tqdm


class ISPCommand:
    # UART PROTOCOL COMMANDS

    """
    This Arguments Gives Nuvoton ISP_UART Communication Examples
    """

    CMD_UPDATE_APROM = 0xA0
    CMD_UPDATE_CONFIG = 0xA1
    CMD_READ_CONFIG = 0xA2
    CMD_ERASE_ALL = 0xA3
    CMD_SYNC_PACKNO = 0xA4
    CMD_GET_FWVER = 0xA6
    CMD_RUN_APROM = 0xAB
    CMD_RUN_LDROM = 0xAC
    CMD_RESET = 0xAD
    CMD_CONNECT = 0xAE
    CMD_DISCONNECT = 0xAF

    CMD_GET_DEVICEID = 0xB1

    CMD_UPDATE_DATAFLASH = 0xC3
    CMD_WRITE_CHECKSUM = 0xC9
    CMD_GET_FLASHMODE = 0xCA

    CMD_RESEND_PACKET = 0xFF

    BUFFER_LEN = 64


class ISPLoader:
    def __init__(self, serial_port):
        self.isp_cmd = ISPCommand()
        self.isp_serial = serial.Serial(serial_port, 115200, timeout=0.5)
        self.isp_buffer = []
        self.write_mcu_buffer = []
        self.last_pack_buffer = []
        self.last_write_buffer = []
        self.mcu_connect_status = False
        self.package_no = 1
        self.firmware_version = 0x00
        self.device_id = 0x00
        self.config_0 = 0x00
        self.config_1 = 0x00
        self.progress = 0

    def updatePackageNumber(self):
        """
        updatePackageNumber update sending package number format

        :return: None
        """
        self.isp_buffer[4] = self.package_no & 0xFF
        self.isp_buffer[5] = (self.package_no >> 8) & 0xFF
        self.isp_buffer[6] = (self.package_no >> 16) & 0xFF
        self.isp_buffer[7] = (self.package_no >> 24) & 0xFF

    def bufferClear(self):
        """
        bufferClear buffer clear and append 64 byte 0x00

        :return: None
        """
        self.isp_buffer.clear()
        for i in range(self.isp_cmd.BUFFER_LEN):
            self.isp_buffer.append(0x00)

    def appendBufferEmptyValues(self, length):
        """
        appendBufferEmptyValues buffer clear and append length with argument to 0x00

        :param length: Determines the number of 0x00 to add
        :return: None
        """
        self.isp_buffer.clear()
        for i in range(length):
            self.isp_buffer.append(0x00)

    def connectMCU(self):  # +
        """
        connectMCU this function connect command sending to MCU and check response checksum

        :return: Connection True or False
        """
        if not self.mcu_connect_status:
            self.isp_serial.timeout = 0.01
            self.package_no = 1
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_CONNECT
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            if resp != b'' and resp is not None:
                if self.calculateChecksum(resp):
                    self.isp_serial.timeout = 0.5
                    self.mcu_connect_status = True
                else:
                    self.mcu_connect_status = False
            else:
                self.mcu_connect_status = False
        return self.mcu_connect_status

    def readConfigMCU(self):  # +
        """
        readConfigMCU this function read config registers (config0 - config1) command sending to MCU and check response checksum

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_READ_CONFIG
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            if resp != b'' and resp is not None:
                if self.calculateChecksum(resp):
                    self.config_0 = resp[8] | (resp[9] << 8) | (resp[10] << 16) | (resp[11] << 24)
                    self.config_1 = resp[12] | (resp[13] << 8) | (resp[14] << 16) | (resp[15] << 24)
                    return True
            else:
                return False
        else:
            return False

    def readDeviceIDMCU(self):  # +
        """
        readDeviceIDMCU this function read Device ID command sending to MCU and check response checksum

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_GET_DEVICEID
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            if resp != b'' and resp is not None:
                if self.calculateChecksum(resp):
                    self.device_id = resp[8] | (resp[9] << 8) | (resp[10] << 16) | (resp[11] << 24)
                    return True
            else:
                return False
        else:
            return False

    def readFirmwareVersionMCU(self):  # +
        """
        readFirmwareVersionMCU this function read Software Firmware Version command sending to MCU and check response checksum

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_GET_FWVER
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            if resp != b'' and resp is not None:
                if self.calculateChecksum(resp):
                    self.firmware_version = resp[8]
                    return True
            else:
                return False
        else:
            return False

    def resetMCU(self):  # +
        """
        resetMCU this function Reset MCU command sending to MCU

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_RESET
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            self.mcu_connect_status = False
            return True
        else:
            return False

    def runAPROM(self):  # +
        """
        runAPROM this function Run APROM command sending to MCU

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_RUN_APROM
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            self.mcu_connect_status = False
            return True
        else:
            return False

    def runLDROM(self):  # +
        """
        runAPROM this function Run LDROM command sending to MCU

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_RUN_LDROM
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            self.mcu_connect_status = False
            return True
        else:
            return False

    def syncMCU(self):  # +
        """
        syncMCU this function Synchronous Package Length Clearing command sending to MCU and check response checksum

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_SYNC_PACKNO
            self.package_no = 1
            self.updatePackageNumber()
            self.isp_buffer[8] = self.package_no
            self.isp_buffer[9] = (self.package_no >> 8) & 0xFF
            self.isp_buffer[10] = (self.package_no >> 16) & 0xFF
            self.isp_buffer[11] = (self.package_no >> 24) & 0xFF
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            if resp != b'' and resp is not None:
                if self.calculateChecksum(resp):
                    return True
            else:
                return False
        else:
            return False

    def eraseAllMCU(self):  # +
        """
        eraseAllMCU this function Erase All MCU command sending to MCU and check response checksum

        :return: Connection True or False
        """
        if self.mcu_connect_status:
            self.isp_serial.timeout = 5
            self.bufferClear()
            self.isp_buffer[0] = self.isp_cmd.CMD_ERASE_ALL
            self.package_no += 2
            self.updatePackageNumber()
            self.isp_serial.write(bytes(self.isp_buffer))
            # resp = self.isp_serial.read(self.isp_cmd.BUFFER_LEN)
            resp = self.isp_serial.readline()
            if resp != b'' and resp is not None:
                if self.calculateChecksum(resp):
                    for _ in tqdm(range(100), desc="Erase"):
                        time.sleep(0.005)
                    self.isp_serial.timeout = 0.5
                    return True
            else:
                return False
        else:
            return False

    def writeDataToBuffer(self, file_len, buffer_size, address):
        """
        writeDataToBuffer this function Address And File Length Info command sending to MCU and check response checksum

        :param file_len: Write File Length
        :param buffer_size: Clear Append Buffer Size
        :param address: Write Address
        """
        if self.mcu_connect_status:
            self.appendBufferEmptyValues(buffer_size)
            self.package_no += 2
            self.isp_buffer[0] = self.isp_cmd.CMD_UPDATE_APROM
            self.updatePackageNumber()
            self.isp_buffer[8] = address & 0xFF
            self.isp_buffer[9] = (address >> 8) & 0xFF
            self.isp_buffer[10] = (address >> 16) & 0xFF
            self.isp_buffer[11] = (address >> 24) & 0xFF
            self.isp_buffer[12] = file_len & 0xFF
            self.isp_buffer[13] = (file_len >> 8) & 0xFF
            self.isp_buffer[14] = (file_len >> 16) & 0xFF
            self.isp_buffer[15] = (file_len >> 24) & 0xFF

    def calculateChecksum(self, resp):
        """
        calculateChecksum calculate checksum function for ISP
        :param resp: Return to MCU Response
        :return: Calculate Checksum Result Result True or False
        """
        if len(resp) > 7: 
            checksum = 0
            for i in self.isp_buffer:
                checksum += i
            package_checksum = resp[0] | (resp[1] << 8)
            checksum %= 65536
            stat = False
            if package_checksum == checksum:
                stat = True
            if stat:
                returnPackageNo = (resp[7] << 24) | (resp[6] << 16) | (resp[5] << 8) | resp[4]
                if returnPackageNo != (self.package_no + 1):
                    stat = False
            return stat
        return False

    def writeBinaryMCU(self, file_name):
        """
        :param file_name:
        :return: Write MCU Status
        """
        file = open(file_name, mode="rb")
        file_content = file.read()
        file.close()
        self.bufferClear()
        file_size = len(file_content)
        self.isp_buffer.clear()
        self.start_byte_len = 16
        self.writeDataToBuffer(file_size, 16, address=0x00)
        self.isp_serial.timeout = 10
        for i in tqdm(range(file_size), desc="Program"):
            if self.start_byte_len % self.isp_cmd.BUFFER_LEN == 0:
                self.isp_serial.write(bytes(self.isp_buffer))
                resp = self.isp_serial.read(64)
                self.package_no += 2
                self.appendBufferEmptyValues(8)
                self.updatePackageNumber()
                self.start_byte_len = 8
                self.isp_buffer.append(file_content[i])
            else:
                self.isp_buffer.append(file_content[i])
            self.start_byte_len += 1
        if self.start_byte_len > 0:
            while self.isp_cmd.BUFFER_LEN - self.start_byte_len != 0:
                self.isp_buffer.append(0x00)
                self.start_byte_len += 1
            self.isp_serial.write(bytes(self.isp_buffer))
            resp = self.isp_serial.read(64)
            if self.calculateChecksum(resp):
                return True
            else:
                return False


def mcuLoadSoftware(binary_file, serial_port, erase_all_mcu_stat=True, reset_mcu_stat=True, mcu_connection_timeout=1000):
    """

    :param binary_file: MCU Write Binary File
    :param serial_port: MCU Write Serial Port
    :param erase_all_mcu_stat: MCU Write Binary File Before Erase All MCU
    :param reset_mcu_stat: MCU Write Binary After Reset MCU
    :param mcu_connection_timeout: MCU Connection Timeout
    :return: Return Result Dict
    """
    return_dict = {"Bin File": "Available", "Program": "Err"}

    isp_loader = ISPLoader(serial_port)
    return_dict["Port"] = serial_port

    timeout_counter = 0
    return_dict["Timeout"] = str(mcu_connection_timeout)
    while timeout_counter < mcu_connection_timeout:
        if isp_loader.connectMCU():
            if isp_loader.syncMCU():
                if erase_all_mcu_stat:
                    if isp_loader.eraseAllMCU():
                        return_dict["Erase"] = "OK"
                        erase_all_mcu_stat = False
                    else:
                        return_dict["Erase"] = "Checksum Error"
                if isp_loader.syncMCU():
                    return_dict["Program"] = "OK"
                    isp_loader.writeBinaryMCU(binary_file)
                    if reset_mcu_stat:
                        isp_loader.runAPROM()
                    return_dict["Timeout"] = "Not Timeout"
                    break
                else:
                    return_dict["Program"] = "Sync Error"
        time.sleep(0.001)
        timeout_counter += 10

    print(return_dict)
    return return_dict


def main(argv):
    usage = """
    usage: python.exe /path/to/loc/isp_loader.py [options] [arguments] ... [-p COM20] [-f firmware.bin] [-h] [--help]
    
    Options:
    -h , --help                 : Print Show Usage
    -e , --erase_all            : MCU All Erase Flash before programming
    -r , --reset                : Restart at the end of the process
    -l , --run_ldrom            : Run LDROM at the end of the process
    -a , --run_aprom            : Run APROM at the end of the process
    -d , --device_id            : Add print list Device ID end of the process
    -v , --firmware_version     : Add print list Firmware Version end of the process
    -c , --configs              : Add print list Device Configs Registers end of the process
    -f , --file=[firmware.bin]  : Write to MCU Bin File Selection
    -p , --port=[/COM, /dev/tty]: Write to MCU UART Port Selection
    -t , --timeout              : MCU Connection Timeout (ms)
    Arguments:
    --file      : Write MCU Bin File
    --port      : Write MCU Uart Port
    --timeout   : MCU Connection Timeout (ms)    # Default 1 second
    
    arg ...: arguments passed to program in sys.argv[1:]
    """
    binary_file = ""
    serial_port = ""
    mcu_connection_timeout = 1000  # Default
    serial_port_stat = False
    bin_file_stat = False
    run_aprom_stat = False
    run_ldrom_stat = False
    reset_mcu_stat = False
    erase_all_mcu_stat = False
    read_config_stat = False
    read_device_id_stat = False
    read_firmware_no_stat = False
    opts, args = getopt.getopt(argv, "p:t:f:acdehvrl", ["help", "file=", "erase_all", "reset", "run_ldrom", "run_aprom", "device_id", "firmware_version", "configs", "timeout=", "port="])
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(usage)
            sys.exit()
        elif opt in ("-e", "--erase_all"):
            erase_all_mcu_stat = True
        elif opt in ("-r", "--reset"):
            reset_mcu_stat = True
        elif opt in ("-l", "--run_ldrom"):
            run_ldrom_stat = True
        elif opt in ("-a", "--run_aprom"):
            run_aprom_stat = True
        elif opt in ("-d", "--device_id"):
            read_device_id_stat = True
        elif opt in ("-v", "--firmware_version"):
            read_firmware_no_stat = True
        elif opt in ("-c", "--configs"):
            read_config_stat = True
        elif opt in ("-f", "--file"):
            bin_file_stat = True
            binary_file = arg
        elif opt in ("-p", "--port"):
            serial_port_stat = True
            serial_port = arg
        elif opt in ("-t", "--timeout"):
            mcu_connection_timeout = int(arg)

    return_dict = {}
    if bin_file_stat:

        return_dict["Bin File"] = "Available"

        if serial_port_stat:
            isp_loader = ISPLoader(serial_port)
            return_dict["Port"] = serial_port
        else:
            return_dict["Port"] = "Not Detected"
            print(return_dict)
            sys.exit()

        timeout_counter = 0
        return_dict["Timeout"] = "Timeout"
        while timeout_counter < mcu_connection_timeout:
            if isp_loader.connectMCU():
                timeout_counter = 0
                if isp_loader.syncMCU():
                    if read_firmware_no_stat:
                        if isp_loader.readFirmwareVersionMCU():
                            return_dict["Firmware No"] = isp_loader.firmware_version
                    if read_device_id_stat:
                        if isp_loader.readDeviceIDMCU():
                            return_dict["Device ID"] = isp_loader.device_id
                    if read_config_stat:
                        if isp_loader.readConfigMCU():
                            return_dict["Config 0"] = isp_loader.config_0
                            return_dict["Config 1"] = isp_loader.config_1
                    if erase_all_mcu_stat:
                        if isp_loader.eraseAllMCU():
                            return_dict["Erase"] = "OK"
                        else:
                            return_dict["Erase"] = "Checksum Error"
                    if isp_loader.syncMCU():
                        return_dict["Program"] = "OK"
                        isp_loader.writeBinaryMCU(binary_file)
                        if reset_mcu_stat:
                            isp_loader.resetMCU()
                        elif run_aprom_stat:
                            isp_loader.runAPROM()
                        elif run_ldrom_stat:
                            isp_loader.runLDROM()
                        return_dict["Timeout"] = "Not Timeout"
                        break
                    else:
                        return_dict["Program"] = "Sync Error"
            time.sleep(0.001)
            timeout_counter += 10
    else:
        return_dict["Bin File"] = "Not Detected."

    print(return_dict)


if __name__ == "__main__":
    main(sys.argv[1:])
