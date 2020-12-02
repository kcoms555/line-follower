# line-follower
Implementation of a line follwer robot based on image processing

#### video/
video/* are from 'imutils' library.  
As it was necessary to add blocking I/O operation in pivideostream.read(), I cloned and modified them.  

# A flowchart of image processing and vehicle control
![flowchartEn](https://user-images.githubusercontent.com/48780754/100902173-fec07100-3507-11eb-8bb4-0fd6fb4a758f.png)  
A direction vector in the image above is used to set a speed and a degree of the vehicle. It is roughly enough to run a track with simple closed curve.

# Results
![image](https://user-images.githubusercontent.com/48780754/100899909-ab4d2380-3505-11eb-8a78-92a194e4922b.png)
Track 1  
Clockwise : takes 9 seconds (1.4 km/h)  
Anticlockwise : takes 10 seconds (1.26 km/h)  

![image](https://user-images.githubusercontent.com/48780754/100899953-b30cc800-3505-11eb-91ef-c3c6bf54a81f.png)
Track 2  
Clockwise : takes 13 seconds (0.96 km/h)  
Anticlockwise : takes 13 seconds (0.96 km/h)  
