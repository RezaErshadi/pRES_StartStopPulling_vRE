from ApRES_RTK_SAR import ApRES_RTK_SAR as ARS
import time
import datetime
import os

InitiateLogger = True
InitiateGPS = True
InitiateApRES = True
while True:
    obj = ARS(InitiateLogger,InitiateGPS,InitiateApRES,"Trimble")
    if (obj.flagLogger == InitiateLogger) and (obj.flagGPS == InitiateGPS) and (obj.flagApRES == InitiateApRES):
        break
    else:
        print("ERROR: Fix the failed device")        
        time.sleep(2)
time.sleep(1) # wait to properly initiate all the devices
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Radar Parameters
obj.DownloadFolder = 'RTK150cmMan'
obj.n_subburst = 5
obj.attenuators = [25]
obj.gains = [-14]
obj.n_attenuator = 1
obj.tx = [1,1,0,0,0,0,0,0]
obj.rx = [1,0,1,0,0,0,0,0]
obj.DownloadFile = False
obj.polarization = "ThhhhR"
obj.prefix = ""
obj.BurstTime = (obj.n_subburst * obj.n_attenuator * obj.tx.count(1) * obj.rx.count(1) * 1.1) + 1
ARS.ApRES_Set(obj) # Set the burst parameters to the ApRES
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Other Parameters
obj.RTKsens = True
obj.nPnt = 0
obj.refLat = [] 
obj.refLon = []
obj.moveDist = 0
obj.GPSfreq = 10 # Hz
obj.stepsize = 150  # cm
obj.min_err = obj.stepsize - (obj.stepsize*0.01)
obj.max_err = obj.stepsize + (obj.stepsize*0.07)
now = datetime.datetime.now()
obj.t0GPS = now
obj.t0_WPL = now
obj.wpl_int = 0.5
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> First point
ARS.updateGPS(obj)
os.system("say 'First Shot'")
ARS.robustBurst(obj)
obj.refLat = obj.lat
obj.refLon = obj.lon
obj.stat = "moving forward"
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Main loop
while True:
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Update GPS pose
    ARS.updateGPS(obj)
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Update distance to the last reference point
    ARS.updateDistance(obj)
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Radar well positioned, trigger the ApRES   
    ARS.triggerApRES(obj)