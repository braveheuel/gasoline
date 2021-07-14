#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 ch <ch@silversurfer.deepspace.local>
#
# Distributed under terms of the MIT license.
"""
Show gasoline price of selected stations in the frontend
"""
import asyncio
import logging
from datetime import timedelta

import async_timeout
import aiohttp
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_NAME, CONF_ID, STATE_UNAVAILABLE)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import (async_track_time_interval)
from lxml import etree

_LOGGER = logging.getLogger(__name__)

CONF_STATIONS = 'stations'
CONF_INTERVAL = 'interval'

DEFAULT_NAME = 'Tankstelle'
DEFAULT_INTERVAL = 60
ICON = 'mdi:gas-station'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_INTERVAL): cv.positive_int,
    vol.Required(CONF_STATIONS): [{
        vol.Required(CONF_ID): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string
    }]
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the gasoline sensor."""

    sensors = []
    for station in config.get(CONF_STATIONS):
        sensors.append(Gasoline(
            station.get(CONF_ID),
            station.get(CONF_NAME, DEFAULT_NAME)
        ))

    if not sensors:
        _LOGGER.warning("No Stations Defined!")
        return
    async_add_devices(sensors)

    station_data = GasolineData(hass, sensors)

    # Update Gasoline Data
    async_track_time_interval(hass, station_data.async_update,
                              timedelta(minutes=10))

    yield from station_data.async_update()

class Gasoline(Entity):
    """Representation of a min/max sensor."""

    def __init__(self, id, name):
        """Initialize the min/max sensor."""
        self._id = id
        self._name = name
        self._last_run = STATE_UNAVAILABLE
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the Currency"""
        return "€"

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    @property
    def last_run(self):
        """Return the last run of the update algorithm"""
        return self._last_run

class GasolineData(object):
    """Data Object for Gasoline Stations"""

    def __init__(self, hass, stations):
        self._hass = hass
        self._stations = stations
        self._url = "http://www.clever-tanken.de/tankstelle_details/"

    @asyncio.coroutine
    def get_gasoline_price(self, station_id):
        station_url = "{}{}".format(self._url, station_id)
        resp = None
        try:
            websession = async_get_clientsession(self._hass)
            with async_timeout.timeout(10, loop=self._hass.loop):
                resp = yield from websession.get(station_url)
            if resp.status != 200:
                _LOGGER.warning("Error fetching {} with error {}!".format(station_url, resp.status))
                return
            text = yield from resp.text()

        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.warning("Error fetching {} with error {}".format(station_url, err))
            return
        tree = etree.HTML(text)
        #//*[@id="current-price-1"]
        r = tree.xpath('//*[@id="current-price-1"]')
        # r = tree.xpath('//*[@id="main-content-fuel-price-list"]/div[1]/div[2]/div/span[2]/span')
        #suffix = tree.xpath('//*[@id="main-content-fuel-price-list"]/div[1]/div[2]/div/span[2]/sup')
        suffix = tree.xpath('//*[@id="suffix-price-1"]')
        if r and suffix:
            text_price = "{}{}".format(r[0].text.strip(" "), suffix[0].text.strip(" "))
            return float(text_price)
        else:
            _LOGGER.warning("Error Parsing Price for Station {}".format(station_id))
            return "n/a"

    @asyncio.coroutine
    def async_update(self, *_):
        """Update the stations"""
        _LOGGER.info("Updating Gasoline Stations...")

        tasks = []
        for station in self._stations:
            new_price = yield from self.get_gasoline_price(station._id)
            if new_price != station._state:
                station._state = new_price
                tasks.append(station.async_update_ha_state())

        if tasks:
            yield from asyncio.wait(tasks, loop=self._hass.loop)
