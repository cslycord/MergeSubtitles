# -*- coding: utf-8 -*-
"""
Created on Tue Oct  2 18:26:02 2018

@author: christoper slycord
"""
import sys
from builtins import str
try:
    import typing
except ImportError:
    print('''typing python package not found. Please install it using
macports or pip''')
    sys.exit()

Subtitle = typing.NamedTuple('Subtitle', [('start_times', int),
                                          ('end_times', int),
                                          ('subtitles', str)])
    
class MySubtitle():
    __slots__ = ['sub']
    
    def __init__(self, start_time=-1, end_time=-1, line_of_text=""):
        self.sub = Subtitle(int(start_time),
                            int(end_time),
                            str(line_of_text))
        
    def __lt__(self, other):
        return self.sub.start_times < other.sub.start_times

    def __le__(self, other):
        return self.sub.start_times <= other.sub.start_times

    def __gt__(self, other):
        return self.sub.start_times > other.sub.start_times

    def __ge__(self, other):
        return self.sub.start_times >= other.sub.start_times

    def __eq__(self, other):
        return self.sub.start_times == other.sub.start_times

    def __ne__(self, other):
        return self.sub.start_times != other.sub.start_time

    def start(self):
        return self.sub.start_times

    def end(self):
        return self.sub.end_times

    def data(self):
        return self.sub.subtitles

    def set_start(self, time):
        self.sub.start_times = time

    def ms2TS(self, time_ms):
        hrs_ms = int(3600000)
        mins_ms = int(60000)
        secs_ms = int(1000)
        
        ms = time_ms
        
        hours = ms // hrs_ms
        ms -= hours * hrs_ms
        minutes = ms // mins_ms
        ms -= minutes * mins_ms
        seconds = ms // secs_ms
        ms -= seconds * secs_ms
        s = '%02d:%02d:%02d,%03d' % (hours, minutes, seconds, ms)
        return s

    def timestamp(self):
        return self.ms2TS(self.start()) + " --> " + self.ms2TS(self.end())

    def __repr__(self):
        s = '%d:%d:<%s>' % (self.sub.start_times,
                            self.sub.end_times,
                            self.sub.subtitles)
        return s