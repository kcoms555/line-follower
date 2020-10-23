# import the necessary packages
from video.videostream import VideoStream
from flask import Response
from flask import Flask
from flask import render_template
from runner import Runner
import threading
import argparse
import time
import cv2
import numpy as np
import wscontroller as wc


# initialize a flask object
app = Flask(__name__)

@app.route("/")
def index():
	# return the rendered template
	return render_template("index.html")

@app.route("/video_feed1")
def video_feed1():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate1(), mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/video_feed2")
def video_feed2():
	# return the response generated along with the specific media
	# type (mime type)
	return Response(generate2(), mimetype = "multipart/x-mixed-replace; boundary=frame")



# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
runnerlock = threading.Lock()
outputFrame1 = None
outputlock1 = threading.Lock()
outputFrame2 = None
outputlock2 = threading.Lock()
cam_frame_counter = 0

# vs will be initailized with args
vs = None
runner = Runner(-1)

def process_video(framerate):
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame1, outputlock1, outputFrame2, outputlock2, cam_frame_counter, runner

	# loop over frames from the video stream
	while True:
		# read the next frame from the video stream
		origin_frame = vs.read()

		#origin_frame = cv2.medianBlur(origin_frame, 9)

		# convert the frame to grayscale
		gray = cv2.cvtColor(origin_frame, cv2.COLOR_BGR2GRAY)

		#gray = cv2.GaussianBlur(gray, (5, 5), 9)
		#gray = cv2.medianBlur(gray, 5)

		mean = np.mean(gray)

		ret, gray = cv2.threshold(gray, mean/2, 255, cv2.THRESH_BINARY_INV)
		#bwi = cv2.adaptiveThreshold(bwi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
		m = cv2.moments(gray, False)
		height, width = gray.shape
		hathird = int(height/3)
		wathird = int(width/5)
		gray = np.vstack([gray[:hathird], gray[hathird:hathird*2]*(3/6), gray[hathird*2:]*(1/6)])
		gray = np.hstack([gray[:,:wathird], gray[:,wathird:wathird*2]*(3/6), gray[:,wathird*2:wathird*3]*(1/6), gray[:,wathird*3:wathird*4]*(3/6), gray[:,wathird*4:]])
		m2 = cv2.moments(gray, False)

		if m["m00"] == 0:
			cX = int(width/2)
			cY = int(height/2)
		else:
			cX = int(m["m10"] / m["m00"])
			cY = int(m["m01"] / m["m00"])
		if m2["m00"] == 0:
			cX2 = int(width/2)
			cY2 = int(height/2)
		else:
			cX2 = int(m2["m10"] / m2["m00"])
			cY2 = int(m2["m01"] / m2["m00"])
		cv2.circle(origin_frame, (cX, cY), 5, (255, 255, 255), -1)
		cv2.circle(origin_frame, (cX2, cY2), 5, (255, 255, 0), -1)


		if cam_frame_counter % framerate == 0:
			print(f'mean : {mean}')
			print(gray.shape)
			print(f'cX, cY : {cX, cY}')
			print(f'cX2, cY2 : {cX2, cY2}')
			#print(gray[:athird])
			#print(gray[athird:athird*2])
			#print(gray[athird*2:])
		
		# acquire the lock, set the output frame, and release the lock
		with outputlock1:
			outputFrame1 = origin_frame.copy()

		with outputlock2:
			outputFrame2 = gray.copy()

		cam_frame_counter += 1

		if not runner.control_check():
			if not runner.take_control():
				continue
		
		width_mid = width/2
		center = cX2 - 0 # bias
		if center < 0: center = 0
		# weight is -1 ~ 1
		weight = (center - width_mid)/width_mid
		weight *= 2
		if weight > 1: weight = 1
		if weight < -1: weight = -1

		runner.setdegree(weight * 90) # -90 ~ 90
		runner.go()

# grab global references to the output frame and lock variables
# loop over frames from the output stream
# wait until the lock is acquired
# check if the output frame is available, otherwise skip
# the iteration of the loop
# encode the frame in JPEG format
# ensure the frame was successfully encoded
# yield the output frame in the byte format
def generate1():
	global outputFrame1, outputlock1, cam_frame_counter
	while outputFrame1 is None:
		time.sleep(1)
		continue
	frame_counter = 0
	while True:
		if frame_counter == cam_frame_counter:
			time.sleep(0.01)
			continue
		frame_counter = cam_frame_counter
		with outputlock1:
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame1)
			if not flag:
				continue
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')

def generate2():
	global outputFrame2, outputlock2, cam_frame_counter
	while outputFrame2 is None:
		time.sleep(1)
		continue
	frame_counter = 0
	while True:
		if frame_counter == cam_frame_counter:
			time.sleep(0.01)
			continue
		frame_counter = cam_frame_counter
		with outputlock2:
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame2)
			if not flag:
				continue
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
			bytearray(encodedImage) + b'\r\n')



# check to see if this is the main thread of execution
if __name__ == '__main__':
	# construct the argument parser and parse command line arguments
	ap = argparse.ArgumentParser()
	ap.add_argument("-i", "--ip", type=str, default="0.0.0.0",
		help="ip address of the device")
	ap.add_argument("-p", "--port", type=int, required=True,
		help="ephemeral port number of the server (1024 to 65535)")
	ap.add_argument("-x", "--width", type=int, default=320,
		help="width size of camera")
	ap.add_argument("-y", "--height", type=int, default=240,
		help="height size of camera")
	ap.add_argument("-f", "--framerate", type=int, default=32,
		help="# of frames used to construct the background model")
	args = vars(ap.parse_args())

	# initialize the video stream and allow the camera sensor
	vs = VideoStream(usePiCamera=True, resolution=(args["width"], args["height"]), 
		framerate=args["framerate"]).start()

	# camera warmup
	time.sleep(2.0)

	# start a thread that will perform motion detection
	t = threading.Thread(target=process_video, args=(args["framerate"], ) )
	t.daemon = True
	t.start()
	wc.run()
	# start the flask app
	app.run(host=args["ip"], port=args["port"], debug=True,
		threaded=True, use_reloader=False)


# release the video stream pointer
vs.stop()
runner.cleanup()

