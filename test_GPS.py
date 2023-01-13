from ApRES_RTK_SAR import ApRES_RTK_SAR as ARS
import time
import datetime

InitiateLogger = True
InitiateGPS = True
InitiateApRES = False
while True:
    obj = ARS(InitiateLogger,InitiateGPS,InitiateApRES,"Trimble")
    if (obj.flagLogger == InitiateLogger) and (obj.flagGPS == InitiateGPS) and (obj.flagApRES == InitiateApRES):
        break
    else:
        print("ERROR: Fix the failed device")        
        time.sleep(2)

obj.RTKsens = False
obj.stat = "moving forward"
obj.nPnt = 0
obj.refLat = [] 
obj.refLon = []
obj.moveDist = 0
obj.GPSfreq = 10 # Hz
obj.stepsize = 150  # cm
obj.min_err = obj.stepsize - (obj.stepsize*0.1)
obj.max_err = obj.stepsize + (obj.stepsize*0.5)
now = datetime.datetime.now()
obj.t0GPS = now
obj.t0_WPL = now
obj.wpl_int = 0.1

while True: 
    ARS.updateGPS(obj)
    ARS.updateDistance(obj)
    print(obj.quality)
    # time.sleep(3)