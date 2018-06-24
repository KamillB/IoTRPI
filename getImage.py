from picamera import PiCamera
import time
import io

url = 'http://192.168.0.112:8080/rpi_data/temp'

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

def getimage():
	camera = PiCamera()
	camera.start_preview()
	time.sleep(10)
	camera.capture('/home/pi/image.jpg')
	camera.stop_preview()
	return 
	
while True:
#	print(read_temp())
	time.sleep(15)
	getimage()
	f = open('image.jpg', 'r+')
	jpgdata = f.read()
	f.close()
	
	payload = {
		"id" : 1,
		"name" : getserial(),
		"image" : jpgdata.encode('base64')
	}
	headers = { 'content-type' : 'application/json' }
	response = requests.post(url, data=json.dumps(payload), headers=headers)	