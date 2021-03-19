#!/usr/bin/python3

import time
import os
import logging
from configparser import RawConfigParser
from watchdog.observers import Observer
from watchdog.events import \
    FileSystemEventHandler, \
    DirDeletedEvent, \
    DirMovedEvent, \
    FileDeletedEvent, \
    FileModifiedEvent, \
    FileMovedEvent

CMD_UNMOUNT = "modprobe -r g_mass_storage"
CMD_SYNC = "sync"

#WATCH_PATH = "/mnt/usb-3dp"
ACT_EVENTS = [
    DirDeletedEvent,
    DirMovedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent]
ACT_TIME_OUT = 3

class DirtyHandler( FileSystemEventHandler ):

    def __init__(self):
        self._dirty = False
        self._dirty_time = 0
        self._path = None

    def on_any_event(self, event):
        if type( event ) in ACT_EVENTS:
            self._dirty = True
            self._dirty_time = time.time()

    @property
    def dirty( self ):
        return self._dirty

    @property
    def dirty_time( self ):
        return self._dirty_time

    def reset(self):
        self._dirty = False
        self._dirty_time = 0
        self._path = None

def main():

    config = RawConfigParser()
    config.read( '/etc/usbshare.ini' )
    cmd_mount = ' '.join( [
        'modprobe',
        'g_mass_storage',
        'file={}'.format( config.get( 'global', 'image' ) ),
        'stall=0',
        'ro=1'] )
    watch_path = config.get( 'global', 'watch' )
    log_fifo = config.get( 'global', 'logfifo' )

    logging.basicConfig( level=logging.DEBUG )
    logger = logging.getLogger( 'usbshare' )

    logger.info( 'mounting on %s', watch_path )
    os.system( cmd_mount )

    evh = DirtyHandler()
    observer = Observer()
    observer.schedule(evh, path=watch_path, recursive=True)
    observer.start()

    try:
        while True:
            while evh.dirty:
                time_out = time.time() - evh.dirty_time
                logger.debug( 'changes detected: %d', time_out )

                if time_out >= ACT_TIME_OUT:
                    os.system( CMD_UNMOUNT )
                    time.sleep( 1 )
                    os.system( CMD_SYNC )
                    time.sleep( 1 )
                    os.system( cmd_mount )
                    evh.reset()

                    time_str = time.strftime( '%H:%M:%S' )
                    if log_fifo:
                        with open( log_fifo, 'w' ) as fifo_io:
                            fifo_io.write( 'Mounted {}', time_str )

                    logger.info( 'remounted at %s', time_str )

                time.sleep(1)

            time.sleep(1)

    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if '__main__' == __name__:
    main()
