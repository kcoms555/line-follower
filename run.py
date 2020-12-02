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
from vector import get_angle


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
outputFrame1 = None
outputlock1 = threading.Lock()
outputFrame2 = None
outputlock2 = threading.Lock()
cam_frame_counter = 0

# vs will be initailized with args
vs = None
runner = Runner(-1)

compensated_angle_sign = 1
def get_compensated_angle(angle, is_compensatable = False):
	global compensated_angle_sign
	if abs(angle * compensated_angle_sign) < 60:
		if is_compensatable:
			if angle > 0:
				compensated_angle_sign = 1
			else:
				compensated_angle_sign = -1
		return angle
	elif angle * compensated_angle_sign > 0:
		return angle
	else:
		return 90 * compensated_angle_sign

def get_continuous_point(point1, point2, target):
	global compensated_angle_sign
	direction_angle = get_angle([point1[0] - point2[0], point1[1] - point2[1]], (0, 1))
	forward = None
	backward = None
	if abs(direction_angle) < 15:
		if point1[1] > point2[1]:
			forward = point1
			backward = point2
		else:
			forward = point2
			backward = point1
	else:
		if compensated_angle_sign > 0:
			if point1[0] > point2[0]:
				forward = point1
				backward = point2
			else:
				forward = point2
				backward = point1
		else:
			if point1[0] < point2[0]:
				forward = point1
				backward = point2
			else:
				forward = point2
				backward = point1
	if target == 'forward':
		return forward
	elif target == 'backward':
		return backward
	else:
		return None
	
# input : gray scale image, output : Two points from end of line and reliability of return(0~1).
def get_two_points_of_line_from_gray(gray_image):
	height, width = gray_image.shape
	
	# find contour
	vx, vy, x, y = 0, -1, int(width/2), int(height/2)
	line_angle = 0
	contours, hierarchy = cv2.findContours(gray_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2:]

	# point1, point2 are two points of end of line.
	line_rel = 0
	point1 = (0, 0)
	point2 = (0, 0)

	if len(contours) > 0:
		contours.sort(key=lambda ar: cv2.contourArea(ar))
		largest_contour = contours[-1]
		[vx, vy, x, y] = cv2.fitLine(largest_contour, cv2.DIST_L2, 0, 0.01, 0.01)

		# get two points and line reliability
		line_count = 0
		line_gray_nz_count = 0
		lcx = x
		lcy = y
		while(True):
			lcx += vx
			lcy += vy
			if 0 <= lcx <= width-1 and 0 <= lcy <= height-1:
				line_count += 1
				if gray_image[int(lcy), int(lcx)] != 0:
					line_gray_nz_count += 1
			else:
				break
		point1 = (lcx[0], lcy[0])

		lcx = x
		lcy = y
		while(True):
			lcx -= vx
			lcy -= vy
			if 0 <= lcx <= width-1 and 0 <= lcy <= height-1:
				line_count += 1
				if gray_image[int(lcy), int(lcx)] != 0:
					line_gray_nz_count += 1
			else:
				break
		point2 = (lcx[0], lcy[0])

		line_rel = 0 if line_count == 0 else 1. * line_gray_nz_count/line_count
			
		# y-axis is fliped. To get angle, vy should be fliped.
		vxf = vx[0]
		vyf = -vy[0]
		if vyf < 0:
			vxf = -vxf
			vyf = -vyf
		line_angle = get_compensated_angle(get_angle((vxf, vyf), (0, 1)), True)
	return point1, point2, line_rel, line_angle

def get_blockscaled_gray(gray, hblocks, wblocks, hscale, wscale):
	height, width = gray.shape

	hblock = int(height/hblocks)
	wblock = int(width/wblocks)

	scaled_gray = gray.copy()
	for i in range(hblocks):
		if i == hblocks-1:
			scaled_gray[hblock*i:] = scaled_gray[hblock*i:] * ((hscale)**i)
		else:
			scaled_gray[hblock*i:hblock*(i+1)] = scaled_gray[hblock*i:hblock*(i+1)] * ((hscale)**i)

	for i in range(wblocks):
		maxi = (1.*(wblocks-1)/2.0)
		multiplier = maxi - abs(i-maxi)
		if i == wblocks-1:
			scaled_gray[:,wblock*i:] = scaled_gray[:,wblock*i:] * ((wscale)**multiplier)
		else:
			scaled_gray[:,wblock*i:wblock*(i+1)] = scaled_gray[:,wblock*i:wblock*(i+1)] * ((wscale)**multiplier)
	return scaled_gray
	
def get_center_from_moment(gray_image):
	height, width = gray_image.shape
	m = cv2.moments(gray_image, False)
	found = False
	if m["m00"] == 0:
		found = False
		cX = int(width/2)
		cY = int(height/2)
	else:
		found = True
		cX = int(m["m10"] / m["m00"])
		cY = int(m["m01"] / m["m00"])
	return cX, cY, found
	

def process_video(framerate):
	# grab global references to the video stream, output frame, and
	# lock variables
	global vs, outputFrame1, outputlock1, outputFrame2, outputlock2, cam_frame_counter, runner
	base_speed = 0

	# loop over frames from the video stream
	while True:
		# read the next frame from the video stream
		origin_frame = vs.read()
		origin_frame = cv2.flip(origin_frame, 0)
		origin_frame = cv2.flip(origin_frame, 1)

		# cut image
		origin_frame = origin_frame[:160,:]

		# convert the frame to grayscale
		gray = cv2.cvtColor(origin_frame, cv2.COLOR_BGR2GRAY)

		# make gray binary image
		_, gray = cv2.threshold(gray, np.mean(gray)*(3/5), 255, cv2.THRESH_BINARY_INV)
		height, width = gray.shape

		# get step by step downscaled gray image
		# downscaled_gray = get_blockscaled_gray(gray, 9, 9, 0.7, 0.7)

		# get center of moments
		cX, cY, _ = get_center_from_moment(gray)
		# cX2, cY2, _ = get_center_from_moment(downscaled_gray)

		# get two points from end of lines
		point1, point2, line_rel, line_angle = get_two_points_of_line_from_gray(gray)

		# get angle of two points
		# line_angle = get_compensated_angle(get_angle((point1[0]-point2[0], point1[1]-point2[1]), (0, 1)), True)

		# get forwarded point
		direction_point = get_continuous_point(point1, point2, 'forward')

		# draw line into origin_frame
		origin_frame = cv2.line(origin_frame, point1, point2, (0,0,255),2)

		cv2.circle(origin_frame, (cX, cY), 5, (255, 255, 255), -1)
		# cv2.circle(origin_frame, (cX2, cY2), 5, (255, 255, 0), -1)
		cv2.circle(origin_frame, direction_point, 5, (0, 255, 0), -1)
		
		# acquire the lock, set the output frame, and release the lock
		with outputlock1: outputFrame1 = origin_frame.copy()
		with outputlock2: outputFrame2 = gray.copy()

		# degree_from_momentum = ( (cX2 - (width/2)) / (width/2) ) * 90
		degree_from_end_of_line = ( (direction_point[0] - (width/2)) / (width/2) ) * 90

		degree = degree_from_end_of_line
		degree *= 1.5
		if degree > 90: degree = 90
		if degree < -90: degree = -90
		sweight = 0.7 + (0.3) * (1 - abs(degree)/90)

		cam_frame_counter += 1
		if cam_frame_counter % framerate == 0:
		#	print(f'degree_from_momentum : {degree_from_momentum}')
			print(f'degree_from_end_of_line : {degree_from_end_of_line}')
			print(f'degree : {degree}')
			print(f'line_angle : {line_angle}')
			print(f'line_rel : {line_rel}')

		# control runner
		if not runner.control_check():
			if not runner.take_control():
				continue
			base_speed = runner.getspeed()

		runner.setspeed(sweight * base_speed)
		runner.setdegree(degree) # -90 ~ 90
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

try:
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
finally:
	# release the video stream pointer
	vs.stop()
	runner.cleanup()

