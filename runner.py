import RPi.GPIO as gpio
import time

class Runner:
	p_A_X = 11 #GPIO. 0
	p_A_Y = 12 #GPIO. 1
	p_B_X = 13 #GPIO. 2
	p_B_Y = 15 #GPIO. 3
	speed = 0
	degree = 0
	is_front = True
	is_initialized = False
	is_cleanedup = False
	now_control = 0

	def __init__(self, control):
		if not Runner.is_initialized:
			Runner.initialize()
		self.control = control
		print(f'{control} Runner READY')

	@staticmethod
	def initialize():
		Runner.is_initialized = True
		gpio.setmode(gpio.BOARD)
		time.sleep(0.5)
		gpio.setup(Runner.p_A_X, gpio.OUT)
		gpio.setup(Runner.p_A_Y, gpio.OUT)
		gpio.setup(Runner.p_B_X, gpio.OUT)
		gpio.setup(Runner.p_B_Y, gpio.OUT)
		time.sleep(0.5)
		Runner.pwm_A_X = gpio.PWM(Runner.p_A_X, 256) # pinnummber, Hz
		Runner.pwm_A_Y = gpio.PWM(Runner.p_A_Y, 256)
		Runner.pwm_B_X = gpio.PWM(Runner.p_B_X, 256)
		Runner.pwm_B_Y = gpio.PWM(Runner.p_B_Y, 256)
		time.sleep(0.5)
		Runner.pwm_A_X.start(0)
		Runner.pwm_A_Y.start(0)
		Runner.pwm_B_X.start(0)
		Runner.pwm_B_Y.start(0)
		time.sleep(0.5)

	def go(self):
		if not self.control_check(): return
		if Runner.speed < 10: return
		s = Runner.speed
		pwm = (0, 0, 0, 0)
		'''
		if -15 <= Runner.degree <= 15:
			pwm = (s, 0, s, 0)
		elif 15 <= Runner.degree < 45:
			pwm = (s*.9, 0, 100, 20)
		elif 45 <= Runner.degree <= 75:
			pwm = (s*.8, 0, 100, 60)
		elif 75 <= Runner.degree <= 105:
			pwm = (s*.7, 0, 100, 100)
		elif 105 <= Runner.degree <= 135:
			pwm = (0, s*.7, 50, 100)
		elif 135 <= Runner.degree <= 165:
			pwm = (0, s*.8, 30, 100)
		elif -45 < Runner.degree <= -15:
			pwm = (100, 30, s*.9, 0)
		elif -75 <= Runner.degree <= -45:
			pwm = (100, 50, s*.8, 0)
		elif -105 <= Runner.degree <= -75:
			pwm = (100, 100, s*.7, 0)
		elif -135 <= Runner.degree <= -105:
			pwm = (60, 100, 0, s*.7)
		elif -165 <= Runner.degree <= -135:
			pwm = (20, 100, 0, s*.8)
		elif 165 <= Runner.degree or Runner.degree <=-165:
			pwm = (0, s, 0, s)
		'''
		d = Runner.degree
		if 0 <= d <= 90:
			pwm = (s, 0, s, (abs(d)/90) * 100)
		elif -90 <= d <= 0:
			pwm = (s, (abs(d)/90) * 100, s, 0)
		elif 90 <= d <= 180:
			pwm = (0, s, ((180-abs(d))/90) * 100, s)
		elif -180 <= d <= -90:
			pwm = (((180-abs(d))/90) * 100, s, 0, s)
			
		print(f'go! degree: {Runner.degree} pwm : {pwm}')
		Runner.pwm_A_X.ChangeDutyCycle(pwm[0])
		Runner.pwm_A_Y.ChangeDutyCycle(pwm[1])
		Runner.pwm_B_X.ChangeDutyCycle(pwm[2])
		Runner.pwm_B_Y.ChangeDutyCycle(pwm[3])
	
	# 0 ~ 100
	def setspeed(self, speed):
		if not self.control_check(): return
		if speed < 0: speed = 0
		if speed > 100: speed = 100
		Runner.speed = speed
		print(f'speed : {speed}')

	def addspeed(self, add_num):
		if not self.control_check(): return
		self.setspeed(Runner.speed + add_num)
	
	def getspeed(self):
		return Runner.speed
	
	# -180 ~ 180
	def setdegree(self, degree):
		if not self.control_check(): return
		degree = degree % 360
		if degree > 180: degree -= 360
		Runner.degree = degree
	
	def stop(self):
		if not self.control_check(): return
		Runner.pwm_A_X.ChangeDutyCycle(0)
		Runner.pwm_A_Y.ChangeDutyCycle(0)
		Runner.pwm_B_X.ChangeDutyCycle(0)
		Runner.pwm_B_Y.ChangeDutyCycle(0)
	
	def cleanup(self):
		if not Runner.is_cleanedup:
			Runner.is_cleanedup = True
			Runner.pwm_A_X.stop()
			Runner.pwm_A_Y.stop()
			Runner.pwm_B_X.stop()
			Runner.pwm_B_Y.stop()
			gpio.cleanup()
	
	def control_check(self):
		if Runner.now_control == self.control:
			return True
		else:
			return False
	
	def take_control(self):
		if Runner.now_control < self.control:
			Runner.now_control = self.control
			print(f'{self.control} takes control')
			return True
		elif Runner.now_control == self.control:
			return True
		else:
			return False
	
	def release_control(self):
		if Runner.now_control == self.control:
			Runner.now_control = -10000
			print(f'{self.control} releases control')
			return True
		else:
			return False
