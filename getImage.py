from picamera import PiCamera
import time
import io
import json
import requests
import datetime
import base64
from PIL import Image
import cStringIO

url = 'http://192.168.0.112:8080/rpi/image'

camera = PiCamera()
camera.rotation = 180
SLEEP_TIMER = 1



def getserial():
 	# Extract serial from cpuinfo file
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


## Saves image to jpg
def getimage():
	camera.start_preview()
	time.sleep(SLEEP_TIMER)
	camera.capture('/home/pi/image.jpg')
	camera.stop_preview()
	return


## returns base64 version of taken image
def getbinimage():
	camera.start_preview()
	time.sleep(SLEEP_TIMER)
	stream = io.BytesIO()
	camera.capture(stream, 'jpeg')	
	return base64.b64encode(stream.getvalue())	

while True:
	#time.sleep(1)
	#getimage()

	#imgFile = 'image.jpg'
	#with open(imgFile, "rb") as imageFile:
		#encoded = base64.b64encode(imageFile.read())

	#image = str(encoded)
	#image = image[2:-1]

	image = getbinimage()
	payload = {
		"ownerSerialNumber" : getserial(),
		"name" : 'main camera',
		"milis" : time.mktime(datetime.datetime.now().timetuple()),
		"image" : image,
	}

	headers = { 'content-type' : 'application/json' }
	response = requests.post(url, data=json.dumps(payload), headers=headers)	