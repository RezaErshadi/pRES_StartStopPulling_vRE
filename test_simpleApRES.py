import apreshttp
import datetime
import time
API_ROOT = "192.168.1.1"
API_KEY = "18052021"
api = apreshttp.API(API_ROOT)
api.setKey(API_KEY)
api.radar.config.set(nAtts = 1,
                    nBursts = 5,
                    rfAttnSet=25,
                    afGainSet=-14,
                    txAnt=(1,0,0,0,0,0,0,0),
                    rxAnt=(1,0,0,0,0,0,0,0))
while True:
    filename = "httpBurst_"+datetime.datetime.now().strftime("%Y%m%d_%H-%M-%S")+".dat"
    attempts = 1
    while attempts < 11:
        try:
            print(f"attempt {attempts}: Burst initiated")
            t0 = time.perf_counter()
            api.radar.burst(filename)
            api.radar.results(wait = True)
            attempts = 20
        except:
            print("Burst failed, trying again")
            attempts +=1
    print(f"Burst completed in: {round(time.perf_counter() - t0,1)} seconds")
    t0 = time.perf_counter()
    time.sleep(3)