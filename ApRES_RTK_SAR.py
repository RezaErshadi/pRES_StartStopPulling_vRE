import socket
import pynmea2
import apreshttp
import os
import datetime
import logging
import time
from haversine import haversine, Unit

class ApRES_RTK_SAR:
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def __init__(self,_logger,_gps,_apres,whichGPS):
        self.flagLogger = False
        self.flagGPS = False
        self.flagApRES = False
        self.whichGPS = whichGPS
        if _logger == True:
            self.InitiateLogger()
        if _gps == True:
            self.InitiateGPS()
        if _apres == True:
            self.InitiateApRES()
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def InitiateLogger(self):
        try:
            print("INFO: initiating logger")
            now = datetime.datetime.now()
            nf = len(os.listdir("./LogFiles/"))
            LogFile = "./LogFiles/"+f"{nf+1}_InfoLog_{now.strftime('%m-%d-%Y_%H-%M-%S')}.txt"
            logging.basicConfig(filename=LogFile, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
            self.InfoLogger = logging.getLogger()
            self.InfoLogger.setLevel(logging.INFO)
            print("INFO: logger started")
            self.InfoLogger.info("logger started")
            self.flagLogger = True
        except:
            print("ERROR: logger failed to start")
            self.InfoLogger.error("logger failed to start")
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def InitiateGPS(self):
        try:
            print("INFO: initiating gps")
            self.PortGPS = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            if self.whichGPS == "Trimble":
                self.PortGPS.connect(('192.168.2.5',5017)) # Trimble
            elif self.whichGPS == "Neumayer":
                self.PortGPS.connect(('192.168.33.97',3007)) # Neumayer
            self.InfoLogger.info("INFO: gps started")
            print("INFO: gps started")
            self.flagGPS = True
        except:
            print("ERROR: gps failed to start")
            self.InfoLogger.error("gps failed to start")
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def InitiateApRES(self):
        try:
            print("INFO: initiating radar")
            API_ROOT = "192.168.1.1"
            API_KEY = "18052021"
            self.ApRES = apreshttp.API(API_ROOT)
            self.ApRES.setKey(API_KEY)
            self.InfoLogger.info("ApRES API Initiated")
            self.flagApRES = True
            print("INFO: radar started")
        except:
            self.InfoLogger.error("radar failed to start")
            print("ERROR: radar failed to start")
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def ApRES_Set(self):
        print("INFO: setting radar config")
        self.ApRES.radar.config.set(
                                    nAtts = self.n_attenuator,
                                    nBursts = self.n_subburst,
                                    rfAttnSet = tuple(self.attenuators),
                                    afGainSet = tuple(self.gains),
                                    txAnt = tuple(self.tx),
                                    rxAnt = tuple(self.rx)
                                    )
        print("INFO: radar config is set")
        self.InfoLogger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>") 
        self.InfoLogger.info(f"ApRES set: Number of sub-bursts --> {self.n_subburst}")                            
        self.InfoLogger.info(f"ApRES set: Number of attenuator --> {self.n_attenuator}")
        self.InfoLogger.info(f"ApRES set: Attenuatorslist --> {self.attenuators}")
        self.InfoLogger.info(f"ApRES set: Gains list --> {self.gains}")
        self.InfoLogger.info(f"ApRES set: Tx list --> {self.tx}")
        self.InfoLogger.info(f"ApRES set: Rx list --> {self.rx}")
        self.InfoLogger.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<") 
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def robustBurst(self):
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> File Name
        os.system("say 'Shooting'")
        self.nPnt += 1
        fn = f"{self.nPnt}_SARRTK_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".dat"
        print(f"INFO: burst file name: {fn}")
        TRY_BURST_TIMEOUT = 30 # seconds
        GET_RESULTS_TIMEOUT = 60 # seconds
        last_burst = time.perf_counter()
        attempts = 1
        while (time.perf_counter() - last_burst) < TRY_BURST_TIMEOUT:
            try:
                print(f"INFO: burst started (attempt: {attempts})")
                self.InfoLogger.info(f"burst started (attempt: {attempts})")
                t0burst = datetime.datetime.now()
                self.ApRES.radar.burst(fn)
                print("INFO: burst finished")
                self.InfoLogger.info("burst finished")
                last_burst = time.perf_counter()
                break
            except apreshttp.RadarBusyException:
                print("WARNING: radar busy, trying again")
                self.InfoLogger.warning("radar busy, trying again")
                os.system("say 'radar busy trying again'")
                attempts+=1
            except ConnectionError:
                print("WARNING: connection to radar rejected, trying again")
                self.InfoLogger.warning("connection to radar rejected, trying again")
                os.system("say 'hold on'")
                attempts+=1
        if (time.perf_counter() - last_burst) >= TRY_BURST_TIMEOUT:
            print(f"CRITICAL: burst failed after trying for {TRY_BURST_TIMEOUT} seconds")
            print("CRITICAL: not getting results")
            self.InfoLogger.critical(f"burst failed after trying for {TRY_BURST_TIMEOUT} seconds")
            self.InfoLogger.critical("not getting results")
            os.system("say 'fatal error'")
            os.system("say 'restart the system'")
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> try to get the results
        last_results = time.perf_counter()
        results_obj = None
        os.system("say 'waiting'")
        t = 0
        while True:
            print(f"{t}/27")
            time.sleep(1)
            t +=1
            if t > 27:
                break
        # while (time.perf_counter() - last_results) < GET_RESULTS_TIMEOUT:
        #     try:
        #         print("INFO: attempting result")
        #         self.InfoLogger.info("attempting result")
        #         os.system("say 'attempting result'")
        #         results_obj = self.ApRES.radar.results(wait = True)
        #         last_results = time.perf_counter()
        #         break
        #     except ConnectionError:
        #         print("WARNING: connection to radar rejected, trying again")
        #         self.InfoLogger.warning("WARNING: connection to radar rejected, trying again")
        #         os.system("say 'hold on'")     
        # if (time.perf_counter() - last_results) >= GET_RESULTS_TIMEOUT:
        #     print(f"CRITICAL: could not get results after trying for {GET_RESULTS_TIMEOUT} seconds")
        #     print("CRITICAL: returning none")
        #     self.InfoLogger.critical(f"could not get results after trying for {GET_RESULTS_TIMEOUT} seconds.")
        #     self.InfoLogger.critical("returning none")
        #     os.system("say 'fatal error'")
        #     os.system("say 'restart the system'")
        #     return None
        # else:
        #     burstdur = self.DeltaTime(t0burst)
        # print(f"INFO: got burst results for filename '{results_obj.filename}'")
        # print(f"INFO: burst proccess duration: {burstdur}")
        # self.InfoLogger.info(f"got burst results for filename '{results_obj.filename}'")
        # self.InfoLogger.info(f"burst proccess duration: {burstdur}")
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Download
        try:
            if self.DownloadFile == True:
                dlpath = f"./DownloadedFiles/{self.DownloadFolder}/"
                if not os.path.exists(fn):
                    print("INFO: download started")
                    self.InfoLogger.info("download started") 
                    self.ApRES.data.download("Survey/" + fn)
                    if not os.path.exists(dlpath):
                        os.makedirs(dlpath)
                    os.system(f"mv {fn} {dlpath}")
                    print("INFO: download finished")
                    self.InfoLogger.info("download finished") 
                    os.system("say 'download finished'")
        except:
                print("ERROR: download failed")
                self.InfoLogger.error("download failed") 
                os.system("say 'download failed'")
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        print(f"INFO: point name --> {fn}")
        print(f"INFO: point info: {self.nPnt},{self.time},{self.lat},{self.lon},{self.alt},{self.moveDist},{self.iquality}")
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<") 
        self.InfoLogger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        self.InfoLogger.info(f"#PointName${fn}")
        self.InfoLogger.info(f"#PointInfo${self.nPnt},{self.time},{self.lat},{self.lon},{self.alt},{self.moveDist},{self.iquality}")
        self.InfoLogger.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<") 
        os.system("say 'DONE'")
        time.sleep(1)
        os.system("say 'GO'")
        return results_obj
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    # def ApRES_Burst(self):
    #     # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> File Name
    #     self.nPnt += 1
    #     fn = f"{self.nPnt}_SARRTK_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+".dat"
    #     print(f"INFO: burst file name: {fn}")
    #     # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Burst
    #     attempts = 1
    #     while True:
    #         try:
    #             print(f"INFO: burst started (attempt: {attempts})")
    #             self.InfoLogger.info(f"burst started (attempt: {attempts})") 
    #             self.ApRES.radar.burst(fn)
    #             self.ApRES.radar.results(wait = True)
    #             print("INFO: burst finished")
    #             self.InfoLogger.info("burst finished") 
    #             break
    #         except:
    #             attempts+=1
    #             time.sleep(7)
    #             self.InitiateApRES()
    #             self.ApRES_Set()
    #             os.system("say 'burst failed trying again'")
    #             print("ERROR: burst attempt failed, trying again")
    #             self.InfoLogger.error("burst attempt failed, trying again") 
    #     # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Download
    #     try:
    #         if self.DownloadFile == True:
    #             dlpath = f"./DownloadedFiles/{self.DownloadFolder}/"
    #             if not os.path.exists(fn):
    #                 print("INFO: download started")
    #                 self.InfoLogger.info("download started") 
    #                 self.ApRES.data.download("Survey/" + fn)
    #                 if not os.path.exists(dlpath):
    #                     os.makedirs(dlpath)
    #                 os.system(f"mv {fn} {dlpath}")
    #                 print("INFO: download finished")
    #                 self.InfoLogger.info("download finished") 
    #     except:
    #             print("ERROR: download failed")
    #             self.InfoLogger.error("download failed") 
    #     print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    #     print(f"INFO: point name --> {fn}")
    #     print(f"INFO: point info: {self.nPnt},{self.time},{self.lat},{self.lon},{self.alt},{self.moveDist}")
    #     print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<") 
    #     self.InfoLogger.info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    #     self.InfoLogger.info(f"#PointName${fn}")
    #     self.InfoLogger.info(f"#PointInfo${self.nPnt},{self.time},{self.lat},{self.lon},{self.alt},{self.moveDist},{self.iquality},{fn}")
    #     self.InfoLogger.info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<") 
    #     os.system("say 'burst done'")
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def DecimalDegree(self,x,dir):
        Deg = int(x) // 100
        Min = x - (100 * Deg)
        dd = round(Deg + Min / 60,7)
        conA = (dir == "N" and dd<0)
        conB = (dir == "S" and dd>0)
        conC = (dir == "E" and dd<0)
        conD = (dir == "W" and dd>0)
        if conA or conB or conC or conD:
            dd = -dd
        return dd
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def ParseGGA(self,sGGA):
        GGAmsg = pynmea2.parse(sGGA)
        # self.time = str(GGAmsg.timestamp)
        t = str(GGAmsg.timestamp)
        tt = t.split(':')
        H = tt[0]
        M = tt[1]
        S = tt[2]
        if len(S) > 4:
            S = S[0:5]
        self.time = f"{H}{M}{S}"
        self.lat = self.DecimalDegree(float(GGAmsg.lat),GGAmsg.lat_dir)
        self.lon = self.DecimalDegree(float(GGAmsg.lon),GGAmsg.lon_dir)
        self.alt = round( (float(GGAmsg.altitude)) ,2)
        self.geoid = float(GGAmsg.geo_sep)
        iq = GGAmsg.gps_qual
        q = ["NotAvailable", #0
            "GPSfix", #1
            "DifferentialGPS", #2
            "-",
            "RTKint", #4
            "RTKfloat"] #5
        self.iquality = iq
        self.quality = q[iq]
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def DeltaTime(self,t0):
        now =  datetime.datetime.now()
        d = now - t0
        return round(d.seconds + (d.microseconds)/1000000,1)
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def updateGPS(self):
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 
        # Update GPS pose
        while True:
            s = self.PortGPS.recv(1024)
            s = str(s.decode())
            a = s.split("\r\n")
            try:
                if len(a)>2:
                    ii = -2
                    while True:
                        if "GGA" in a[ii]:
                            ss = a[ii]
                            break
                        else:
                            ii -= 1
                    # print(f"ss----> {ss}")
                    self.ParseGGA(ss)
                    break
                else:
                    if "GGA" in s:
                        # print(f"s----> {s}")
                        self.ParseGGA(s)
                        break
            except:
                print("ERROR: gps parser failed")
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def updateDistance(self):  
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>       
        # update antenna displacement relative to the last measurement point
        if self.RTKsens == True: # error if there is no RTK
            RTKcond = self.iquality == 4 or self.iquality == 5
        elif self.RTKsens == False: # no sensitivity to RTK
            RTKcond =True
        if self.refLon == [] and self.refLat == []:
            self.refLat = self.lat
            self.refLon = self.lon
            self.moveDist = 0
        else:
            if RTKcond == True:
                self.moveDist = haversine((self.lat, self.lon), (self.refLat, self.refLon), unit=Unit.METERS) * 100
                self.moveDist = round(self.moveDist,0)
                self.rmndst = round(self.stepsize - self.moveDist,0)
                if self.stat != "well positioned":
                    if self.DeltaTime(self.t0_WPL) > self.wpl_int:
                        if self.rmndst>=0:
                            print(f"go forward --> {self.rmndst} [cm]")
                        else:
                            print(f"go backward --> {-self.rmndst} [cm]")
                        self.t0_WPL = datetime.datetime.now()
            else:
                os.system("say 'RTK is not available'")
                print("ERROR: rtk is not available")
                self.InfoLogger.error("rtk is not available")
                time.sleep(2)
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
# |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
    def triggerApRES(self):     
        if self.iquality == 4 or self.iquality == 5: 
            # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Radar passed the point while moving forward
            if self.stat == "moving forward":
                if self.moveDist > self.max_err:
                    self.stat = "moving backward"
                    os.system("say 'Wait'")
                    os.system("say 'Stop'")
                    os.system("say 'Go Back' ")
                    os.system(f"say '{round(self.moveDist-self.max_err,0)} to {round(self.moveDist-self.min_err,0)} centimeters'")
            # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Radar passed the point while moving backward
            if self.stat == "moving backward":
                if self.moveDist < self.min_err:
                    self.stat = "moving forward"
                    os.system("say 'Wait'")
                    os.system("say 'Stop'")
                    os.system("say 'Go Forward'")
                    os.system(f"say '{round(self.min_err-self.moveDist,0)} to {round(self.max_err-self.moveDist,0)} centimeters'")
            # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Radar well positioned
            if self.stat != "well positioned":
                if (self.moveDist > self.min_err) and (self.moveDist < self.max_err):
                    self.stat = "well positioned"
                    os.system("say 'Wait'")
                    time.sleep(1)
                    os.system("say 'Stop'")
                    self.robustBurst()
                    self.refLat = self.lat
                    self.refLon = self.lon
                    self.stat = "moving forward"      