#!/usr/bin/env python
__author__ = "Arana Fireheart"

from machine import Pin
import time
from sys import exit
import urequests
from plantUtilities import uUrlEncode, AnalogInWithHysteresis, levels, levelValues
import network
import gc
versionNumber = "0.x.1"

# Each level has a value for [redLightOn, fastBlink]
ledStates = {"Wet": [False, False], "Damp": [False, False], "Moist": [True, True], "Dry": [True, True]}
hysteresisValue = 10

messages = ["is wet", "is damp", "is moist!", "is bone dry!"]
webhookURL = "https://maker.ifttt.com/trigger/PlantMail/with/key/oKQM5KSDAg9lAxclodsMonxnGBehfLm3dEmGe2aUMDB"


class PlantTalker(object):
    def __init__(self, waterLevelsList, hysteresisValue):
        self.slowBlinkTime = 5000
        self.fastBlinkTime = 100
        self.triggerInterval = 100      # Basic time unit for the TimeWarden
        self.lightOn = True
        self.redLightOn = True
        self.fastBlink = True
        self.stopButton = Pin(16, Pin.IN)

        self.redLED = Pin(5, Pin.OUT, Pin.PULL_UP, value=0)
        self.greenLED = Pin(0, Pin.OUT, Pin.PULL_UP, value=0)
        self.address1 = Pin(12, Pin.IN)
        self.address2 = Pin(14, Pin.IN)
        self.address4 = Pin(4, Pin.IN)
        self.address8 = Pin(13, Pin.IN)

        inputPin = 0
        self.waterSensor = AnalogInWithHysteresis(inputPin, waterLevelsList, hysteresisValue)
        self.currentCondition = self.waterSensor.updateCurrentSensorValue()
        print("Level: {0}".format(self.waterSensor.previousSensorValue))
        print("Initial values: Condition: {3}; LightOn: {0}; RedLightOn {1}; FastBlink: {2}".format(self.lightOn, self.redLightOn, self.fastBlink, self.currentCondition))
        self.updateLights()

    def getTriggerInterval(self):
        return self.triggerInterval

    def isTimeToStop(self):
        return self.stopButton.value() == 0

    def showActivity(self):
        print(".", end='')
        # print("Current time: {0}".format(time.ticks_ms()))

    def smellTheRoses(self):
        newCondition = self.waterSensor.updateCurrentSensorValue()
        print("New Condition: {0}".format(newCondition))
        stateChanged = self.currentCondition != newCondition
        print("Checking the roses... {0}".format(self.currentCondition))
        if stateChanged:
            self.currentCondition = newCondition
            print("Moisture state changed to: {0}".format(self.currentCondition))
            oldFastBlink = self.fastBlink
            import gc
            gc.collect()
            print("Free RAM: {0}".format(gc.mem_free()))
            sendNotification(11, messages[levels[self.currentCondition]])
            print("Currently red is {0} and blink is {1}".format(self.redLightOn, self.triggerInterval))

    def setLightStates(self):
        self.redLightOn, self.fastBlink = ledStates[self.waterSensor.getCurrentInputState()]
        return None

    def updateLights(self):
        if self.lightOn:
            self.lightOn = False
            self.redLED.off()
            self.greenLED.off()
        else:
            self.lightOn = True
            if self.redLightOn:
                self.redLED.on()
                self.greenLED.off()
            else:
                self.redLED.off()
                self.greenLED.on()


def sendNotification(stationAddress, message):
    print("Current time: {0}".format(time.ticks_ms()))
    plantHeader = {"Content-Type": "application/x-www-form-urlencoded"}
    plantData = {"value1": "{0}".format(stationAddress), "value2": "{0}".format(message)}
    plantDataEncoded = uUrlEncode(plantData)
    print("Current time: {0}".format(time.ticks_ms()))
    webResponse = urequests.post(webhookURL, data=plantDataEncoded, headers=plantHeader)
    print("Current time: {0}".format(time.ticks_ms()))
    print("Response: {0} to message: {1}".format(webResponse.text, plantData))
    print(webResponse.content)
    print(webResponse.encoding)
    webResponse.close()


if __name__ == "__main__":
    print("Welcome to Plant Monitor version: {0}".format(versionNumber))
    gc.collect()
    nic = network.WLAN(network.STA_IF)
    while not nic.isconnected():
        pass
        # print('+', end='')
    print("Location: {0}".format(nic.ifconfig()[0]))

    thisPlant = PlantTalker(levelValues, hysteresisValue)
    # print(thisPlant)
    stopTime = thisPlant.isTimeToStop()

    while not stopTime:
        stopTime = thisPlant.isTimeToStop()
        thisPlant.smellTheRoses()
        for count in range(0, 5):
            print(".", end='')
            time.sleep(2)
    thisPlant.shutdown()
    exit()

