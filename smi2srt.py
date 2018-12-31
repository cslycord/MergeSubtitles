#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
from __future__ import print_function
from builtins import str

import os
import sys
import re
import logging
import io
from my_subtitle import MySubtitle

__author__ = "steven <mcchae@gmail.com>"
__date__ = "2014/02/15"
__version_info__ = (1, 3, 1)
__version__ = "{0}.{1}.{2}".format(__version_info__[0], __version_info__[1],
                                   __version_info__[2])
__license__ = "GCQVista's NDA"

'''

2014.2.25
Class for converting smi to srt including encoding.
It detect encoding of smi file and convert it to the user provided encoding.

Started : 2014/2/25
license: GPL

@version: 1.0.0
@author: steven <ramsessk@gmail.com>

SMI have this format!
===============================================================================

SRT have this format!
===============================================================================
1
00:00:12,000 --> 00:00:15,123
This is the first subtitle

2
00:00:16,000 --> 00:00:18,000
Another subtitle demonstrating tags:
<b>bold</b>, <i>italic</i>, <u>underlined</u>
<font color="#ff0000">red text</font>

3
00:00:20,000 --> 00:00:22,000  X1:40 X2:600 Y1:20 Y2:50
Another subtitle demonstrating position.
'''

'''
2018.10.04
Updated to be okay to use w/ Python 3
Changed underlying data structure to allow for use
w/ the associated srt merger I've written
Refactored code as best as I could to simplify
'''

try:
    import cchardet as detector
except ImportError:
    print('''cchardet python package not found. Please install it using
macports or pip''')
    sys.exit()

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
#            SMI to SRT
# -----------------------------------------------------------------------------


class smiItem(object):
    ''' smiItem class
    convert smi to srt format.
    '''
    __slots__ = ['MySub']

    def __init__(self):
        self.MySub = MySubtitle()

    @staticmethod
    def ms2ts(ms):
        MS_TO_HOURS = int(3600000)
        MS_TO_MINUTES = int(60000)
        MS_TO_SECONDS = int(1000)

        hours = ms // MS_TO_HOURS
        ms -= hours * MS_TO_HOURS
        minutes = ms // MS_TO_MINUTES
        ms -= minutes * MS_TO_MINUTES
        seconds = ms // MS_TO_SECONDS
        ms -= seconds * MS_TO_SECONDS
        s = '%02d:%02d:%02d,%03d' % (hours, minutes, seconds, ms)
        return s

    def convertSrt(self, outside=False):

        line = self.MySub.sub.subtitles

        # 1) remove new-line
        line = re.sub(r'\s+', ' ', line)
        # 2) remove web string like "&nbsp";
        line = re.sub(r'&[a-z]{2,5};', '', line)
        # 3) replace "<br>" with '\n';
        line = re.sub(r'(<br>)+', '\n', line, flags=re.IGNORECASE)
        # 4) find all tags
        fndx = line.find('<')
        if fndx >= 0:
            sb = line[0:fndx]
            contents = line[fndx:]
            while True:
                m = re.match(r'</?([a-z]+)[^>]*>([^<>]*)', contents,
                                   flags=re.IGNORECASE)
                if m is None:
                    break
                contents = contents[m.end(2):]
                if m.group(1).lower() in ['b', 'i', 'u']:
                    sb += m.string[0:m.start(2)]
                sb += m.group(2)
            final_line = ''
            for x in sb.splitlines(True):
                final_line += x.strip(' ')
            sb = final_line.rstrip('\n')
            self.MySub = MySubtitle(self.MySub.sub.start_times,
                                    self.MySub.sub.end_times,
                                    sb)

    def __repr__(self):
        s = '%d:%d:<%s>' % (self.MySub.sub.start_times,
                            self.MySub.sub.end_times,
                            self.MySub.sub.subtitles)
        return s

# -----------------------------------------------------------------------------


class SMI2SRT(smiItem):
    '''
    Convert smi file to srt format with the provided encoding format.

    public attribute:
    smi: smi file including .smi extension to be converted to srt format
    encoding: encoding for srt file to be saved
    titles: srt file contents in UTF-8 even though srt file to be written
              might have the different encoding
    convereted: status of conversion
    '''
    def __init__(self, smi, encoding):
        self.smifile = smi
        self.encoding = encoding
        self.titles = []
        self.converted = False
        self.srtfile = ""
        rndx = self.smifile.rfind('.')
        self.srtfile = '%s.srt' % self.smifile[0:rndx]
        self.mySubs = list()
        self.return_srt = list()

    def _del_rows(self, indices):
        for i in sorted(indices, reverse=True):
            del self.mySubs[i]

    def convert_smi(self, srtfile="", outside=False):
        ''' convert smi file to srt format with encoding provided.
        Default srt file name is same as smi except extention which is .srt
        return True or Flase
        '''
        if not self.smifile.lower().endswith('.smi'):
            logger.error("Not smi file:".format(self.smifile))
            return False

        if not os.path.exists(self.smifile):
            logger.error('Cannot find smi file {0}\n'.format(self.smifile))
            return False

        if srtfile == "":
            rndx = self.smifile.rfind('.')
            self.srtfile = '%s.srt' % self.smifile[0:rndx]
        else:
            self.srtfile = srtfile

        with open(self.smifile, mode="rb") as ifp:
            smi_sgml = ifp.read()

        chdt = detector.detect(smi_sgml)
        logger.info("{0} encoding is {1} with condidence {2}".
                    format(self.smifile, chdt['encoding'], chdt['confidence']))
        if chdt['encoding'].lower() != 'utf-8':
            try:
                # smi_sgml with chdt['encoding'] --convert--> unicode
                smi_sgml = str(smi_sgml, chdt['encoding'].lower())
            except UnicodeError:
                logger.error("Error : str(smi_sgml, chdt) in {0}".
                             format(self.smifile))
                return False

        # skip to first starting tag (skip first 0xff 0xfe ...)
        try:
            fndx = smi_sgml.find('<SYNC')
        except Exception as e:
            logger.debug(chdt)
            raise e
        if fndx < 0:
            logger.error("No <SYNC string found, maybe it is not smi file")
            return False
        smi_sgml = smi_sgml[fndx:]
        lines = smi_sgml.split('\n')

        sync_cont = ''
        next_start = None
        curr_start = None
        for line in lines:

            # http://stackoverflow.com/questions/11339955/python-string-encode-decode
            # convert smi contents to utf-8 for re
            if chdt['encoding'].lower() != 'utf-8':
                line = line.encode('UTF-8').decode('UTF-8')
            sndx = line.upper().find('<SYNC')
            if sndx >= 0:
                m = re.search(r'<sync\s+start\s*=\s*(\d+)>(.*)$', line,
                              flags=re.IGNORECASE)
                if not m:
                    logger.error('Invalid format tag of <Sync start=nnnn> \
                                 with {0}'.format(line))
                    continue        # ignore the wrong format line
                sync_cont += line[0:sndx]
                curr_start = next_start
                if not(curr_start is None):
                    curr_end = int(m.group(1))
                    curr_line = sync_cont
                    curr_sub = smiItem()
                    curr_sub.MySub = MySubtitle(curr_start,
                                                curr_end, curr_line)
                    self.mySubs.append(curr_sub)
                sync_cont = m.group(2)
                next_start = int(m.group(1))
            else:
                line = line.lstrip()
                sync_cont += line
        sub_index = 1
        remove_rows = []
        for i in range(len(self.mySubs)):
            current_sub = self.mySubs[i]
            current_sub.convertSrt()
            if (current_sub.MySub.sub.subtitles is None or
                len(current_sub.MySub.sub.subtitles) <= 0):
                remove_rows.append(i)
                continue
            else:
                mystr = str(sub_index) + '\n' + current_sub.MySub.timestamp() + '\n' + current_sub.MySub.data() + "\n"
                for s in mystr.strip().split('\n'):
                    self.titles.append(s)
                sub_index += 1
        self._del_rows(remove_rows)
        if outside is True:
            return(self.mySubs)

    def _print_srt(self):
        # open file with required encoding
        with io.open(self.srtfile, mode='w', encoding=self.encoding) as writer:
            for i in range(len(self.mySubs)):
                current = self.mySubs[i].MySub
                line = str(i+1) + '\n' + current.timestamp() + '\n' + current.data() + "\n\n"
                if(i == len(self.mySubs)-1):
                    line = line[:-2]
                writer.write(line)

            logger.info("Written file {0} in {1}".
                        format(self.srtfile, self.encoding))
            self.converted = True

    def analysis_srt(self):
        ''' Convert srt file to simplified list to use it easily.
        If smi is not converted srt yet, it will convert it first with
        default srt file name.

        list format to be returned would be:
        subtitles = [ ['1', '00:00 --> 00:00', 'hi steven'],
                      ['2', '00:01 --> 00:01', 'Im' fine!], ....
        subtitles[0] = ['1', '00:00 --> 00:00', 'hi steven']

        if error, return empty list
        '''
        if not self.converted:
            logger.info("smi file {0} not yet converted to srt".
                        format(self.smifile))
            self.convert_smi(self.srtfile)

        logger.info("Analysis a srt file ...")
        subtitle = []
        subtitles = []
        new_subtitle = False
        for line in self.titles:
            line = line.strip()
            line += '\n'
            if len(line) <= 1:      # consider '\n'
                continue
            isnumber = True
            try:
                int(line)
            except ValueError:
                isnumber = False
                pass

            if len(line.split()) == 1 and new_subtitle is False and isnumber:
                new_subtitle = True
                if len(subtitle) > 0:
                    subtitles.append(subtitle)
                    subtitle = []
                subtitle.append(line)
            else:
                new_subtitle = False
                if len(line) > 1:            # consider '\n'
                    subtitle.append(line)

        # save last one
        if len(subtitle) > 0:
            subtitles.append(subtitle)
        logger.info("{0} subtitles".format(len(subtitles)))

        return subtitles


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    if len(sys.argv) < 3:
        print("Usage:")
        print("$python smi2srt.py smifile encoding")
        sys.exit(1)
    obj = SMI2SRT(smi=sys.argv[1], encoding=sys.argv[2])
    obj.convert_smi()
    obj._print_srt()
    st = obj.analysis_srt()
    print(st[0])
    print(st[0][2])
