import json
import logging
import requests
import voluptuous as vol

from datetime import timedelta
from re import search
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    ATTR_ATTRIBUTION, CONF_NAME, CONF_USERNAME, CONF_PASSWORD,
    EVENT_HOMEASSISTANT_START)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity


_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Powered by Xfinity"

ATTR_TOTAL_USAGE = 'total_usage'
ATTR_ALLOWED_USAGE = 'allowed_usage'
ATTR_REMAINING_USAGE = 'remaining_usage'

DEFAULT_NAME = "Xfinity Usage"

SCAN_INTERVAL = timedelta(hours=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the sensor platform."""
    name = config.get(CONF_NAME)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    xfinity_data = XfinityUsageData(username, password)
    sensor = XfinityUsageSensor(name, xfinity_data)

    def _first_run():
        sensor.update()
        add_entities([sensor])

    # Wait until start event is sent to load this component.
    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, lambda _: _first_run())


class XfinityUsageSensor(Entity):
    """Representation of the Xfinity Usage sensor."""

    def __init__(self, name, xfinity_data):
        """Initialize the sensor."""
        self._name = name
        self._xfinity_data = xfinity_data
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._xfinity_data.total_usage is not None:
            return self._xfinity_data.total_usage

    @property
    def device_state_attributes(self):
        """Return the state attributes of the last update."""
        if self._xfinity_data.total_usage is None:
            return None

        res = {ATTR_ATTRIBUTION: ATTRIBUTION}
        res[ATTR_TOTAL_USAGE] = self._xfinity_data.total_usage
        res[ATTR_ALLOWED_USAGE] = self._xfinity_data.allowed_usage
        res[ATTR_REMAINING_USAGE] = self._xfinity_data.remaining_usage
        return res

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self._xfinity_data.unit is not None:
            return self._xfinity_data.unit

    def update(self):
        """Fetch new state data for the sensor."""
        self._xfinity_data.update()


class XfinityUsageData:
    """Xfinity Usage data object"""

    def __init__(self, username, password):
        """Setup usage data object"""
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.data = None
        self.unit = None
        self.total_usage = None
        self.allowed_usage = None
        self.remaining_usage = None

    def update(self):
        """Update usage values"""
        _LOGGER.debug("Finding reqId for login...")
        res = self.session.get('https://customer.xfinity.com/oauth/force_connect/?continue=%23%2Fdevices')
        if res.status_code != 200:
            _LOGGER.error("Failed to find reqId, status_code:{}".format(res.status_code))
            return

        m = search(r'<input type="hidden" name="reqId" value="(.*?)">', res.text)
        req_id = m.group(1)
        _LOGGER.debug("Found reqId = %r", req_id)

        data = {
          'user': self.username,
          'passwd': self.password,
          'reqId': req_id,
          'deviceAuthn': 'false',
          's': 'oauth',
          'forceAuthn': '1',
          'r': 'comcast.net',
          'ipAddrAuthn': 'false',
          'continue': 'https://oauth.xfinity.com/oauth/authorize?client_id=my-account-web&prompt=login&redirect_uri=https%3A%2F%2Fcustomer.xfinity.com%2Foauth%2Fcallback&response_type=code&state=%23%2Fdevices&response=1',
          'passive': 'false',
          'client_id': 'my-account-web',
          'lang': 'en',
        }

        _LOGGER.debug("Posting to login...")
        res = self.session.post('https://login.xfinity.com/login', data=data)
        if res.status_code != 200:
            _LOGGER.error("Failed to login, status_code:{}".format(res.status_code))
            return

        _LOGGER.debug("Fetching internet usage AJAX...")
        res = self.session.get('https://customer.xfinity.com/apis/services/internet/usage')
        _LOGGER.debug("Resp: %r", res.text)
        if res.status_code != 200:
            _LOGGER.error("Failed to fetch data, status_code:{}".format(res.status_code))
            return

        self.data = json.loads(res.text)
        _LOGGER.debug("Received Xfinity Usage data: {}".format(self.data))

        self.unit = self.data['usageMonths'][-1]['unitOfMeasure']
        self.total_usage = self.data['usageMonths'][-1]['homeUsage']
        self.allowed_usage = self.data['usageMonths'][-1]['allowableUsage']
        self.remaining_usage = self.allowed_usage - self.total_usage
        return
