"""
Hash calculation utilities for files and directories.
"""
import os
import hashlib

BLOCK_SIZE = 4096


def file_checksum(file_name):
    """

    Parameters
    ----------
    file_name: file name of the file for which md5 checksum is required.

    Returns
    -------
    md5 checksum of the given file.

    """
    with open(file_name, "rb") as file_handle:
        md5 = hashlib.md5()

        # Save current cursor position and reset cursor to start of file
        curpos = file_handle.tell()
        file_handle.seek(0)

        buf = file_handle.read(BLOCK_SIZE)
        while buf:
            md5.update(buf)
            buf = file_handle.read(BLOCK_SIZE)

        # Restore file cursor's position
        file_handle.seek(curpos)

        return md5.hexdigest()


def dir_checksum(directory, followlinks=True):
    """

    Parameters
    ----------
    directory : A directory with an absolute path
    followlinks: Follow symbolic links through the given directory

    Returns
    -------
    md5 checksum of the directory.

    """
    md5_dir = hashlib.md5()
    # Walk through given directory and find all directories and files.
    for dirpath, _, filenames in os.walk(directory, followlinks=followlinks):
        # Go through every file in the directory and sub-directory.
        for filepath in [os.path.join(dirpath, filename) for filename in filenames]:
            # Look at filename and contents.
            # Encode file's checksum to be utf-8 and bytes.
            md5_dir.update(filepath.encode("utf-8"))
            filepath_checksum = file_checksum(filepath)
            md5_dir.update(filepath_checksum.encode("utf-8"))
    return md5_dir.hexdigest()
