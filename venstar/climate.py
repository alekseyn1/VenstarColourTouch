"""Support for Venstar WiFi Thermostats.  https://community.home-assistant.io/t/editing-component-files-in-hassio/24273  """
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    #PRESET_AWAY,
    PRESET_NONE,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    HVAC_MODE_OFF,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_TIMEOUT,
    CONF_USERNAME,
    PRECISION_WHOLE,
    STATE_ON,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_FAN_STATE = "fan_state"
ATTR_HVAC_STATE = "hvac_mode"

CONF_HUMIDIFIER = "humidifier"

DEFAULT_SSL = False

VALID_FAN_STATES = [STATE_ON, HVAC_MODE_AUTO]
VALID_THERMOSTAT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_COOL, HVAC_MODE_OFF, HVAC_MODE_AUTO]

HOLD_MODE_OFF = "off"
HOLD_MODE_TEMPERATURE = "temperature"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_HUMIDIFIER, default=True): cv.boolean,
        vol.Optional(CONF_SSL, default=DEFAULT_SSL): cv.boolean,
        vol.Optional(CONF_TIMEOUT, default=5): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
        vol.Optional(CONF_USERNAME): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Venstar thermostat."""
    #import venstarcolortouch

    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    host = config.get(CONF_HOST)
    timeout = config.get(CONF_TIMEOUT)
    humidifier = config.get(CONF_HUMIDIFIER)

    if config.get(CONF_SSL):
        proto = "https"
    else:
        proto = "http"

    client = VenstarColorTouch(
        addr=host, timeout=timeout, user=username, password=password, proto=proto
    )

    add_entities([VenstarThermostat(client, humidifier)], True)


class VenstarThermostat(ClimateDevice):
    """Representation of a Venstar thermostat."""

    def __init__(self, client, humidifier):
        """Initialize the thermostat."""
        self._client = client
        self._humidifier = humidifier

    def update(self):
        """Update the data from the thermostat."""
        info_success = self._client.update_info()
        sensor_success = self._client.update_sensors()
        if not info_success or not sensor_success:
            _LOGGER.error("Failed to update data")

    @property
    def supported_features(self):
        """Return the list of supported features."""
        features = SUPPORT_TARGET_TEMPERATURE | SUPPORT_FAN_MODE | SUPPORT_PRESET_MODE

        if self._client.mode == self._client.MODE_AUTO:
            features |= SUPPORT_TARGET_TEMPERATURE_RANGE

        if self._humidifier and hasattr(self._client, "hum_active"):
            features |= SUPPORT_TARGET_HUMIDITY

        return features

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._client.name

    @property
    def precision(self):
        """Return the precision of the system.

        Venstar temperature values are passed back and forth in the
        API as whole degrees C or F.
        """
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        """Return the unit of measurement, as defined by the API."""
        if self._client.tempunits == self._client.TEMPUNITS_F:
            return TEMP_FAHRENHEIT
        return TEMP_CELSIUS

    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return VALID_FAN_STATES

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return VALID_THERMOSTAT_MODES

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._client.get_indoor_temp()

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._client.get_indoor_humidity()

    @property
    def hvac_mode(self):
        """Return current operation ie. heat, cool, idle."""
        if self._client.mode == self._client.MODE_HEAT:
            return HVAC_MODE_HEAT
        if self._client.mode == self._client.MODE_COOL:
            return HVAC_MODE_COOL
        if self._client.mode == self._client.MODE_AUTO:
            return HVAC_MODE_AUTO
        return HVAC_MODE_OFF

    @property
    def fan_mode(self):
        """Return the fan setting."""
        if self._client.fan == self._client.FAN_AUTO:
            return HVAC_MODE_AUTO
        return STATE_ON

    @property
    def device_state_attributes(self):
        """Return the optional state attributes."""
        return {
            ATTR_FAN_STATE: self._client.fanstate,
            ATTR_HVAC_STATE: self._client.state,
        }

    @property
    def target_temperature(self):
        """Return the target temperature we try to reach."""
        if self._client.mode == self._client.MODE_HEAT:
            return self._client.heattemp
        if self._client.mode == self._client.MODE_COOL:
            return self._client.cooltemp
        return None

    @property
    def target_temperature_low(self):
        """Return the lower bound temp if auto mode is on."""
        if self._client.mode == self._client.MODE_AUTO:
            return self._client.heattemp
        return None

    @property
    def target_temperature_high(self):
        """Return the upper bound temp if auto mode is on."""
        if self._client.mode == self._client.MODE_AUTO:
            return self._client.cooltemp
        return None

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return self._client.hum_setpoint

    @property
    def min_humidity(self):
        """Return the minimum humidity. Hardcoded to 0 in API."""
        return 0

    @property
    def max_humidity(self):
        """Return the maximum humidity. Hardcoded to 60 in API."""
        return 60

    @property
    def preset_mode(self):
        """Return current preset."""
        #if self._client.away:
        #    return PRESET_AWAY
        if self._client.schedule == 0:
            return HOLD_MODE_TEMPERATURE

    @property
    def preset_modes(self):
        """Return valid preset modes."""
        return [PRESET_NONE, HOLD_MODE_TEMPERATURE]

    def _set_operation_mode(self, operation_mode):
        """Change the operation mode (internal)."""
        if operation_mode == HVAC_MODE_HEAT:
            success = self._client.set_mode(self._client.MODE_HEAT)
        elif operation_mode == HVAC_MODE_COOL:
            success = self._client.set_mode(self._client.MODE_COOL)
        elif operation_mode == HVAC_MODE_AUTO:
            success = self._client.set_mode(self._client.MODE_AUTO)
        else:
            success = self._client.set_mode(self._client.MODE_OFF)

        if not success:
            _LOGGER.error("Failed to change the operation mode")
        return success

    def set_temperature(self, **kwargs):
        """Set a new target temperature."""
        set_temp = True
        operation_mode = kwargs.get(ATTR_HVAC_MODE, self._client.mode)
        temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        temperature = kwargs.get(ATTR_TEMPERATURE)

        if operation_mode != self._client.mode:
            set_temp = self._set_operation_mode(operation_mode)

        if set_temp:
            if operation_mode == self._client.MODE_HEAT:
                success = self._client.set_setpoints(temperature, self._client.cooltemp)
            elif operation_mode == self._client.MODE_COOL:
                success = self._client.set_setpoints(self._client.heattemp, temperature)
            elif operation_mode == self._client.MODE_AUTO:
                success = self._client.set_setpoints(temp_low, temp_high)
            else:
                success = False
                _LOGGER.error(
                    "The thermostat is currently not in a mode "
                    "that supports target temperature: %s",
                    operation_mode,
                )

            if not success:
                _LOGGER.error("Failed to change the temperature")

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if fan_mode == STATE_ON:
            success = self._client.set_fan(self._client.FAN_ON)
        else:
            success = self._client.set_fan(self._client.FAN_AUTO)

        if not success:
            _LOGGER.error("Failed to change the fan mode")

    def set_hvac_mode(self, hvac_mode):
        """Set new target operation mode."""
        self._set_operation_mode(hvac_mode)

    def set_humidity(self, humidity):
        """Set new target humidity."""
        success = self._client.set_hum_setpoint(humidity)

        if not success:
            _LOGGER.error("Failed to change the target humidity level")

    def set_preset_mode(self, preset_mode):
        """Set the hold mode."""
        if preset_mode == HOLD_MODE_TEMPERATURE:
            success = self._client.set_schedule(0)
        elif preset_mode == PRESET_NONE:
            success = False
            if self._client.schedule == 0:
                success = success and self._client.set_schedule(1)
        else:
            _LOGGER.error("Unknown hold mode: %s", preset_mode)
            success = False

        if not success:
            _LOGGER.error("Failed to change the schedule/hold state")
			
import json
import requests
import urllib3
import urllib
import logging
from requests.auth import HTTPDigestAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MIN_API_VER=3

class VenstarColorTouch:
    def __init__(self, addr, timeout, user=None, password=None, proto='http', SSLCert=False):
        #API Constants
        self.MODE_OFF = 0
        self.MODE_HEAT = 1
        self.MODE_COOL = 2
        self.MODE_AUTO = 3
        self.STATE_IDLE = 0
        self.STATE_HEATING = 1
        self.STATE_COOLING = 2
        self.STATE_LOCKOUT = 3
        self.STATE_ERROR = 4
        self.FAN_AUTO = 0
        self.FAN_ON = 1
        self.FANSTATE_OFF = 0
        self.FANSTATE_ON = 1
        self.TEMPUNITS_F = 0
        self.TEMPUNITS_C = 1
        self.SCHED_F = 0
        self.SCHED_C = 1
        self.SCHEDPART_MORNING = 0
        self.SCHEDPART_DAY = 1
        self.SCHEDPART_EVENING = 2
        self.SCHEDPART_NIGHT = 3
        self.SCHEDPART_INACTIVE = 255
        #self.AWAY_HOME = 0
        #self.AWAY_AWAY = 1

        #Input parameters
        self.addr = addr
        self.timeout = timeout

        if user != None and password != None:
            self.auth = HTTPDigestAuth(user, password)
        else:
            self.auth = None

        self.proto = proto 
        self.SSLCert = SSLCert

        #Initialize State
        self.status = {}
        self._api_ver = None
        self._type = None
        self._info = None
        self._sensors = None
        #
        # /control
        #
        self.setpointdelta = None
        self.heattemp = None
        self.cooltemp = None
        self.fan = None
        self.mode = None
        self.fanstate = None
        self.state = None
        #
        # /settings
        #
        self.name = None
        self.tempunits = None
        #self.away = None
        self.schedule = None
        self.hum_setpoint = None
        self.dehum_setpoint = None
        self.hum_active = None

    def login(self):
        r = self._request("/")
        if r is False:
            return r
        j = r.json()
        if j["api_ver"] >= MIN_API_VER:
            self._api_ver = j["api_ver"]
            self._type = j["type"]
            return True
        else:
            return False

    def _request(self, path, data=None):
        uri = "{proto}://{addr}/{path}".format(proto=self.proto, addr=self.addr, path=path)
        try:
            if data is not None:
                req = requests.post(uri, 
                                    verify=self.SSLCert,
                                    timeout=self.timeout,
                                    data=data,
                                    auth=self.auth)
            else:
                req = requests.get(uri,
                                   verify=self.SSLCert,
                                   timeout=self.timeout,
                                   auth=self.auth)
        except Exception as ex:
            print("Error requesting {uri} from Venstar ColorTouch.".format(uri=uri))
            print(ex)
            return False

        if not req.ok:
            print("Connection error logging into Venstar ColorTouch. Status Code: {status}".format(status=req.status_code))
            return False
       
        return req

    def update_info(self):
        r = self._request("query/info")

        if r is False:
            return r

        self._info=r.json()

        #
        # Populate /control stuff
        #
        self.setpointdelta=self.get_info("setpointdelta")
        self.heattemp=self.get_info("heattemp")
        self.cooltemp=self.get_info("cooltemp")
        self.fan=self.get_info("fan")
        self.fanstate=self.get_info("fanstate")
        self.mode=self.get_info("mode")
        self.state=self.get_info("state")

        #
        # Populate /settings stuff
        #
        self.name = self.get_info("name")
        self.tempunits = self.get_info("tempunits")
        #self.away = None #self.get_info("away")
        self.schedule = self.get_info("schedule")
        # T5800 thermostat will not have hum_setpoint/dehum_setpoint in the JSON, so make
        # it optional
        if 'hum_setpoint' in self._info:
          self.hum_setpoint = self.get_info("hum_setpoint")
        else:
          self.hum_setpoint = None
        if 'dehum_setpoint' in self._info:
          self.dehum_setpoint = self.get_info("dehum_setpoint")
        else:
          self.dehum_setpoint = None
        #
        if 'hum_active' in self._info:
            self.hum_active = self.get_info("hum_active")
        else:
            self.hum_active = 0

        return True

    def update_sensors(self):
        r = self._request("query/sensors")

        if r is False:
            return r
        self._sensors = r.json()
        return True

    # returns a list of all runtime records. get_runtimes()[-1] should be the last one.
    # runtimes are updated every day (86400 seconds).
    def get_runtimes(self):
        r = self._request("query/runtimes")
        if r is False:
            return r
        else:
            runtimes=r.json()
            return runtimes["runtimes"]

    def get_info(self, attr):
        return self._info[attr]

    def get_thermostat_sensor(self, attr):
        if self._sensors != None and self._sensors["sensors"] != None and len(self._sensors["sensors"]) > 0:
            # 'hum' (humidity) sensor is not present on T5800 series
            if attr in self._sensors["sensors"][0]:
              return self._sensors["sensors"][0][attr]
            else:
              return None
        else:
            return None

    def get_outdoor_sensor(self, attr):
        if self._sensors != None and self._sensors["sensors"] != None and len(self._sensors["sensors"]) > 0:
            return self._sensors["sensors"][1][attr]
        else:
            return None

    def get_indoor_temp(self):
        return self.get_thermostat_sensor('temp')

    def get_outdoor_temp(self):
        return self.get_outdoor_sensor('temp')

    def get_indoor_humidity(self):
        return self.get_thermostat_sensor('hum')

    def get_alerts(self):
        r = self._request("query/alerts")
        if r is False:
            return r
        else:
            alerts=r.json()
            return alerts["alerts"][0]

    # The /control endpoint requires heattemp/cooltemp in each message, even if you're just turning
    # the fan on/off or setting the mode. So we retrieve everything from self and use accessors
    # to set them.
    def set_control(self):
        if self.mode is None:
            return False
        path="/control"
        data = urllib.parse.urlencode({'mode':self.mode, 'fan':self.fan, 'heattemp':self.heattemp, 'cooltemp':self.cooltemp})
        print("Path is: {0}".format(path))
        r = self._request(path, data)
        if r is False:
            return r
        else:
            if r is not None:
                if "success" in r.json():
                    print("set_control Success!")
                    return True
                else:
                    print("set_control Fail {0}.".format(r.json()))
                    return False

    def set_setpoints(self, heattemp, cooltemp):
        # Must not violate setpointdelta if we're in auto mode.
        if self.mode == self.MODE_AUTO and heattemp + self.setpointdelta > cooltemp:
            print("In auto mode, the cool temp must be {0} " 
                  "degrees warmer than the heat temp.".format(self.setpointdelta))
            return False
        self.heattemp = heattemp
        self.cooltemp = cooltemp
        return self.set_control()

    def set_mode(self, mode):
        self.mode = mode
        return self.set_control()

    def set_fan(self, fan):
        self.fan = fan
        return self.set_control()

    #
    # set_settings can't change the schedule or away while schedule is on, so no point in trying.
    #
    def set_settings(self):
        if self.tempunits is None:
            return False
        path="/settings"
        data = urllib.parse.urlencode({'tempunits':self.tempunits, 'hum_setpoint':self.hum_setpoint, 'dehum_setpoint':self.dehum_setpoint})
        r = self._request(path, data)
        print("url is: {0} json is: {1}".format(data, r.text))
        if r is False:
            return r
        else:
            if r is not None:
                if "success" in r.json():
                    print("set_settings Success!")
                    return True
                else:
                    print("set_settings Fail {0}.".format(r.text))
                    return False

    def set_tempunits(self, tempunits):
        self.tempunits = tempunits
        return self.set_settings()

    #
    # We can't change any settings while the schedule is active so we can't use set_settings()
    #
    def set_schedule(self, schedule):
        if (self.schedule == schedule):
            return True
        #
        # If thermostat is in away mode, then can't enable schedule.
        #
        #if (self.away == 1):
        #    return False
        self.schedule = schedule
        path="/settings"
        data = urllib.parse.urlencode({'schedule':self.schedule})
        r = self._request(path, data)
        if r is False:
            ret = False
        else:
            if r is not None:
                if "success" in r.json():
                    print("set_schedule Success!")
                    self.update_info()
                    ret = True
                else:
                    print("set_schedule Fail {0}.".format(r.json()))
                    ret = False
        return ret

    def set_hum_setpoint(self, hum_setpoint):
        self.hum_setpoint = hum_setpoint
        return self.set_settings()

    def set_dehum_setpoint(self, dehum_setpoint):
        self.dehum_setpoint = dehum_setpoint
        return self.set_settings()