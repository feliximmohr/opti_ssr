"""
#todo
"""

from __future__ import print_function
import sys
import threading
import socket
from time import sleep
import numpy
from abc import ABCMeta, abstractmethod # for abstract classes and methods

from opti_network import opti_network
from ssr_network import ssr_network

class _Bridge(threading.Thread):
    """An abstract class which receives some data from optitrack and sends some
       other data to the ssr
    """

    __metaclass__ = ABCMeta

    def __init__(self, optitrack, ssr, data_limit=500, timeout=0.01, *args,
        **kwargs):
        # call contructor of super class (threading.Thread)
        super(_Bridge, self).__init__(*args, **kwargs)

        # event triggered to stop execution
        self._quit = threading.Event()

        # interfaces
        self._optitrack = optitrack
        self._ssr = ssr

        # storing older data
        self._data = []  # the data buffer itself
        self._data_limit = data_limit  # maximum number of entries
        self._data_lock = threading.Lock()  #  mutex to block access
        self._data_available = threading.Event()  # event for new data

        # timeout
        self._timeout = timeout  # timeout in seconds

    def get_last_data(self):
        """Returns a list of data received from the OptiTrack system."""
        return self._data

    def clear_data(self):
        """Clears buffer"""
        if self._packet_available.is_set():
            with self._data_lock:  # lock the mutex
                self._packet_data = []
                self._packet_available.clear()

    def run(self):
        while not self._quit.is_set():
            try:
                # get the data
                packet = self._receive()  # dummy data
            except socket.error:
                sleep(0.1)
            except (KeyboardInterrupt, SystemExit):
                self._quit.set()
            else:
                # save data
                with self._data_lock:
                    self._data.append(packet)
                    self._data = self._data[-self._data_limit:]
                self._data_available.set()
                # send data
                self._send(packet)

    def stop(self):
        self._quit.set()  # fire event to stop execution

    @abstractmethod
    def _receive(self):
        return

    @abstractmethod
    def _send(self, packet):
        return

class HeadTracker(_Bridge):
    """A class for using the OptiTrack system as a head tracker for the SSR
    """

    def __init__(self, rb_id=0, *args, **kwargs):
        # call contructor of super class
        super(HeadTracker, self).__init__(*args, **kwargs)
        # selects which rigid body from OptiTrack is the head tracker
        self._rb_id = rb_id

    def _receive(self):
        rigid_body = self._optitrack.get_rigid_body(self._rb_id)
        # position
        pos = rigid_body.position
        # yaw-pitch-roll angles
        q = _Quaternion(rigid_body.orientation)
        ypr = q.yaw_pitch_roll
        #
        return pos, ypr

    def _send(self, rigid_body):
        _, ypr = rigid_body
        self._ssr.ref_orientation(angle*180/np.pi)

class LocalWFS(_Bridge):
    """
    #TODO
    """
    def __init__(self, N=64, R=1.00, rb_id=0, *args, **kwargs):
        # call contructor of super class
        super(LocalWFS, self).__init__(optitrack, ssr, *args, **kwargs)
        # selects which rigid body from OptiTrack is the tracker
        self._rb_id = rb_id
        self._N = N
        self._R = R

        self._create_virtual_sources()

    def _receive(self):
        # get position data from Motive
        x, y, z = self._optitrack.get_rigid_body_position()[0]
        # z-coordinate of Motive is the y-coordinate of the SSR
        # evtl. -x
        return [x, y, z]

    def _send(self, center)
        # calculation of source positions in a circular array
        alpha = np.linspace(0, 2 * np.pi, self._N, endpoint=False)
        src_pos = np.zeros((self._N, len(center)))
        src_pos[:, 0] = self._R * np.cos(alpha)
        src_pos[:, 1] = self._R * np.sin(alpha)
        src_pos += center
        # sending position data to SSR; number of source id depends on number of existing sources
        for src_id in range(1, self._N+1):
            self._ssr.set_src_position(src_id, src_pos[src_id-1, 0], src_pos[src_id-1, 1])

