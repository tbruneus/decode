#!/usr/bin/env python3
"""
This program takes a text file and can translate it using a dictionary read from a file.
The output can be printed to the console or saved in a txt or pdf file.

Text inside square brackets [] and angle brackets <> as well as in comments (starting with #) is left unchanged.
If multiple matches from the provided keys are possible, the longest applicable key will be used.

The translation dictionary has to contain key-value pairs delimited using "/", one pair per line.
Comments ("#" to the end of line) are allowed. Unicode characters can be specified in the following formats:
\\u0000, \\U00000000, \\N{char_name}.
"""

import argparse
import codecs
import io
import os
import re
import sys

__version__ = '1.1'
__author__ = 'TimB'
__license__ = 'MIT'


def read_file(filename: str) -> str:
    """
    Tries to read a file using the provided file name and returns contents as a string.
    Prints error message and exits if file can not be read.

    :param filename: The name of the file, can contain path
    :return: file contents as string
    """

    try:
        with io.open(filename, encoding='utf-8', newline='') as f:
            # Fix for inconsistent line breaks - all linebreaks are replaced with system default linebreaks
            return re.sub('\r*\n', os.linesep, f.read())
    except IOError as ex:
        print(ex)
        sys.exit(1)


def write_file(output_file: str, output: str) -> None:
    """
    Tries to write the provided string to a file.
    Prints error message and exits if file can not be written.

    :param output_file: Name/path of the output file
    :param output:      string to be written
    :return:            None
    """

    try:
        with io.open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
    except IOError as ex:
        print(ex)
        sys.exit(1)


# Return a dictionary with translation key-value pairs
def get_dictionary(dict_data: str, reverse: bool = False) -> dict:
    r"""
    Returns a dictionary with translation key-value pairs from a provided string.
    The pairs have to be delimited using "/", one pair per line. Comments ("#" to the end of line) are allowed.
    Unicode characters can be specified in the following formats: \\u0000, \\U00000000, \\N{char_name}.
    If reverse is true, the dictionary is reversed.
    NB: If the values in the original dict are not unique, some keys will be overwritten.

    :param dict_data:   String containing the key-value pairs
    :param reverse:     TRUE if the dict should be reversed
    :return:            dictionary of translation key-value pairs
    """

    # Un-escape escaped unicode characters (\u0000, \U00000000, \N{char_name}
    dict_data = re.sub(r'(\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|N{[^}]+}))',
                       lambda l: codecs.decode(l.group(), 'unicode_escape'), dict_data)

    kv_delimiter = '/'  # Character delimiting strings to be translated from and to
    comment_delimiter = '#'

    d = {}
    for line in dict_data.splitlines():
        if kv_delimiter in line and line[0] != comment_delimiter:  # Ignore comments and lines without delimiters
            (k, v) = line.split(comment_delimiter)[0].split(kv_delimiter)
            d[k.strip()] = v.strip()

    if len(d) == 0:
        raise ValueError('Error: The dictionary does not have a valid format (no key-value pairs found).\n'
                         'The dictionary has to be delimited using "' + kv_delimiter + '", one pair per line:\n' +
                         'a' + kv_delimiter + 'b\n'
                                              'c' + kv_delimiter + 'd\n'
                                                                   '...')

    if reverse:
        d = {v: k for k, v in d.items()}

    return d


def translate(text: str, transdict: dict) -> str:
    """
    Translates the provided text using the translation dictionary.
    Text inside square brackets [] and angle brackets <> as well as in comments (starting with #) is left unchanged.
    If multiple matches from the provided keys are possible, the longest applicable key will be used.

    :param text:        the text to be translated
    :param transdict:   the translation dictionary (key -> value)
    :return:            the translated text
    """

    # Compile regex matching ciphertext keys from dictionary, sorted by key length (longest first)
    ciphers_pattern = re.compile('|'.join(sorted(transdict.keys(), key=len, reverse=True)))

    # https://regexper.com/#(%5B%5E%3C%5C%5B%23%5D*)(((%3F%3A%3C%5B%5E%3E%5D*%3E)%7C(%3F%3A%5C%5B%5B%5E%5C%5D%5D*%5C%5D))*(%23.*%24)%3F)
    regex = r'([^<\[#]*)(((?:<[^>]*>)|(?:\[[^\]]*\]))*(#.*$)?)'

    # Decode the text by splitting the string into the part to be translated (group 0)
    # and the part to be ignored (cleartext and comments) (group 1).
    # In the first group, each key from the dictionary is replaced by the corresponding value.
    # The result is then concatenated with the unchanged second group.
    output = ''
    for match in re.findall(regex, text, flags=re.MULTILINE):
        output += ciphers_pattern.sub(
            lambda l: transdict[l.group()], match[0]) + match[1]
    return output


def remove_comments(text: str) -> str:
    """
    Removes comments from text. Comment lines are removed completely, including newline.

    :param text:    Input text
    :return:        Text without comments
    """
    return re.sub('(^[ \t]*#.*\n)|(#.*$)', '', text, flags=re.MULTILINE)


def remove_tags(text: str) -> str:
    """
    Removes tags and extracts text inside square brackets [] and angle brackets <>.
    Also removes 'cleartext' 'CLEARTEXT' or 'Cleartext' as well as language attributes
    (2 letter uppercase sequences following 'cleartext' and space(s) or dash(es)).

    :param text:    Input text
    :return:        Text with tags removed and text extracted
    """
    return re.sub(
        r'(?:(<[ ]*(?:(?:cleartext|CLEARTEXT|Cleartext)(?:[ -][A-Z]{2})?[ -]*)?)|(\[))((?(1)[^>]*|[^\]]*))(?(1)>|\])',
        r'\3', text, flags=re.MULTILINE)


def create_pdf(text: str, output_file: str, font_type: str, font_size: int,
               remove_cms: bool = True, remove_tgs: bool = True) -> None:
    """
    Creates a pdf file from a provided text.
    The font type and maximum font size can be provided.

    :param text:        Text to be written
    :param output_file: The name/path of the file to be written
    :param font_type:   The font to be used
    :param font_size:   The maximum font size (smaller size is used if the text does not fit on a page).
    :param remove_cms:  Remove comments (default true)
    :param remove_tgs:  Remove tags and extract text (default true)
    :return:            None
    """

    # Install reportlab if not installed
    try:
        import reportlab
    except ImportError:
        import pip
        pip.main(['install', 'reportlab', '--user'])
        import reportlab

    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus.flowables import KeepInFrame
    from reportlab.lib import pagesizes

    canvas = canvas.Canvas(output_file, pagesize=pagesizes.A4)

    # Get default fonts into a dictionary
    default_fonts = {font.upper(): font for font in canvas.getAvailableFonts()}

    # Get fonts in fonts/ directory into a dictionary
    program_fonts = {}
    for root, dirs, files in os.walk("fonts/"):
        for file in files:
            if file.endswith('.ttf') or file.endswith('.otf'):
                program_fonts[re.sub('\.[ot]tf$', '', file).upper()] = os.path.join(root, file)

    # Try to register font if not one of the defaults, fails otherwise
    try:
        # Check if font is in the fonts/ directory, register if true
        if font_type.upper() in program_fonts:
            pdfmetrics.registerFont(TTFont(font_type, program_fonts.get(font_type.upper())))
        # Else check if path to font is provided, register if true
        elif os.path.isfile(font_type) and font_type.endswith('.ttf') or font_type.endswith('.otf'):
            pdfmetrics.registerFont(TTFont(font_type, font_type))
        # Else check if the provided font is one of the default fonts, rename font
        elif font_type.upper() in default_fonts:
            font_type = default_fonts.get(font_type.upper())
        # Otherwise fail
        else:
            raise ValueError('Not a valid font file.')
    except (ValueError, reportlab.pdfbase.ttfonts.TTFError) as ex:
        print(ex)
        print('Can not use font: ' + os.path.abspath(font_type) + '.')
        print('You can use one of the default fonts:')
        [print(font, end=" ") for font in default_fonts.values()]
        print()
        print('or the fonts in the "fonts/" directory:')
        [print(font, end=" ") for font in program_fonts.keys()]
        print()
        print('Alternatively, you can provide a path to a TrueType font file.')
        sys.exit(1)

    # Styling
    stylesheet = getSampleStyleSheet()
    stylesheet.add(ParagraphStyle(name='custom', fontName=font_type, fontSize=font_size, leading=font_size * 1.3))

    # Positioning
    width, height = pagesizes.A4
    width -= 40  # drawing area width
    height -= 30  # drawing area height

    tlx = 30  # offset from left
    tly = height + 10  # offset from bottom

    # Remove comments and/or tags
    if remove_cms:
        text = remove_comments(text)
    if remove_tgs:
        text = remove_tags(text)

    # Pagination
    # Pages are split on empty lines (can contain whitespace)
    pages = re.split('(?:[\n][ \t]*){2,}', text.strip())
    for index, page in enumerate(pages):
        frame = KeepInFrame(width, height, [Paragraph(page.replace('\n', '<br/>\n'), stylesheet["custom"])])
        w, h = frame.wrapOn(canvas, width, height)
        frame.drawOn(canvas, tlx, tly - h)

        # Insert page break for all but the last page
        if index != len(pages):
            canvas.showPage()

    # Produce pdf
    canvas.save()


def main() -> None:
    """
    Program entry point, parses provided arguments.
    :return:    None
    """

    # Program arguments
    parser = argparse.ArgumentParser(prog=sys.argv[0], description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_file', help='input file')
    parser.add_argument('-d', '--dict_file', help='translation dictionary file')
    parser.add_argument('-r', '--reverse', action='store_true', help='reverse dictionary')
    parser.add_argument('-o', '--output_file', default='output',
                        help='output filename without extension (default: %(default)s)')
    parser.add_argument('-t', '--txt', action='store_true', help='write output to .txt file')
    parser.add_argument('-p', '--pdf', action='store_true', help='write output to .pdf file')
    parser.add_argument('-c', '--console', action='store_true', help='write output to console')
    parser.add_argument('--font_type', default='Quivira', help='set font type (default: %(default)s)')
    parser.add_argument('--font_size', default=30, type=int, help='set maximum font size (default: %(default)s)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__)
    args = parser.parse_args()

    # The output file path is the same as the input file path unless an absolute path is provided
    output_file = os.path.join(os.path.dirname(args.input_file), args.output_file)

    # Translate if dictionary is provided, otherwise output is the same as input.
    if args.dict_file:
        try:
            transdict = get_dictionary(read_file(args.dict_file), args.reverse)
            output = translate(read_file(args.input_file), transdict)
        except ValueError as e:
            print(e)
            sys.exit(1)
    else:
        output = read_file(args.input_file)

    if args.txt:
        write_file(output_file + '.txt', output)

    if args.pdf:
        create_pdf(output, output_file + '.pdf', args.font_type, args.font_size)

    if args.console:
        print(output)


if __name__ == '__main__':
    main()
