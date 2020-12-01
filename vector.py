import math
def get_vector_sum(A, B):
	return (A[0]+B[0], A[1]+B[1])
def get_vector_len(vector):
	return (vector[0]**2 + vector[1]**2)**(1./2)
def get_angle(v1, v2):
	l1 = get_vector_len(v1)
	l2 = get_vector_len(v2)
	if l1 * l2 == 0:
		return 0
	angle_asin_rad = math.asin((v1[0]*v2[1]-v1[1]*v2[0])/(l1 * l2))
	angle_acos_rad = math.acos((v1[0]*v2[0]+v1[1]*v2[1])/(l1 * l2)) # pi ~ 0
	if angle_asin_rad >= 0:
		rad = angle_acos_rad
	else:
		rad = -angle_acos_rad
	return rad * 180 / math.pi
def get_angle_v2(v1, v2):
	l1 = get_vector_len(v1)
	l2 = get_vector_len(v2)
	if l1 * l2 == 0:
		return 0
	angle_asin_rad = math.asin((v1[0]*v2[1]-v1[1]*v2[0])/(l1 * l2))
	return angle_asin_rad * 180 / math.pi
def get_angle_v3(v1, v2):
	l1 = get_vector_len(v1)
	l2 = get_vector_len(v2)
	if l1 * l2 == 0:
		return 0
	angle_acos_rad = math.acos((v1[0]*v2[0]+v1[1]*v2[1])/(l1 * l2)) # pi ~ 0
	return angle_acos_rad * 180 / math.pi
