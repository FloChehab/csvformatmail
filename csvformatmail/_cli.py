# Copyright 2019, Jean-Benoist Leger <jb@leger.tf>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import functools
import argcomplete
import argparse
import textwrap
import sys
import csvspoon

from csvformatmail.mail import Mailer, Mail


def parseargs():
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """
            A tool to format mails from csv and to send them.

            Mails are formatted as f-string with namespace from csv.
            """
        ),
        epilog=textwrap.dedent(
            """
            Example:
              - A template file can be:
                > From: Me <my-mail-address@example.org>
                > To: {email}
                > Subject: Your results
                >
                > Hi {name.capitalize()},
                >
                > You obtain the following result {result}, with the value {value:.1f}
                >
                > -- 
                > me
              - With a csv file containg columns email, name, result, value.
              - With the command:
                  %(prog)s template.txt -t value:float listing.csv
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version="", help=argparse.SUPPRESS
    )

    parser.add_argument(
        "-d",
        "--delim",
        dest="delim",
        default=",",
        help="Input delimiter. (default: ',')",
    )
    parser.add_argument(
        "-b",
        "--before",
        action="append",
        default=[],
        help="""
            Run the following code before evaluate the expression on each row.
            Can be specified multiple times. (e.g. "import math").
            """,
    )
    parser.add_argument(
        "-t",
        "--type",
        action="append",
        type=csvspoon.ColType,
        default=[],
        help="""
            Apply type conversion on specified command prior to expression. The
            argument must be a column name followed by a valid Python type. See
            "--before" to define non standard type. e.g. "a_column:int" or
            "a_column:float". This option can be specified multiple time to type
            different columns.
            """,
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="""
            SMTP host (default: localhost)
            """,
    )
    parser.add_argument(
        "--port",
        default=25,
        type=int,
        help="""
            SMTP port (default: 25)
            """,
    )

    parser.add_argument(
        "--without-confirm",
        action="store_true",
        help="""
            Send mails without confirmation.
            """,
    )

    parser.add_argument(
        "template",
        help="""
            Template file. Must contains header, a empty line, and mail content.
            Header must contains lines From, To and Subject. Other header (as
            Bcc) can be provided.
            Template can contain braces encapsuled python code, same as
            f-string, which are evaluated in the namespace of row.
            """,
        type=argparse.FileType("r"),
    )

    parser.add_argument(
        "inputcsv",
        help="""
            Input csv file. Must contains columns which are used in template.
            Typing can be applied, see '-t'. Delimiter can be changed, see -'d'.
            """,
        type=csvspoon.CsvFileSpec,
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    return args


def main():
    args = parseargs()
    template = args.template.read()
    input_csv = csvspoon.ContentCsv(filespec=args.inputcsv, delim=args.delim)
    fake_global = {"__name__": "__main__"}
    for before in args.before:
        ast = compile(before, "<string>", "exec")
        exec(ast, fake_global)
    for t in args.type:
        t.build_type(fake_global)
        input_csv.add_type(*t.get_coltype)
    mailer = Mailer(args.host, args.port)
    for row in input_csv.rows_typed:
        mail = Mail(template, row, fake_global)
        mailer.add_mail(mail)
    if args.without_confirm:
        mailer.send_mails()
    else:
        mailer.prompt()


if __name__ == "__main__":
    main()