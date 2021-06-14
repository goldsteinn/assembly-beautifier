#! /usr/bin/env python3

import os
import sys
import argparse
import datetime
import json
import textwrap
import copy

parser = argparse.ArgumentParser(
    description="Simple asm formatter for glibc x86_64")
parser.add_argument("--file",
                    action="store",
                    default=None,
                    help="File to parse")
parser.add_argument("-l",
                    action="store_true",
                    default=None,
                    help="Parse from stdin")

parser.add_argument("--no-indent",
                    action="store_true",
                    default=False,
                    help="Turn off #define indentation")

parser.add_argument("--width",
                    action="store",
                    default="",
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


def make_tmp_objdump(config, lines):
    if config.verify_objfile is False:
        return None
    date_marker = str(datetime.datetime.now()).replace(" ", "-").replace(
        ":", "-").replace(".", "-")
    tmpfname = ".tmp-objdump-" + date_marker + ".S"
    assert os.path.exists(
        tmpfname) is False, "tmpfile already exists with same name: {}".format(
            tmpfname)
    assert os.path.exists(
        tmpfname +
        ".o") is False, "tmpfile already exists with same name: {}.o".format(
            tmpfname)

    try:
        tmpfile = open(tmpfname, "w+")
        for line in lines:
            tmpfile.write(line + "\n")
        tmpfile.flush()
        tmpfile.close()
        ret = os.system("gcc -c {} -o {}.o {}".format(tmpfname, tmpfname,
                                                      "> /dev/null 2>&1"))
        # Let this fail silently imo
        if ret != 0:
            os.system("rm -f {} {}".format(tmpfname, "> /dev/null 2>&1"))
            os.system("rm -f {}.o".format(tmpfname, {}))
            return None
        ret = os.system("objdump -d {}.o > {} {}".format(
            tmpfname, tmpfname, "2>&1"))
        os.system("rm -f {}.o {}".format(tmpfname, "> /dev/null 2>&1"))
        if ret != 0:
            os.system("rm -f {}".format(tmpfname, "> /dev/null 2>&1"))
            return None

        return tmpfname

    except IOError:
        os.system("rm -f {}".format(tmpfname))
        return ""


def verify_tmp_objdump(config, old_fname, lines):
    if config.verify_objfile is False or old_fname is None:
        return

    new_fname = make_tmp_objdump(config, lines)
    error = False
    if new_fname is None or new_fname == "":
        error = True

    old_lines = []
    new_lines = []
    try:
        if error is False:
            start = False
            for line in open(old_fname):
                if "Disassembly" in line:
                    start = True
                if start is True:
                    old_lines.append(line)
            start = False
            for line in open(new_fname):
                if "Disassembly" in line:
                    start = True
                if start is True:
                    new_lines.append(line)

    except IOError:
        os.system("rm -f {} {}".format(new_fname, "> /dev/null 2>&1"))
        os.system("rm -f {} {}".format(old_fname, "> /dev/null 2>&1"))
        assert False, "IO Error verify objdump files"

    os.system("rm -f {} {}".format(new_fname, "> /dev/null 2>&1"))
    os.system("rm -f {} {}".format(old_fname, "> /dev/null 2>&1"))

    if error is False:
        if len(old_lines) != len(new_lines):
            error = True
        for i in range(0, len(old_lines)):
            if error is True:
                break
            if old_lines[i] != new_lines[i]:
                error = True

    if error:
        print("##################################")
        print("ERROR: Formatter bug")
        print("The underlying objdump file changed after formatting")
        print("##################################")
        assert False


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
    for i in range(0, len(pieces) - 1):
        out += pieces[i] + seperator
    out += pieces[len(pieces) - 1]

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
        self.verify_objfile = False
        self.width = 64
        self.skip_header = True
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
                if "Objdump_Verify" in config_data:
                    self.verify_objfile = str2bool(
                        config_data["Objdump_Verify"])
                if "Skip_Header" in config_data:
                    self.skip_header = str2bool(config_data["Skip_Header"])
                if "Width" in config_data:
                    try:
                        self.width = int(config_data["Width"])
                    except ValueError:
                        return
                if "Init_Indent" in config_data:
                    try:
                        self.initial_indent = int(config_data["Init_Indent"])
                    except ValueError:
                        return

            except IOError:
                return


def end_comment(line):
    line = line.rstrip().lstrip()
    spaces = "   "
    if "/*" in line:
        assert line[:2] == "/*"
        assert line[:2] + line[2:] == line

        spaces = "/* "
        line = line[2:]
    line = line.rstrip().lstrip()
    assert line[len(line) - 2:] == "*/", line
    assert line[:len(line) - 2] + line[len(line) - 2:] == line
    line = line[:len(line) - 2]
    line = line.rstrip().lstrip()
    if line[len(line) - 1:] != ".":
        line += "."
    return "\t" + spaces + line + "  */"


class Formatter():
    def __init__(self, conf):
        self.TABLEN = 8

        self.init_def_count = conf.initial_indent
        self.enable_indent = conf.padd_indent

        self.def_count = self.init_def_count + 1
        self.in_comment = False
        self.comment_text = ""
        self.wrap_width = conf.width

        self.first_line = not conf.skip_header
        self.skipping_first_comment = False
        assert conf.width == -1 or conf.width > 10

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
        original_line = line
        line = line.replace("\n", "").lstrip().rstrip()
        if len(line) == 0:
            return ""

        if self.first_line is False and line[:2] == "/*":
            self.first_line = True
            if "*/" not in line:
                self.skipping_first_comment = True
            return original_line.rstrip()
        else:
            self.first_line = False

        if self.skipping_first_comment is True:
            if "*/" in line:
                self.skipping_first_comment = False
            return original_line.rstrip()

        if self.wrap_width == -1:
            if self.in_comment is True:
                if "*/" in line:
                    self.in_comment = False
                    if "*/" == line:
                        return "\t */"
                    return end_comment(line)
                return "\t   " + line.rstrip().lstrip()
            # Handle start comment
            if "/*" in line:
                if "*/" not in line:
                    self.in_comment = True
                    return "\t" + line.rstrip().lstrip()
                else:
                    return end_comment(line)
        else:
            finish_comment = False
            if "/*" in line:
                assert self.in_comment is False
                assert self.comment_text == ""
                self.comment_text = line.rstrip().lstrip()
                if "*/" in line:
                    finish_comment = True
                else:
                    self.in_comment = True
                    return None

            elif self.in_comment is True:
                if self.comment_text != "":
                    self.comment_text += " "
                self.comment_text += line.rstrip().lstrip()

                if "*/" in line:
                    self.in_comment = False
                    finish_comment = True
                else:
                    return None

            if finish_comment is True:
                assert self.in_comment is False
                assert self.comment_text.count("/*") == 1
                assert self.comment_text.count("*/") == 1
                line = self.comment_text.lstrip().rstrip()
                self.comment_text = ""
                line = end_comment(line)
                line = textwrap.fill(line, width=self.wrap_width)

                lines = line.split("\n")
                line = "\t" + lines[0].lstrip().rstrip()
                if len(lines) != 1:
                    line += "\n"
                    for i in range(1, len(lines) - 1):
                        line += "\t   " + lines[i].lstrip().rstrip() + "\n"

                    if lines[len(lines) - 1] == "*/":
                        line += "\t */"
                    else:
                        line += "\t   " + lines[len(lines) -
                                                1].lstrip().rstrip()
                return line
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

        if ":" in line or ("END (" in line or "END(" in line or "END\t("
                           in line) or ("ENTRY (" in line or "ENTRY(" in line
                                        or "ENTRY\t(" in line):
            return fmt_pieces(pieces, "")

        if ".cfi_" in line:
            return "\t" + fmt_pieces(pieces, " ")

        extra = ""
        if ".section" not in line:
            tmp_pieces = []
            for i in range(0, len(pieces)):
                if pieces[i] == ",":
                    continue
                if "{" in pieces[i] and "}" in pieces[i] and len(
                        pieces[i]) < 8 and ("k" in pieces[i]
                                            or "z" in pieces[i]):
                    tmp_pieces[len(tmp_pieces) - 1] += pieces[i]
                else:
                    tmp_pieces.append(pieces[i].replace(",", ""))
            extra = ","
            pieces = tmp_pieces

        line = "\t" + pieces[0]
        if len(pieces) != 1:
            prefix = "\t"
            if len(pieces[0]) >= self.TABLEN:
                prefix = " "
            line += prefix + fmt_pieces(pieces[1:], extra + " ")
        return line


lines = []

args = parser.parse_args()
asm_fname = args.file
from_stdin = args.l
no_indent = args.no_indent
arg_width = args.width

assert asm_fname is not None or from_stdin is not None
assert asm_fname is None or from_stdin is None

config = Config(args.config)
if arg_width != "":
    try:
        config.width = int(arg_width)
    except ValueError:
        assert False, "width must be an integer"

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
    tmpfname = make_tmp_objdump(config, lines)
    assert tmpfname != "", "Error making objdump"

    lines_out = []

    formatter = Formatter(config)
    for line in lines:
        out = formatter.fmt_line(line)
        if out is not None:
            lines_out.append(out)

    verify_tmp_objdump(config, tmpfname, lines_out)

    assert formatter.valid()
    for line in lines_out:
        print(line)
