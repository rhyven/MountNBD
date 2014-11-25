#!/usr/bin/python3
__author__ = 'Eric Light'
__copyright__ = "Copyleft 2014, Eric Light"
__license__ = "GPLv3"
__version__ = "2014-11-25 (v0.9)"
__maintainer__ = "Eric Light"
__email__ = "eric@ericlight.com"
__status__ = "Production"


from os import geteuid, path, mkdir
from subprocess import check_output, CalledProcessError
from argparse import ArgumentParser
import logging as log
# need to pause briefly after connecting the NBD device; otherwise it progresses before the file system is loaded
from time import sleep

global VERBOSE
MOUNT_POINT = r'/mnt/qcow'
LEGITIMATE_HEADERS = [b'QFI\xfb']  # QCOW2
NBD_LOCATION = r'/dev/nbd'


def startup():
    """
    Performs basic startup functions, including checking for root, checking arguments, etc

    """

    parser = ArgumentParser(description="Mounts a QEMU NBD-compatible disk image to a given location",
                            epilog="Currently, MountNBD will only accept a QCOW2 image file, though others can be"
                                   " added easily. MountNBD requires root privileges to function.")
    parser.add_argument('-v', '--verbose', action='count', help="print more detailed progress messages")
    parser.add_argument('--version', action='version', version='MountNBD version %s' % __version__)
    parser.add_argument('image_file', help="relative file path to the image file that you want to open")
    parser.add_argument('mount_point', nargs='?', help='where the image file should be mounted (default: %(default)s)',
                        default=MOUNT_POINT)

    parsed_arguments = parser.parse_args()

    # Check for Root access
    if geteuid() != 0:
        exit("You need to have root privileges to run this script.")

    return parsed_arguments


def is_QCOW(file_path):
    """
    Checks the first four bytes of the target image file, and returns True if those bytes match a QCOW2 file header

    """

    try:
        with open(file_path, 'rb') as binaryFile:
            if binaryFile.read(4) in LEGITIMATE_HEADERS:
                log.debug("%s appears to be a compatible format." % image_file)
                return True
    except IsADirectoryError:
        exit("You've asked to mount a whole directory as your image file - that won't work.")
    except Exception as error_details:
        exit("Wow, unexpected problem when trying to open the image file:\n\n%s" % error_details)


def check_image_file(file_to_check):
    """
    Makes sure that the image file exists, and checks that it is in the correct format

    """

    # Check that the target image file exists
    if not path.exists(file_to_check):
        exit("The target image file at %s doesn't seem to exist!" % file_to_check)

    # Confirm that the given file is a qcow image file
    if not is_QCOW(file_to_check):
        exit("The file at %s doesn't look like a QCOW2 image file." % file_to_check)

    log.debug("Image file looks OK!")


def load_nbd_driver():
    """
    Uses subprocess calls to load the NBD driver; then calls lsmod to ensure NBD has been correctly loaded

    """

    log.debug("Loading the NBD driver...")

    # Load NBD Driver
    try:
        check_output(['modprobe', 'nbd', 'max_part=16'])
    except CalledProcessError:
        exit("There was a problem loading the NBD driver. Perhaps you need to install qemu-kvm?")

    # Confirm NBD driver was successfully loaded
    try:
        check_output("lsmod | grep nbd", shell=True)
    except CalledProcessError:
        exit("There was a problem loading the NBD driver.  Try running modprobe nbd manually and see if it works.")

    log.debug("NBD driver loaded successfully")


def mount_devices(target_nbd_device):
    """
    Performs functions required to mount the NBD device to the file system

    Creates the desired mount point if it doesn't exist;
    Ensures nothing is already mounted at the mount point;
    Mounts the appropriate NBD device at the desired mount point;

    """
    log.debug("Trying to mount %s at %s" % (target_nbd_device, MOUNT_POINT))

    # Create mount point if it doesn't already exist
    if not path.exists(MOUNT_POINT):
        log.warning("Creating the mount point at %s" % MOUNT_POINT)
        mkdir(MOUNT_POINT)

    # Check MOUNT_POINT isn't already mounted
    if path.ismount(MOUNT_POINT):
        mounted_on = check_output("mount | grep %s | cut -f 1 -d ' '" % MOUNT_POINT, shell=True)
        exit("The target path is already mounted on %sPlease un-mount this path first." % mounted_on.decode())

    # Mount nbd_device_to_mount to MOUNT_POINT
    try:
        # need to pause before mounting the NBD device, to prevent mount attempt before partitions are recognised
        sleep(2)
        check_output(["mount", target_nbd_device, MOUNT_POINT])
    except CalledProcessError:
        exit("Everything seemed to go fine, right up until mounting %s at %s!" % (target_nbd_device, MOUNT_POINT))

    log.debug("%s successfully mounted at %s" % (target_nbd_device, MOUNT_POINT))


def connect_nbd(image_file_to_connect):
    """
    Connect /dev/nbdx to the image file

    First, loops through /dev/nbdx to find an nbd block device that isn't currently used.
    When an appropriate nbd device is found, try to connect the nbd device to the virtual drive image.

    """

    # Determine appropriate NBD device
    target_drive = ''
    nbd_drive = 0
    while target_drive == '':
        drive_size = check_output(["blockdev", "--getsize64", "/dev/nbd%s" % nbd_drive])
        if int(drive_size) == 0:
            # Found an empty NBD device
            target_drive = '/dev/nbd' + str(nbd_drive)
            log.debug("nbd%s is empty; using %s as the target drive." % (nbd_drive, target_drive))
        else:
            log.info("nbd%s is already mapped to a file; trying the next one..." % nbd_drive)
            nbd_drive += 1

    # Connect NBD device to appropriate point
    try:
        check_output(["qemu-nbd", "--connect=%s" % target_drive, image_file_to_connect])
        log.debug("Successfully connected %s to %s." % (target_drive, image_file_to_connect))
    except CalledProcessError:
        exit("There was a problem when connecting qemu-nbd to the destination file at %s." % image_file_to_connect)

    return target_drive


if __name__ == "__main__":

    cli_args = startup()
    MOUNT_POINT = cli_args.mount_point
    image_file = cli_args.image_file

    if cli_args.verbose:
        VERBOSE = True
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        log.debug("Basic startup complete.  Giving verbose output.")
    else:
        VERBOSE = False
        log.basicConfig(format="%(levelname)s: %(message)s")

    log.debug("Destination mount point is at %s" % MOUNT_POINT)
    check_image_file(image_file)
    load_nbd_driver()
    nbd_device_to_mount = connect_nbd(image_file)
    #TODO - stop assuming first partition
    mount_devices(nbd_device_to_mount + "p1")  # Assumes first partition
    print("%s successfully mounted at %s" % (image_file, MOUNT_POINT))
    if VERBOSE:
        print("\n\nWhen you're finished, run the following to unmount and disconnect the drives:\n")
        print("\tsudo umount %s && sudo qemu-nbd -d %s" % (MOUNT_POINT, nbd_device_to_mount))
        print("\n\tOptionally, use sudo rmmod nbd to unload the NBD driver from memory")
