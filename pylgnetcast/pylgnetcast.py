"""
Client library for the LG Smart TV running NetCast 3 or 4.

LG Smart TV models released in 2012 (NetCast 3.0) and LG Smart TV models
released in 2013 (NetCast 4.0) are supported.
For pre 2012 LG TV remote commands are supported by the "hdcp" protocol.

The client is inspired by the work of
https://github.com/ubaransel/lgcommander
"""
import logging
import requests
from xml.etree import ElementTree

_LOGGER = logging.getLogger(__name__)

__all__ = ['LgNetCastClient', 'LG_COMMAND', 'LG_QUERY', 'LG_PROTOCOL', 'LgNetCastError',
           'AccessTokenError', 'SessionIdError']


# LG TV handler
LG_HANDLE_KEY_INPUT = 'HandleKeyInput'
LG_HANDLE_MOUSE_MOVE = 'HandleTouchMove'
LG_HANDLE_MOUSE_CLICK = 'HandleTouchClick'
LG_HANDLE_TOUCH_WHEEL = 'HandleTouchWheel'
LG_HANDLE_CHANNEL_CHANGE = 'HandleChannelChange'

DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 3


class LG_COMMAND(object):
    """LG TV remote control commands."""

    APPS = 417
    ASPECT_RATIO = 46
    AUDIO_DESCRIPTION = 407
    AV_MODE = 410
    BACK = 23
    BLUE = 29
    CHANNEL_DOWN = 28
    CHANNEL_UP = 27
    DASH = 402
    DOWN = 13
    ENERGY_SAVING = 409
    EPG = 44
    EXIT = 412
    EXTERNAL_INPUT = 47
    FAST_FORWARD = 36
    FAVORITE_CHANNEL = 404
    GREEN = 30
    HOME_MENU = 21
    LEFT = 14
    LIVE_TV = 43
    LR_3D = 401
    MARK = 52
    MUTE_TOGGLE = 26
    NUMBER_0 = 2
    NUMBER_1 = 3
    NUMBER_2 = 4
    NUMBER_3 = 5
    NUMBER_4 = 6
    NUMBER_5 = 7
    NUMBER_6 = 8
    NUMBER_7 = 9
    NUMBER_8 = 10
    NUMBER_9 = 11
    OK = 20
    PAUSE = 34
    PIP_CHANNEL_DOWN = 415
    PIP_CHANNEL_UP = 414
    PIP_SECONDARY_VIDEO = 48
    PLAY = 33
    POWER = 1
    PREVIOUS_CHANNEL = 403
    PROGRAM_INFORMATION = 45
    PROGRAM_LIST = 50
    QUICK_MENU = 405
    RECORD = 40
    RECORDING_LIST = 41
    RED = 31
    REPEAT = 42
    RESERVATION_PROGRAM_LIST = 413
    REWIND = 37
    RIGHT = 15
    SHOW_SUBTITLE = 49
    SIMPLINK = 411
    SKIP_BACKWARD = 39
    SKIP_FORWARD = 38
    STOP = 35
    SWITCH_VIDEO = 416
    TELE_TEXT = 51
    TEXT_OPTION = 406
    UP = 12
    VIDEO_3D = 400
    VOLUME_DOWN = 25
    VOLUME_UP = 24
    YELLOW = 32


class LG_COMMAND_2011(object):
    """LG TV remote control commands."""

    AUDIO_DESCRIPTION = 145
    AUDIO_LANGUAGE = 10
    AV_MODE = 48
    AV1 = 90
    AV2 = 208
    AV3 = 209
    BACK = 40
    BLUE = 97
    CHANNEL_BACK = 26
    CHANNEL_DOWN = 1
    CHANNEL_LIST = 83
    CHANNEL_UP = 0
    CINEMA_ZOOM = 175
    COMPONENT = 191
    COMPONENT_RGB_HDMI = 152
    DOWN = 65
    ENERGY_SAVING = 149
    EXIT = 91
    FACTORY_ADVANCED_MENU1 = 251
    FACTORY_ADVANCED_MENU2 = 255
    FACTORY_PICTURE_CHECK = 252
    FACTORY_SOUND_CHECK = 253
    FAST_FORWARD = 142
    FAVORITES = 30
    GREEN = 113
    GREYED_OUT_ADD_BUTTON = 85
    GUIDE = 169
    HDMI = 198
    HDMI1 = 206
    HDMI2 = 204
    HDMI3 = 233
    HDMI4 = 218
    HOME_MENU = 67
    INFO = 170
    INPUT = 11
    INSTALLATION_MENU = 207
    LEFT = 7
    LIVE_TV = 158
    MUTE_TOGGLE = 9
    NUMBER_0 = 16
    NUMBER_1 = 17
    NUMBER_2 = 18
    NUMBER_3 = 19
    NUMBER_4 = 20
    NUMBER_5 = 21
    NUMBER_6 = 22
    NUMBER_7 = 23
    NUMBER_8 = 24
    NUMBER_9 = 25
    PAUSE = 186
    PICTURE_MODE = 77
    PLAY = 176
    POWER = 8
    PREMIUM_MENU = 89
    QUICK_MENU = 69
    RATIO = 121
    RATIO_16_9 = 119
    RATIO_4_3 = 118
    RECORD = 189
    RED = 114
    REWIND = 143
    RGB = 213
    RIGHT = 6
    SELECT_CMD = 68
    SIMPLINK = 126
    SLEEP_TIMER = 14
    SLIDESHOW_USB1 = 238
    SLIDESHOW_USB2 = 168
    SOUND_MODE = 82
    STATUS_BAR = 35
    STOP = 177
    SUBTITLE_LANGUAGE = 57
    T_OPT = 33
    TELETEXT = 32
    THREE_D = 220
    TV_RADIO = 15
    UNDERSCORE = 76
    UP = 64
    USB = 124
    VOLUME_DOWN = 3
    VOLUME_UP = 2
    YELLOW = 99


class LG_QUERY(object):
    """LG TV data queries."""

    CUR_CHANNEL = 'cur_channel'
    CHANNEL_LIST = 'channel_list'
    CONTEXT_UI = 'context_ui'
    VOLUME_INFO = 'volume_info'
    SCREEN_IMAGE = 'screen_image'
    IS_3D = 'is_3d'


class LG_PROTOCOL(object):
    """Supported LG TV protcols."""

    HDCP = 'hdcp'
    ROAP = 'roap'


class LgNetCastClient(object):
    """LG NetCast TV client using the ROAP or HDCP protocol."""

    HEADER = {'Content-Type': 'application/atom+xml'}
    XML = '<?xml version=\"1.0\" encoding=\"utf-8\"?>'
    KEY = XML + '<auth><type>AuthKeyReq</type></auth>'
    AUTH = XML + '<auth><type>%s</type><value>%s</value></auth>'
    COMMAND = XML + '<command><session>%s</session><type>%s</type>%s</command>'

    def __init__(self, host, access_token, protocol=LG_PROTOCOL.ROAP):
        """Initialize the LG TV client."""
        self.url = 'http://%s:%s/%s/api/' % (host, DEFAULT_PORT, protocol)
        self.access_token = access_token
        self.protocol = protocol
        self._session = None

    def __enter__(self):
        """Context manager method to support with statement."""
        self._session = self._get_session_id()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager method to support with statement."""
        self._session = None

    def send_command(self, command):
        """Send remote control commands to the TV."""
        message = self.COMMAND % (self._session, LG_HANDLE_KEY_INPUT,
                                  '<value>%s</value>' % command)
        self._send_to_tv('command', message)

    def change_channel(self, channel):
        """Send change channel command to the TV."""
        message = self.COMMAND % (self._session, LG_HANDLE_CHANNEL_CHANGE,
                                  ElementTree.tostring(channel,
                                                       encoding='unicode'))
        self._send_to_tv('command', message)

    def query_data(self, query):
        """Query status information from the TV."""
        response = self._send_to_tv('data', payload={'target': query})
        if response.status_code == requests.codes.ok:
            data = response.text
            tree = ElementTree.XML(data)
            data_list = []
            for data in tree.iter('data'):
                data_list.append(data)
            return data_list

    def _get_session_id(self):
        """Get the session key for the TV connection.

        If a pair key is defined the session id is requested otherwise display
        the pair key on TV.
        """
        if not self.access_token:
            self._display_pair_key()
            raise AccessTokenError(
                'No access token specified to create session.')
        message = self.AUTH % ('AuthReq', self.access_token)
        response = self._send_to_tv('auth', message)
        if response.status_code != requests.codes.ok:
            raise SessionIdError('Can not get session id from TV.')
        data = response.text
        tree = ElementTree.XML(data)
        session = tree.find('session').text
        return session

    def _display_pair_key(self):
        """Send message to display the pair key on TV screen."""
        self._send_to_tv('auth', self.KEY)

    def _send_to_tv(self, message_type, message=None, payload=None):
        """Send message of given type to the tv."""
        if self.protocol == LG_PROTOCOL.HDCP:
            if message_type == 'auth':
                message_type = 'auth'
            else:
                message_type = 'dtv_wifirc'
        if message:
            url = '%s%s' % (self.url, message_type)
            print("POST %s to %s" % (message, url))
            response = requests.post(url, data=message, headers=self.HEADER,
                                     timeout=DEFAULT_TIMEOUT)
        else:
            url = '%sdata?target=%s&session=%s' % (self.url, payload["target"], self._session)
            print("GET %s from %s" % (payload["target"], url))
            response = requests.get(url, params=payload, headers=self.HEADER,
                                    timeout=DEFAULT_TIMEOUT)
        print("Received: %s" % response.text)
        return response


class LgNetCastError(Exception):
    """Base class for all exceptions in this module."""


class AccessTokenError(LgNetCastError):
    """No access token specified to create session."""


class SessionIdError(LgNetCastError):
    """No session id could be retrieved from TV."""
