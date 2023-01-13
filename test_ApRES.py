from ApRES_RTK_SAR import ApRES_RTK_SAR as ARS
import time
import datetime

InitiateLogger = True
InitiateGPS = True
InitiateApRES = True
while True:
    obj = ARS(InitiateLogger,InitiateGPS,InitiateApRES,"Neumayer")
    if (obj.flagLogger == InitiateLogger) and (obj.flagGPS == InitiateGPS) and (obj.flagApRES == InitiateApRES):
        break
    else:
        print("ERROR: Fix the failed device")        
        time.sleep(2)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Radar Parameters
obj.DownloadFolder = 'test'
obj.n_subburst = 5
obj.attenuators = [25]
obj.gains = [-14]
obj.n_attenuator = 1
obj.tx = [1,1,0,0,0,0,0,0]
obj.rx = [1,1,0,0,0,0,0,0]
obj.DownloadFile = False
obj.polarization = "ThhhhR"
obj.prefix = ""
ARS.ApRES_Set(obj) # Set the burst parameters to the ApRES
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Other Parameters
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
obj.wpl_int = 0.5

t0rad = now
while True: 
    ARS.updateGPS(obj)
    ARS.updateDistance(obj)
    if ARS.DeltaTime(obj,t0rad) > 5:
        ARS.robustBurst(obj)
        t0rad = datetime.datetime.now()