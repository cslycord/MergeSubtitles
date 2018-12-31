#!/usr/bin/env python2
# author: Christopher Slycord

from __future__ import print_function
import re
import sys
import os
from my_subtitle import MySubtitle
from smi2srt import SMI2SRT
try:
    import cchardet
except ImportError:
    print('''cchardet python package not found. Please install it using
macports or pip''')
    sys.exit()
try:
    import chardet
except ImportError:
    print('''chardet python package not found. Please install it using
macports or pip''')
    sys.exit()

TIME_PATTERN = (r'\d{1,2}:\d{1,2}:\d{1,2},\d{1,5} --> '
                r'\d{1,2}:\d{1,2}:\d{1,2},\d{1,5}\r\n')


class Merger():
    """
    SRT Merger allows you to merge subtitle files, no matter what language
    are the subtitles encoded in. The result of this merge will be a new
    subtitle file which will display subtitles from each merged file.
    """
    def __init__(self,
                 output_file='subtitle_name.srt',
                 output_encoding='utf-8'):
        self.lines = []
        self.remove_rows = list()
        dirpath = os.path.dirname(output_file)
        self.output_path = dirpath if dirpath != '' else '.'
        self.output_name = os.path.basename(output_file)
        self.output_encoding = output_encoding
        # self.subtitles will be a list of all subs
        self.subtitles = list()

    def get_milliseconds(self, timestr, File, SubNumber):
        if len(timestr) != 12:
            print(File + " has an invalid timecode for an SRT file.")
            print("Have a look at subtitle number " + str(SubNumber))
            print("Exiting!")
            sys.exit(1)
        HRS = int(timestr[0:2])
        MINS = int(timestr[3:5])
        SECS = int(timestr[6:8])
        MIL_SECS = int(timestr[9:12])

        HRS_MS = int(3600000)
        MINS_MS = int(60000)
        SECS_MS = int(1000)

        return(HRS*HRS_MS+MINS*MINS_MS+SECS*SECS_MS+MIL_SECS)

    def _findOverlapping(self, CheckSubtitle):
        # returns the maximum position in the list of timestamps that are lower
        # than the one we are checking. Avoids needless looping

        first = 0
        last = len(self.subtitles)-1

        if (last < first):
            return first
        if CheckSubtitle <= self.subtitles[first]:
            return first
        if CheckSubtitle >= self.subtitles[last]:
            return last

        def do_search(Subtitle, low, high):
            if Subtitle >= self.subtitles[high]:
                return high
            if Subtitle <= self.subtitles[low]:
                return low
            if low >= high:
                return high
            middle = (low + high) // 2
            middle_sub = self.subtitles[middle]
            if middle_sub == Subtitle:
                return middle
            if middle_sub > Subtitle:
                return do_search(Subtitle, low, middle)
            return do_search(Subtitle, middle+1, high)

        position = do_search(CheckSubtitle, first, last)
        # position now has the position in the list that has the next highest
        # start time.
        # But the new subtitle to be inserted might start before the previous
        # subtitle ended
        keep_looking = True
        while position != first and keep_looking:
            if CheckSubtitle.start() < self.subtitles[position-1].end():
                position -= 1
            else:
                keep_looking = False
        return position

    def _add_lines(self, ListOfLines, position, remove=True):
        end = len(self.subtitles)

        if position > end:
            self.subtitles += ListOfLines
        else:
            if not remove:
                if position == end:
                    self.subtitles += ListOfLines
                else:
                    self.subtitles = self.subtitles[0:position] + \
                        ListOfLines + self.subtitles[position:]
            else:
                self.subtitles = self.subtitles[0:position] + \
                    ListOfLines + self.subtitles[position+1:]

    def _check_times(self,
                     CheckSubtitle,
                     SubNumber,
                     FirstFile=True):
        # timestamp = self.ms2TS(start_time) + " --> " + self.ms2TS(end_time)

        start_time = CheckSubtitle.start()
        end_time = CheckSubtitle.end()
        line_of_text = CheckSubtitle.data()

        # set original variables
        list_start = int(-1)
        list_end = int(-1)
        list_line = ""
        finished_adding = False
        while not finished_adding:
            i = self._findOverlapping(CheckSubtitle)

            # file = "First" if FirstFile == True else "Second"
            # print(file + "- Line Number:" + str(SubNumber))

            if len(self.subtitles) > 0:
                CurrentSubtitle = self.subtitles[i]

                list_start = CurrentSubtitle.start()
                list_end = CurrentSubtitle.end()
                list_line = CurrentSubtitle.data()

            added_rows = list()

            # check for overlaps
            # starts before
            if start_time < list_start:

                # 1) starts & ends before (or at) Current ending position
                # start_time     end_time    list_start        list_end
                # start_time                 end_time/list_start   list_end
                if end_time <= list_start:
                    new_row = MySubtitle(start_time,
                                         end_time,
                                         line_of_text)
                    added_rows.append(new_row)

                    self._add_lines(added_rows, i, remove=False)

                    finished_adding = True
                    break
                else:
                    # all of these start before and end sometime after
                    # the current one starts

                    # FIRST Add the stuff that occurs early
                    new_row = MySubtitle(start_time,
                                         list_start,
                                         line_of_text)
                    added_rows.append(new_row)

                    # 2) starts before & ends between
                    # start_time     list_start    end_time        list_end
                    if end_time < list_end:
                        new_row = MySubtitle(list_start,
                                             end_time,
                                             list_line+'\n'+line_of_text)

                        added_rows.append(new_row)

                        new_row = MySubtitle(end_time,
                                             list_end,
                                             list_line)

                        added_rows.append(new_row)

                        self._add_lines(added_rows, i, remove=True)

                        finished_adding = True
                        break
                    # 3) starts before & ends same
                    # start_time     list_start        list_end
                    #                                  end_time
                    if end_time == list_end:
                        new_row = MySubtitle(list_start,
                                             end_time,
                                             list_line+'\n'+line_of_text)
                        added_rows.append(new_row)

                        self._add_lines(added_rows, i, remove=True)

                        finished_adding = True
                        break

                    # 4 starts before & ends after
                    # start_time     list_start        list_end      end_time
                    if end_time > list_end:
                        new_row = MySubtitle(list_start,
                                             list_end,
                                             list_line+'\n'+line_of_text)
                        added_rows.append(new_row)

                        self._add_lines(added_rows, i, remove=True)

                        # update start time to be able to continue checking
                        start_time = list_end

                        finished_adding = False
            else:
                # either starts at same or after (start_time >= list_start)

                # Starts at same
                if start_time == list_start:

                    if end_time >= list_end:
                        new_row = MySubtitle(list_start,
                                             list_end,
                                             list_line+'\n'+line_of_text)
                        added_rows.append(new_row)

                        self._add_lines(added_rows, i, remove=True)

                        if end_time == list_end:
                            # starts same; ends same
                            # list_start     list_end
                            # start_time     end_time
                            finished_adding = True
                            break
                        else:
                            # starts same; ends after
                            # list_start       list_end  end_time
                            # start_time
                            start_time = list_end

                            finished_adding = False

                    else:
                        # starts same; ends before
                        # list_start   end_time    list_end
                        # start_time
                        new_row = MySubtitle(list_start,
                                             end_time,
                                             list_line+'\n'+line_of_text)
                        added_rows.append(new_row)

                        new_row = MySubtitle(end_time,
                                             list_end,
                                             list_line)
                        added_rows.append(new_row)

                        self._add_lines(added_rows, i, remove=True)

                        finished_adding = True
                        break
                else:
                    # starts after this one or between

                    if start_time >= list_end:
                        # starts after; so continue looking
                        break

                    # starts between
                    else:
                        # needed for all that are between
                        new_row = MySubtitle(list_start,
                                             start_time,
                                             list_line)
                        added_rows.append(new_row)

                        if end_time < list_end:
                            # starts & ends between
                            # list_start   start_time      end_time    list_end

                            new_row = MySubtitle(start_time,
                                                 end_time,
                                                 list_line+'\n'+line_of_text)
                            added_rows.append(new_row)

                            new_row = MySubtitle(end_time,
                                                 list_end,
                                                 list_line)
                            added_rows.append(new_row)

                            self._add_lines(added_rows, i, remove=True)

                            finished_adding = True
                            break

                        else:
                            # if end_time >= list_end
                            new_row = MySubtitle(start_time,
                                                 list_end,
                                                 list_line+'\n'+line_of_text)
                            added_rows.append(new_row)

                            self._add_lines(added_rows, i, remove=True)

                            if end_time == list_end:
                                # starts between ends same
                                # list_start   start_time    list_end
                                #                            end_time

                                # added above
                                finished_adding = True
                                break

                            if end_time > list_end:
                                # starts between ends after
                                # list_start   start_time   list_end  end_time

                                # timestamps added above

                                start_time = list_end

                                finished_adding = False
            if not finished_adding:
                CheckSubtitle = MySubtitle(start_time,
                                           end_time,
                                           line_of_text)
        if not finished_adding:
                # Looks like this goes after all the other time stamps
                new_row = MySubtitle(start_time,
                                     end_time,
                                     line_of_text)
                added_rows.append(new_row)

                self._add_lines(added_rows, len(self.subtitles), remove=False)

    def _split_dialogs(self,
                       dialogs,
                       subtitle,
                       FirstFile=True):
        for dialog in dialogs:
            if dialog.startswith('\r\n'):
                dialog = dialog.replace('\r\n', '', 1)
            if dialog.startswith('\n'):
                dialog = dialog[1:]
            if (
                    dialog == '' or
                    dialog == '\n' or
                    dialog.rstrip().lstrip() == ''):
                continue
            try:
                if dialog.startswith('\r\n'):
                    dialog = dialog[2:]
                SubNumber = dialog.split('\n', 2)[0]
                StartTime = dialog.split('\n', 2)[1].split('-->')[0].rstrip()
                StartTime = int(self.get_milliseconds(StartTime,
                                                      subtitle['address'],
                                                      SubNumber))
                EndTime = dialog.split('\n', 2)[1].split('-->')[1].lstrip()
                EndTime = int(self.get_milliseconds(EndTime,
                                                    subtitle['address'],
                                                    SubNumber))
            except Exception as e:
                continue
            texts = dialog.split('\n', 1)[1].split('\n')[1:]
            Text = ""
            for t in texts:
                t = t.lstrip()
                Text += t + '\n'
            if Text == '' or Text == '\n':
                continue
            Text = Text.strip('\n')
            sub = MySubtitle(StartTime, EndTime, Text)
            self._check_times(sub, SubNumber, FirstFile)

    def _encode(self, text):
        codec = self.output_encoding
        try:
            return bytes(text, encoding=codec)
        except Exception as e:
            print('Problem in "%s" to encoing by %s. \nError: %s'
                  % (repr(text), codec, e))
            return (b'An error has been occured in encoing by specifed '
                    b'`output_encoding`')

    def add(self, top_subtitle_address, bottom_subtitle_address):
        windows_line_ending = '\r\n'
        linux_line_ending = '\n'

        top_subtitle = {
            'address': top_subtitle_address,
            'dialogs': []
            }
        bottom_subtitle = {
                'address': bottom_subtitle_address,
                'dialogs': []
                }
        if top_subtitle_address.lower().endswith('.smi'):
            SMI = SMI2SRT(smi=top_subtitle_address,
                          encoding=self.output_encoding)
            converted_smi = SMI.convert_smi(outside=True)
            for i in range(len(converted_smi)):
                self._check_times(converted_smi[i].MySub, i+1, FirstFile=True)
            # self._add_lines(SMI.convert_smi(outside=True),
            #                 len(self.subtitles),
            #                 remove=False)
            # easy_srt = SMI.analysis_srt()
        else:
            with open(top_subtitle_address, 'rb') as file:
                data = file.read()
                cchdt = cchardet.detect(data)
                codec = cchdt['encoding']
                if cchdt['confidence'] < 0.99:
                    chdt = chardet.detect(data)
                    if chdt['confidence'] > cchdt['confidence']:
                        codec = chdt['encoding']
                data = data.decode(codec).replace(windows_line_ending,
                                  linux_line_ending)
                dialogs = re.split('\r\n\r|\n\n', data)
                top_subtitle['data'] = data
                top_subtitle['raw_dialogs'] = dialogs
                self._split_dialogs(dialogs, top_subtitle,
                                    FirstFile=True)

        if bottom_subtitle_address.lower().endswith('.smi'):
            SMI = SMI2SRT(smi=bottom_subtitle_address,
                          encoding=self.output_encoding)
            converted_smi = SMI.convert_smi(outside=True)
            for i in range(len(converted_smi)):
                self._check_times(converted_smi[i].MySub, i+1, FirstFile=False)
            # self._add_lines(SMI.convert_smi(outside=True),
            #                 len(self.subtitles),
            #                remove=False)
        else:
            with open(bottom_subtitle_address, 'rb') as file:
                data = file.read()
                cchdt = cchardet.detect(data)
                codec = cchdt['encoding']
                if cchdt['confidence'] < 0.99:
                    chdt = chardet.detect(data)
                    if chdt['confidence'] > cchdt['confidence']:
                        codec = chdt['encoding']
                data = data.decode(codec).replace(windows_line_ending,
                                  linux_line_ending)
                bottom_dialogs = re.split('\r\n\r|\n\n', data)
                bottom_subtitle['data'] = data
                bottom_subtitle['raw_dialogs'] = bottom_dialogs
                self._split_dialogs(bottom_dialogs, bottom_subtitle,
                                    FirstFile=False)

    def get_output_path(self):
        if self.output_path.endswith('/'):
            return self.output_path + self.output_name
        return self.output_path + '/' + self.output_name

    def ms2TS(self, timeMS):
        HRS_MS = int(3600000)
        MINS_MS = int(60000)
        SECS_MS = int(1000)

        ms = timeMS

        hours = ms // HRS_MS
        ms -= hours * HRS_MS
        minutes = ms // MINS_MS
        ms -= minutes * MINS_MS
        seconds = ms // SECS_MS
        ms -= seconds * SECS_MS
        s = '%02d:%02d:%02d,%03d' % (hours, minutes, seconds, ms)
        return s

    def _write(self):

        self.lines = []
        for i in range(len(self.subtitles)):
                current = self.subtitles[i]
                line = str(i+1) + '\n' + current.timestamp() + '\n' + \
                current.data() + '\n\n'
                if i == len(self.subtitles)-1:
                    line = line[:-1]
                line = line.encode(self.output_encoding)
                self.lines.append(line)

        if self.lines[-1].endswith(b'\x00\n\x00'):
            self.lines[-1] = self.lines[-1][:-3] + b'\x00'
        if self.lines[-1].endswith(b'\n'):
            self.lines[-1] = self.lines[-1][:-1] + b''
        import io
        with io.open(self.get_output_path(), 'w',
                     encoding=self.output_encoding) as output:
            output.buffer.writelines(self.lines)
            print("'%s'" % (output.name), 'created successfully.')


if __name__ == '__main__':
    if (len(sys.argv) < 4) or (len(sys.argv) > 5):
        print("Usage:")
        print("$python srtmerger top_sub.srt bottom_sub.srt output.srt \
              [output_encoding]")
        sys.exit(1)
    else:
        if len(sys.argv) == 5:
            encoding = sys.argv[4]
        else:
            encoding = "utf-8"
    m = Merger(output_file=sys.argv[3], output_encoding=encoding)
    m.add(sys.argv[1], sys.argv[2])
    m._write()
