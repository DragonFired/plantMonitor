#!/usr/bin/env python
__author__ = "Arana Fireheart"

from machine import Pin
import time
from sys import exit
import urequests
from pmHardware import *
from plantUtilities import uUrlEncode, AnalogInWithHysteresis, levels, levelValues
from timeWarden import *
import network
import gc
versionNumber = "0.3.17"

# Each level has a value for [redLightOn, fastBlink]
ledStates = {"Wet": [False, False], "Damp": [False, False], "Moist": [True, True], "Dry": [True, True]}
hysteresisValue = 10

messages = ["is wet", "is damp", "is moist!", "is bone dry!"]
webhookURL = "https://maker.ifttt.com/trigger/PlantMail/with/key/oKQM5KSDAg9lAxclodsMonxnGBehfLm3dEmGe2aUMDB"


# dictionaryElement = {"Value1": "{0}".format(5), "Value2": "{0}".format("Very wet!")}

class PlantTalker(object):
    def __init__(self, waterLevelsList, hysteresisValue):
        self.slowBlinkTime = 5000
        self.fastBlinkTime = 100
        self.triggerInterval = 100      # Basic time unit for the TimeWarden
        self.lightOn = True
        self.redLightOn = True
        self.fastBlink = True
        self.stopButton = Pin(stopButtonPin, Pin.IN)

        self.redLED = Pin(redLEDPin, Pin.OUT, Pin.PULL_UP, value=0)
        self.greenLED = Pin(greenLEDPin, Pin.OUT, Pin.PULL_UP, value=0)
        self.address1 = Pin(address1Pin, Pin.IN)
        self.address2 = Pin(address2Pin, Pin.IN)
        self.address4 = Pin(address4Pin, Pin.IN)
        self.address8 = Pin(address8Pin, Pin.IN)
        self.stationAddress = self.getStationAddress()

        self.waterSensor = AnalogInWithHysteresis(inputPin, waterLevelsList, hysteresisValue)
        self.currentCondition = self.waterSensor.updateCurrentSensorValue()
        self.setLightStates()
        print("Level: {0}".format(self.waterSensor.previousSensorValue))
        print("Initial values: Condition: {3}; LightOn: {0}; RedLightOn {1}; FastBlink: {2}".format(self.lightOn, self.redLightOn, self.fastBlink, self.currentCondition))
        self.updateLights("Dummy")
        self.ticker = TimeWarden(self.triggerInterval)
        print("Timer code version: {0}".format(self.ticker.version()))
        self.ticker.registerEvent({10000: [self.smellTheRoses, ]})
        self.ticker.registerEvent({self.slowBlinkTime: [self.showActivity, ]})
        blinkTime = self.fastBlinkTime if self.fastBlink else self.slowBlinkTime
        self.ticker.registerEvent({blinkTime: [self.updateLights, ]})

    def __str__(self):
        return "Condition: {0} TriggerInterval: {1} Light on: {2} Red on: {3}".format(self.currentCondition, self.triggerInterval, self.lightOn, self.redLightOn)

    def shutdown(self):
        print("Deleting the ticker")
        self.ticker.shutdown()

    def getTriggerInterval(self):
        return self.triggerInterval

    def isTimeToStop(self):
        return self.stopButton.value() == 0

    def getStationAddress(self):
        fullAddress = (~self.address8.value() % 2) * 8 + (~self.address4.value() % 2) * 4 + (
                    ~self.address2.value() % 2) * 2 + (~self.address1.value() % 2)
        return fullAddress

    def winkLEDS(self, delayTime):
        for count in range(0, 2):
            self.redLED.on()
            self.redLED.on()
            time.sleep(delayTime)
            self.redLED.off()
            self.greenLED.on()
            time.sleep(delayTime)
            self.greenLED.off()

    def showActivity(self, callingArgument):
        print(".", end='')
        # print("Current time: {0}".format(time.ticks_ms()))

    def smellTheRoses(self, callingArgument):
        stateChanged = self.waterSensor.getCurrentInputState() != self.waterSensor.updateCurrentSensorValue()
        print("Checking the roses... {0}".format(self.currentCondition))
        if stateChanged:
            print("Moisture state changed to: {0}".format(levels[self.currentCondition]))
            self.currentCondition = self.waterSensor.getCurrentInputState()
            oldFastBlink = self.fastBlink
            self.setLightStates()
            if oldFastBlink != self.fastBlink:      # Blink speed changed
                if self.fastBlink:                  # It was fast, make it slow
                    self.ticker.registerEvent({self.fastBlinkTime: [self.updateLights, ]})
                    self.ticker.registerEvent({self.slowBlinkTime: [self.updateLights, ]})
                else:
                    self.ticker.registerEvent({self.slowBlinkTime: [self.updateLights, ]})
                    self.ticker.registerEvent({self.fastBlinkTime: [self.updateLights, ]})
            self.updateLights("Dummy")
            import gc
            gc.collect()
            print("Free RAM: {0}".format(gc.mem_free()))
            sendNotification(self.stationAddress, messages[levels[self.currentCondition]])
            print("Currently red is {0} and blink is {1}".format(self.redLightOn, self.triggerInterval))

    def setLightStates(self):
        self.redLightOn, self.fastBlink = ledStates[self.waterSensor.getCurrentInputState()]
        return None

    def updateLights(self, callingArgument):
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
    thisPlant.winkLEDS(.2)  # Successful powerup indication
    # print(thisPlant)
    print("Station number: {0}".format(thisPlant.getStationAddress()))
    stopTime = thisPlant.isTimeToStop()

    while not stopTime:
        stopTime = thisPlant.isTimeToStop()
        # print(".", end='')
        # time.sleep(thisPlant.getTriggerInterval())
    thisPlant.shutdown()
    exit()

