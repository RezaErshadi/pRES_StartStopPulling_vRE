import apreshttp
import datetime
import time
from requests.exceptions import ConnectionError

TRY_BURST_TIMEOUT = 30 # seconds
GET_RESULTS_TIMEOUT = 60 # seconds

API_ROOT = "192.168.1.1"
API_KEY = "18052021"
api = apreshttp.API(API_ROOT)
api.setKey(API_KEY)
api.radar.config.set(nAtts = 1,
                    nBursts = 5,
                    rfAttnSet=25,
                    afGainSet=-14,
                    txAnt=(1,1,0,0,0,0,0,0),
                    rxAnt=(1,1,0,0,0,0,0,0))
                    

count = 1
lastBursts = 1


def do_burst_and_get_results(apres):

    last_burst = time.perf_counter()
    while (time.perf_counter() - last_burst) < TRY_BURST_TIMEOUT:
        try:
            print("Attempting burst")
            t0burst = time.perf_counter()
            apres.radar.burst()
            # If we get to this point we've succesfully completed the burst 
            # update last_burst and get out of here!
            last_burst = time.perf_counter()
            break
        except apreshttp.RadarBusyException:
            print("Radar busy... trying again for {:f} more seconds...\n".format(
                TRY_BURST_TIMEOUT - (time.perf_counter() - last_burst)
            ))
        except ConnectionError:
            print("First Error")
            print("Connection to radar rejected... trying again for {:f} more seconds...\n".format(
                TRY_BURST_TIMEOUT - (time.perf_counter() - last_burst)
            ))
        
    # If we've exceeded the timeout period, then something bad has happened
    # or we need a longer timeout period...
    # 
    # Let's call this the burst has failed
    if (time.perf_counter() - last_burst) >= TRY_BURST_TIMEOUT:
        print("FATAL: Burst failed after trying for {:f} seconds.".format(TRY_BURST_TIMEOUT))
        print("Not getting results.")
        
    # Now we try and get the results
    last_results = time.perf_counter()
    results_obj = None
    while (time.perf_counter() - last_results) < GET_RESULTS_TIMEOUT:
        try:
            print("Attempting resuls...")
            results_obj = api.radar.results(wait = True) # wait = True is default behaviour, btw
            last_results = time.perf_counter()
            break
        except ConnectionError:
            print("Second Error")
            print("Connection to radar rejected... trying to get results again for {:f} more seconds...\n".format(
                GET_RESULTS_TIMEOUT - (time.perf_counter() - last_results)
            ))
            
    if (time.perf_counter() - last_results) >= GET_RESULTS_TIMEOUT:
        print("FATAL: Could not get results after trying for {:f} seconds.".format(GET_RESULTS_TIMEOUT))
        print("Returning none.")
        return None
    else:
        print("Got burst results for filename '{:s}'.".format(results_obj.filename))
        print(f"complete burst time: {time.perf_counter() - t0burst}")
        return results_obj

## DO LOOP
while True:

    print("Attempting burst #{:d}".format(count))
    do_burst_and_get_results(api)
    count = count + 1
    time.sleep(3)
   
    
