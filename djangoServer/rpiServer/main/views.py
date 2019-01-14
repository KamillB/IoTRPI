from django.shortcuts import render
from django.http import HttpResponse
from . import configFile
from picamera import PiCamera
from rest_framework.parsers import JSONParser
import RPi.GPIO as GPIO
import io
import json
import requests
import os
import glob
import time
import datetime
import base64
import threading


workTemperature = False
workImage = False
sleep_time_temperature = configFile.temperatureRefreshRate
sleep_time_image = configFile.imageRefreshRate

# Number of seconds before camera takes a picture
CAMERA_WARMUP_TIMER = 0
camera = PiCamera()
# Rotate camera 
camera.rotation = 180

# Temp sensor setup
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(21, GPIO.OUT)
dioda = False

#################### INNER RASPBERRY METHODS ####################
# Extract serial from cpuinfo file
def getserial():
	cpuserial = "0000000000000000"
	try:
		f = open('/proc/cpuinfo','r')
		for line in f:
			if line[0:6]=='Serial':
				cpuserial = line[10:26]
		f.close()
	except:
		cpuserial = "ERROR000000000"
	return cpuserial 


# Get name of the Ethernet interface	
def getEthName():
	try:
		for root,dirs,files in os.walk('/sys/class/net'):
			for dir in dirs:
				if dir[:3]=='enx' or dir[:3]=='eth':
					interface=dir
	except:
		interface="None"
	return interface


# Return the MAC address of the specified interface
def getMAC(interface='eth0'):
	try:
		str = open('/sys/class/net/%s/address' %interface).read()
	except:
		str = "00:00:00:00:00:00"
	return str[0:17]


# Read raw temperature
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
	

# Read temperature and return it in celcius
def read_temp():
	lines = read_temp_raw()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1].find('t=')
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		temp_c = float(temp_string) / 1000.0
	#        temp_f = temp_c * 9.0 / 5.0 + 32.0
	#        return temp_c, temp_f
	return temp_c	


# Saves image to jpg
def getImage():
	camera.start_preview()
	time.sleep(CAMERA_WARMUP_TIMER)
	camera.capture('/home/pi/image.jpg')
	camera.stop_preview()
	return


# Returns base64 version of taken image
def getBinImage():
	camera.start_preview()
	time.sleep(CAMERA_WARMUP_TIMER)
	stream = io.BytesIO()
	camera.capture(stream, 'jpeg')	
	return base64.b64encode(stream.getvalue())


#################### HTTP METHODS ####################
def register():
	url = configFile.serverAddress + '/register'
	payload = {
		"mac" 			: getMAC(),
		"serialNumber" 	: getserial()
	}
	headers = { 'content-type' : 'application/json' }
	response = requests.post(url, data=json.dumps(payload), headers=headers)
	
	# save device key to file
	file = open("deviceKey.txt", "w+")
	file.write(str(response.content)[2:-1])
	file.close()
	configFile.deviceKey = str(response.content)[2:-1]
	


def changeKey():
	url = configFile.serverAddress + '/changeKey'
	payload = {
		"mac" 			: getMAC(),
		"serialNumber" 	: getserial()
	}
	headers = { 'content-type' : 'application/json' }
	response = requests.post(url, data=json.dumps(payload), headers=headers)
	
	# save device key to file
	file = open("deviceKey.txt", "w+")
	file.write(str(response.content)[2:-1])
	file.close()
	configFile.deviceKey = str(response.content)[2:-1]


def sendTemperature():
	global workTemperature
	while (workTemperature == True):
		url = configFile.serverAddress + '/temperature'
		payload = {
			"ownerSerialNumber" : getserial(),
			"temp" : read_temp(),
			"milis" : time.mktime(datetime.datetime.now().timetuple()),
			"name" : "Thermometer"
		}
		headers = { 'content-type' : 'application/json' }
		response = requests.post(url, data=json.dumps(payload), headers=headers)
		time.sleep(sleep_time_temperature)
		print(payload)


def sendImage():
	global workImage
	while (workImage == True):
		url = configFile.serverAddress + '/image'
		image = getBinImage()
		payload = {
			"ownerSerialNumber" : getserial(),
			"name" : 'Main Camera',
			"milis" : time.mktime(datetime.datetime.now().timetuple()),
			"image" : str(image)[2:-1],
		}
		headers = { 'content-type' : 'application/json' }
		response = requests.post(url, data=json.dumps(payload), headers=headers)
		time.sleep(sleep_time_image)


def sendPeriphery(pinNumber, status):
	url = configFile.serverAddress + '/periphery'
	payload = {
		"owner" : getserial(),
		"name" : "Diode",
		"milis" : time.mktime(datetime.datetime.now().timetuple()),
		"gpioBcm" : pinNumber,
		"status" : status
	}
	headers = { 'content-type' : 'application/json' }
	response = requests.post(url, data=json.dumps(payload), headers=headers)
	
		
def gpioOn(pinNumber):
	GPIO.output(pinNumber, GPIO.HIGH)
	global dioda 
	dioda = True
	sendPeriphery(pinNumber, GPIO.HIGH)
	
	
def gpioOff(pinNumber):
	GPIO.output(pinNumber, GPIO.LOW)
	global dioda
	dioda = False
	sendPeriphery(pinNumber, GPIO.LOW)


#################### VIEWS ####################
def handleServerMessages(request):
	if request.method == 'POST':
		data = JSONParser().parse(request)
		print(data)
		if (data.get('key') == configFile.deviceKey):
			global workImage
			global workTemperature
			global dioda
			
			if (data.get('type') == 'cameraOn'):
				if (workImage == False):
					workImage = True
					threading.Thread(target = sendImage).start()
			
			elif (data.get('type') == 'cameraOff'):
				if (workImage == True):
					workImage = False
			
			elif (data.get('type') == 'temperatureOn'):
				if (workTemperature == False):
					workTemperature = True
					threading.Thread(target = sendTemperature).start()
					
			elif (data.get('type') == 'temperatureOff'):
				if (workTemperature == True):
					workTemperature = False
			
			elif (data.get('type') == 'periphery') :
				if (dioda == False):
					gpioOn(21)
				elif (dioda == True):
					gpioOff(21)
					
			elif (data.get('type') == 'peripheryOff'):
				gpioOff(21)
				
			elif (data.get('type') == 'test'):
				threadlist = threading.enumerate()
				for p in threadlist:
					print(type(p))
			
			return HttpResponse('ok it works')
			
		else :
			return HttpResponse('Wrong device key')
	else :
		return HttpResponse('Wrong method, use POST')



##### RUN THESE ON RPI START #####
workImage = True
threading.Thread(target = sendImage).start()

workTemperature = True
threading.Thread(target = sendTemperature).start()

sendPeriphery(21, GPIO.LOW)

