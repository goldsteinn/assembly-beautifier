#! /usr/bin/env python3

import os
import sys
import argparse
import datetime
import json

parser = argparse.ArgumentParser(
    description="Simple asm formatter for glibc x86_64")
parser.add_argument("--file",
                    action="store",
                    default=None,
                    help="File to parse")
parser.add_argument("-l",
                    action="store_true",
                    default=False,
                    help="Parse from stdin")

parser.add_argument("--no-indent",
                    action="store_true",
                    default=False,
                    help="Turn off #define indentation")

parser.add_argument("--config",
                    action="store",
                    default=None,
                    help="Config file")

parser.add_argument("--none",
                    action="store_true",
                    default=None,
                    help="Does nothing")


def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")


def make_backup(config, fname, lines):
    if config.backup_path is None or config.do_backup is False:
        return

    date_marker = str(datetime.datetime.now()).replace(" ", "-").replace(
        ":", "-").replace(".", "-")
    if fname is None:
        fname = date_marker
    else:
        fname += "-" + date_marker

    backup_path = config.backup_path
    backup_fname = "{}/{}".format(backup_path, fname)
    assert os.system("mkdir -p {}".format(backup_path)) == 0
    try:
        backup_file = open(backup_fname, "w+")
        for line in lines:
            backup_file.write(line)
        backup_file.flush()
        backup_file.close()
    except IOError:
        assert False, "Error making backup file: {}".format(backup_fname)


def fmt_pieces(pieces, seperator):
    out = ""
    for piece in pieces:
        out += piece + seperator

    return out.rstrip().lstrip()


class Config():
    def __init__(self, config_fname):
        self.config_fname = "/home/noah/.config/abf.json"
        if config_fname is not None:
            self.config_fname = config_fname

        # Defaults
        self.backup_path = None
        self.do_backup = False
        self.padd_indent = True
        self.initial_indent = 0
        if os.access(self.config_fname, os.R_OK) is True:
            try:
                config_file = open(self.config_fname, "r")
                config_data = json.load(config_file)
                if "Backup_Path" in config_data:
                    self.backup_path = config_data["Backup_Path"]
                if "Backup" in config_data:
                    self.do_backup = str2bool(config_data["Backup"])
                if "Padd_Indent" in config_data:
                    self.padd_indent = str2bool(config_data["Padd_Indent"])
                if "Init_Indent" in config_data:
                    try:
                        self.initial_indent = int(config_data["Init_Indent"])
                    except ValueError:
                        return

            except IOError:
                return


class Formatter():
    def __init__(self, conf):
        self.init_def_count = conf.initial_indent
        self.enable_indent = conf.padd_indent

        self.def_count = self.init_def_count + 1
        self.in_comment = False

    def incr_dc(self):
        if self.enable_indent is True:
            self.def_count += 1

    def decr_dc(self):
        if self.enable_indent is True:
            self.def_count -= 1

    def dc(self):
        if self.enable_indent is True:
            return self.def_count
        return self.init_def_count

    def valid(self):
        return (self.init_def_count +
                1) == self.def_count and self.in_comment is False

    def fmt_line(self, line):
        line = line.replace("\n", "").lstrip().rstrip()
        if len(line) == 0:
            return ""

        # Handle end comment
        if self.in_comment is True:
            if "*/" in line:
                self.in_comment = False
            if "*/" == line:
                return "\t " + line.rstrip().rstrip()
            return "\t" + "   " + line.rstrip().rstrip()
        # Handle start comment
        if "/*" in line:
            if "*/" not in line:
                self.in_comment = True
            return "\t" + line.rstrip().lstrip()

        pieces = line.split()
        if "#" in line:
            op = pieces[0]
            start = 1
            if len(pieces[0]) == 1:
                op = pieces[1]
                start = 2
            op = op.replace("#", "")

            if "endif" == op:
                self.decr_dc()
            pad_count = self.dc()
            if self.enable_indent is True and ("else" == op or "elif" == op):
                pad_count -= 1

            line = "#".ljust(pad_count) + op
            if op == "define":
                line += " " + fmt_pieces(pieces[start:], "\t")
            elif start != len(pieces):
                line += " " + fmt_pieces(pieces[start:], " ")
            if "ifdef" == op or "ifndef" == op or "if" == op:
                self.incr_dc()

            return line

        if ":" in line:
            return fmt_pieces(pieces, "")

        if "." in line:
            return "\t" + fmt_pieces(pieces, " ")

        line = "\t" + pieces[0]
        if len(pieces) != 1:
            line += "\t" + fmt_pieces(pieces[1:], " ")
        return line


lines = []

args = parser.parse_args()
asm_fname = args.file
from_stdin = args.l
no_indent = args.no_indent

assert asm_fname is not None or from_stdin is not None
assert asm_fname is None or from_stdin is None

config = Config(args.config)

if no_indent is True:
    config.padd_indent = False

if asm_fname is None:
    lines = sys.stdin.readlines()
else:
    asm_file = None
    try:
        assert os.access(asm_fname,
                         os.R_OK), "Error {} does not exist".format(asm_fname)
        asm_file = open(asm_fname, "r")
    except IOError:
        assert False, "Error opening {}".format(asm_fname)

    assert asm_file is not None, "Error opening {}".format(asm_fname)

    for line in asm_file:
        lines.append(line)
    asm_file.close()

make_backup(config, asm_fname, lines)

if len(lines) != 0:
    lines_out = []

    formatter = Formatter(config)
    for line in lines:
        lines_out.append(formatter.fmt_line(line))

    assert formatter.valid()
    for line in lines_out:
        print(line)
