"""Config flow to configure aqara gateway component."""
from collections import OrderedDict
from typing import Optional

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_PUSH,
    ConfigFlow,
    OptionsFlow,
    ConfigEntry
    )
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util.network import is_ip_address

from .core import gateway
from .core.const import (
    DOMAIN, DATA_KEY, OPT_DEVICE_NAME, CONF_MODEL, OPT_DEBUG, CONF_DEBUG, CONF_STATS
)
from .core.entry_data import RuntimeEntryData
from .core.utils import Utils



class AqaraGatewayFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Aqara Gateway config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize flow."""
        self._host: Optional[str] = None
        self._password: Optional[str] = None
        self._model: Optional[str] = None
        self._device_info: Optional[str] = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """ get option flow """
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: Optional[ConfigType] = None,
        error: Optional[str] = None
    ):  # pylint: disable=arguments-differ
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self._set_user_input(user_input)
            if not is_ip_address(self._host):
                return self.async_abort(reason="connection_error")
            ret = gateway.is_aqaragateway(self._host,
                                          self._password,
                                          self._model)
            if "error" in ret['status']:
                return self.async_abort(reason="connection_error")
            self._name = ret.get('name', '')
            self._model = ret.get('model', '')
            return self._async_get_entry()

        for name, _ in OPT_DEVICE_NAME.items():
            if self._name and name in self._name.lower():
                self._model = name
                break

        fields = OrderedDict()
        fields[vol.Required(CONF_HOST,
                            default=self._host or vol.UNDEFINED)] = str
        fields[vol.Optional(CONF_PASSWORD,
                            default=self._password or vol.UNDEFINED)] = str
        fields[vol.Optional(CONF_MODEL,
                            default=self._model or 'm1s')] = vol.In(
                                OPT_DEVICE_NAME)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(fields),
            errors={'base': error} if error else None
        )

    @property
    def _name(self):
        # pylint: disable=no-member
        # https://github.com/PyCQA/pylint/issues/3167
        return self.context.get(CONF_NAME)

    @_name.setter
    def _name(self, value):
        # pylint: disable=no-member
        # https://github.com/PyCQA/pylint/issues/3167
        self.context[CONF_NAME] = value
        self.context["title_placeholders"] = {"name": self._name}

    def _set_user_input(self, user_input):
        if user_input is None:
            return
        self._host = user_input.get(CONF_HOST, "")
        self._password = user_input.get(CONF_PASSWORD, "")
        self._model = user_input.get(CONF_MODEL, "")

    async def _async_add(self, user_input):
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_HOST: self._host,
                CONF_PASSWORD: self._password,
                CONF_MODEL: self._model
            },
        )

    async def async_step_discovery_confirm(self, user_input=None):
        """Handle user-confirmation of discovered node."""

        if user_input is not None:
            return await self._async_add(user_input)

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._name,
                                      "device_info": self._device_info}
        )

    async def async_step_zeroconf(self, discovery_info: DiscoveryInfoType):
        """Handle zeroconf discovery."""
        # Hostname is format: _aqara._tcp.local., _aqara-setup._tcp.local.
        local_name = discovery_info["hostname"][:-1]
        node_name = local_name[: -len(".local")]
        address = discovery_info["properties"].get(
            "address", discovery_info["host"])
        model = discovery_info["properties"].get("md", "unknow")
        fwversion = discovery_info["properties"].get("fw", "unknow")
        fwcloud = discovery_info["properties"].get("cl", "unknow")
        self._device_info = (
                f"Name: {node_name}\n"
                f"Model: {model}\n"
                f"Hostname: {local_name}\n"
                f"IP: {address}\n"
                f"Version: {fwversion}\n"
                f"Cloud: {fwcloud}"
            )

        self._host = discovery_info[CONF_HOST]
        self._name = node_name
        self._password = ''
        self._model = Utils.get_device_name(model).split(" ")[-1]

        for entry in self._async_current_entries():
            already_configured = False
            if CONF_HOST in entry.data and entry.data[CONF_HOST] in [
                address,
                discovery_info[CONF_HOST],
            ]:
                # Is this address or IP address already configured?
                already_configured = True
            elif CONF_HOST in entry.options and entry.options[CONF_HOST] in [
                address,
                discovery_info[CONF_HOST],
            ]:
                # Is this address or IP address already configured?
                already_configured = True
            if already_configured:
                # Backwards compat, we update old entries

                return self.async_abort(reason="already_configured")

        if discovery_info.get('type') == '_aqara-setup._tcp.local.':
            return await self.async_step_user()
        else:
            return await self.async_step_discovery_confirm()

    @callback
    def _async_get_entry(self):
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_HOST: self._host,
                CONF_PASSWORD: self._password,
                CONF_MODEL: self._model
            },
        )


class OptionsFlowHandler(OptionsFlow):
    _host = None
    _password = None
    _model = None
    # pylint: disable=too-few-public-methods
    """Handle options flow changes."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""
        if user_input is not None:
            if not is_ip_address(user_input.get(CONF_HOST)):
                return self.async_abort(reason="connection_error")
            self._host = user_input.get(CONF_HOST)
            if len(user_input.get(CONF_PASSWORD, "")) >= 1:
                self._password = user_input.get(CONF_PASSWORD)
            return self.async_create_entry(
                title='',
                data={
                    CONF_HOST: self._host,
                    CONF_PASSWORD: self._password,
                    CONF_MODEL: self._model,
#                    CONF_STATS: user_input.get(CONF_STATS, False),
                    CONF_DEBUG: user_input.get(CONF_DEBUG, []),
                },
            )
        self._host = self.config_entry.options[CONF_HOST]
        self._password = self.config_entry.options.get(CONF_PASSWORD, '')
        self._model = self.config_entry.options.get(CONF_MODEL, '')
#        stats = self.config_entry.options.get(CONF_STATS, False)
        debug = self.config_entry.options.get(CONF_DEBUG, [])

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._host): str,
                    vol.Optional(CONF_PASSWORD, default=self._password): str,
#                    vol.Required(CONF_STATS, default=stats): bool,
                    vol.Optional(CONF_DEBUG, default=debug): cv.multi_select(
                        OPT_DEBUG
                    ),
                }
            ),
        )
