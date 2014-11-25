MountNBD
========

A simple script to mount a qemu-nbd compatible drive into a Linux filesystem

I built this app to help in my work, where we have Linux servers which host a number of virtual machines.  The virtual drives for the virtual machines are all in the QCOW2 file format, which is the recommended format at the moment.

However, restoring from backup (e.g. reading files directly from these virtual drives) can be a pain.

So, I finally wrote a piece of Python that does the job of loading all the drivers, and mounting the virtual drive for you.  I run it from the home folder on each server that hosts virtual machines.

Usage
=====

sudo ~/MountNBD.py [IMAGE FILE TO MOUNT]

The above will mount the file at the default location, which is /mnt/qcow.

You can then browse the backed up file system with:

cd /mnt/qcow/

It comes complete with --help and --verbose command-line arguments.

Please let me know if you:
a) use it
b) find it interesting
c) break it
d) all of the above
