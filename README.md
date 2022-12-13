# Nuvoton UART ISP Loader

This project application has been prepared based on the ISP UART example found in the Nuvoton BSP files.

## Before Starting

In order to use it, the ISP_UART software must be written to the LDROM flash address.

File Selecting

![Alt text](./images/ldrom_isp.png?raw=true "Title")

Also, LDROM must be selected as the boot option.

![Alt text](./images/chip_settings.png?raw=true "Title")

## Usage

    usage: isp_loader.py [options] [arguments] ... [-f firmware.bin] [-h] [--help]
    
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
    -t , --timeout              : MCU Connection Timeout (ms)
    Arguments:
    --file      : Write MCU Bin File
    --timeout   : MCU Connection Timeout (ms)    # Default 1 second
    
    arg ...: arguments passed to program in sys.argv[1:]