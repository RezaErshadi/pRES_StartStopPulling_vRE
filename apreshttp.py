# Python wrapper for HTTP API to Control the ApRES Radar
import datetime
import http
import json
import math
import os
import re
import requests
import time
import threading
from numpy import linspace

class API:
    """
    Entry-point class for Python code to access HTTP ApRES API

    The API class exposes the system, radar and data top-level elements
    of the ApRES HTTP API.  It also exposes methods for assigning the
    API key required to perform POST requests.

    POST requests are used to perform operations on the radar (such as
    bursts updating configuration, etc.) and as such require the API
    key to provided.
    """

    def __init__(self, root):
        """
        Initialise a new instance of the API specifying the root URL

        Creating a new instance of the API class requires the provision
        of a root URL.

        The default URL used by the ApRES is

            http://radar.localnet OR
            http://192.168.1.1

        The root URL is sanitised by API.assignRootURL - see this for
        further information.

        :param root: Root URL for the API to direct HTTP requests to
        :type root: str
        """

        # Set root URL
        self.assignRootURL(root)

        # Assign root objects
        self.system = System(self)
        self.radar = Radar(self)
        self.data = Data(self)

        # Assign default repeat requests/timeout
        self.timeout = 30 #: HTTP timeout in seconds
        self.wait = 1 #: wait time between consecutive HTTP requests

        #: Interval between requests for results in seconds
        self.resultsInterval = 2 

        # Whether to output debug commands
        self.debugEnable = False
        self.requestCount = 0;

        self.apiKey = "INVALID"

    def debug(self, *args, **kwargs):

        """
        Prints to the default system output buffer, if debug enabled

        Prints to the default system output buffer, as used by the
        system `print` function.

        :param args: unpack unnamed arguments into print
        :param kwargs: unpack named keywork arguments into print
        """

        if self.debugEnable:
            print(*args, **kwargs)

    def setKey(self, key):
        """
        Sets the API key to be used during POST requests

        :param key: string key to be used for API requests
        :type key: str
        :raises InvalidAPIKeyException: raised if the key parameter is not a string or is empty.
        """

        if isinstance(key, str) and len(key) > 0:
            self.apiKey = key
        else:
            raise InvalidAPIKeyException

    def assignRootURL(self, root):
        """Sanitises and assigns the value in root as the root API URL

        Checks whether the value in root is formatted correctly as the
        root URL for the API.

        Values for root can be preceeded with 'http://' or omit the
        'http://' protocol.  Trailing forward slashes will be trimmed
        from the root URL if present.

        Empty text at the start of the root URL is stripped, however no
        guarantee is given that the URL will connect when API functions
        are called.

        :param root: root URL for the api (i.e. http://radar.localnet)
        :type root: str
        :raises TypeError: raised if the root parameter is not a str
        """

        # Check whether the root is a string
        if not isinstance(root, str):
            raise TypeError("Root directory should be in string format, i.e. http://radar.localnet")

        # Check whether there is a leading "http://" or not
        http_idx = root.find("http://")
        if http_idx > 0:
            # There is some preceeding text to the "http://" - strip it
            root = root[http_idx:]
        elif http_idx == -1:
            # No "http://" provided - add it
            root = "http://" + root

        # Check for trailing slash
        if root[-1] == "/":
            # Remove trailing character
            root = root[0:-1]

        self.root = root

class APIChild:
    """
    APIChild objects provide wrappers for POST and GET requests

    APIChild objects wrap the :py:func:`requests.get` and
    :py:func:`requests.post` methods to build classes to support the
    implementation of calls of GET and POST API methods.
    """

    def __init__(self, api_obj):
        """
        Assign instance of the :py:class:`API` class

        APIChild should inherently be a child of an :py:class:`API` object
        hence the constructor requires an instance of :py:class:`API` to
        meet this conditions.

        :param api_obj: instance of :py:class:`API`
        :type api_obj: apreshttp.API
        """

        self.api = api_obj

    def postRequest(self, url, data_obj = None, files_obj = None, *args, **kwargs):
        """
        Perform a POST request to the URL, passing an API key and data

        The URL should be a valid ApRES HTTP API URL as described in
        :any:`api_routes`, without the `api/` or root prefix.  If the
        URL is not valid then a NotFoundException is raised.

        HTTP arguments can be passed using the `data_obj` parameter as
        a dictionary, containing named arguments (["name"]=value).
        Acceptable value types are `str`, `float`, `int`.

        If files are to be uploaded, then they should be provided to
        the `files_obj` parameter.  The HTTP variable name is the
        dictionary key and the value is two-element tuple describing
        the filename and its content
        (i.e. ["name"] = (filename, file_content)).

        :param url: URL to be requested from the API.  Should not include the API root (i.e. http://radar.localnet/api/)
        :param data_obj: Name-value pairs to be passed as HTTP args
        :param files_obj: Dictionary of name-value pairs, where the name represents the HTTP variable name and the value is a two-element tuple of (filename, file_content)

        :type data_obj: dict
        :type url: str
        :type files_obj: dict

        """

        # Form complete URL
        completeUrl = self.formCompleteURL(url);

        # If the data object was empty, then create one and assign the local
        # API key for use in the post request
        if data_obj == None:
            data_obj = dict()
            data_obj['apikey'] = self.api.apiKey
        # Otherwise, check whether an API key was provided and if not add one
        # using the local API key value
        elif "apikey" not in data_obj.keys():
            data_obj["apikey"] = self.api.apiKey

        self.api.requestCount = self.api.requestCount + 1;

        if self.api.debugEnable:
            data_obj["requestid"] = self.api.requestCount

        self.api.debug("POST request to [{url:s}] with data:".format(url=completeUrl))
        self.api.debug(data_obj)

        # Create request object
        if files_obj == None:
            response = requests.post(
                completeUrl,
                data = data_obj,
                timeout = self.api.timeout,
                *args,
                **kwargs
            )
        else:
        # If files is set then add that
            response = requests.post(
                completeUrl,
                data = data_obj,
                files = files_obj,
                timeout = self.api.timeout,
                *args,
                **kwargs
            )

        self.api.debug("Validating...")
        # Check for errorCode and errorMessage keys
        self.validateResponse(response)

        self.api.debug("Passed.")

        # Return the response for the function to do something with
        return response

    def getRequest(self, url, data_obj = None, *args, **kwargs):
        """
        Perform a GET request to the URL, passing an API key and data

        The URL should be a valid ApRES HTTP API URL as described in
        :any:`api_routes`, without the `api/` or root prefix.  If the
        URL is not valid then a NotFoundException is raised.

        HTTP arguments can be passed using the `data_obj` parameter as
        a dictionary, containing named arguments (["name"]=value).
        Acceptable value types are `str`, `float`, `int`.  This is the
        same as requesting a URL with a query string appended with

            ?name1=value1&name2=value2

        :param url: URL to be requested from the API which is append to the root in the form {root}/api/{url}
        :param data_obj: Name-value pairs to be passed as HTTP args

        :type data_obj: dict
        :type url: str

        """

        # Form complete URL
        completeUrl = self.formCompleteURL(url);

        # If data object is empty, convert into an empty dict
        if data_obj == None:
            data_obj = dict()

        self.api.requestCount += 1;

        if self.api.debugEnable:
            data_obj["requestid"] = self.api.requestCount

        self.api.debug("GET request to [{url:s}] with data:".format(url=completeUrl))
        self.api.debug(data_obj)

        # Create request object
        response = requests.get(
            completeUrl,
            params = data_obj,
            timeout = self.api.timeout
        )

        self.api.debug(response.url)

        self.api.debug("Validating...")
        self.validateResponse(response)
        self.api.debug("Passed.")

        return response

    def validateResponse(self, response):
        """
        Takes a `requests.response` object and handles common errors

        If the response is JSON and contains the errorCode and
        errorMessage keys, then parse these and raise the appropriate
        exceptions.

        :param response: `response` object returned from :py:meth:`getRequest` or :py:meth:`postRequest`
        :type response: request.response object

        :raises InvalidAPIKeyException: API key is invalid
        :raises NotFoundException: Requested URL was not found/invalid
        :raises InternalRadarErrorException: Problem with the radar described in the error text.
        :raises RadarBusyException: Radar could not perform requested task because it is busy.
        """

        # Check  we have a JSON object
        if "Content-Type" in response.headers.keys() and response.headers["Content-Type"] == "application/json":
            # Default checking GET and POST requests
            response_json = response.json()
            if "errorCode" in response_json or "errorMessage" in response_json:
                if response_json['errorCode'] == 401:
                    raise InvalidAPIKeyException(response_json['errorMessage'])
                elif response_json['errorCode'] == 404:
                    raise NotFoundException(response_json['errorMessage'])
                elif response_json['errorCode'] == 500:
                    raise InternalRadarErrorException(response_json['errorMessage'])
                elif response_json['errorCode'] == 503:
                    raise RadarBusyException(response_json['errorMessage'])


    def formCompleteURL(self, url_part):
        """
        Returns the full URL for the HTTP request

        Combines the API root, /api/ component and final API route into
        a complete URL, i.e.

            system/reset => http://radar.localnet/api/system/reset

        :param url_part: API route, i.e. system/reset
        :type url_part: str
        :return: str
        """
        return self.api.root + "/api/" + url_part

################################################################################
# SYSTEM
################################################################################

class System(APIChild):
    """
    System wraps system-related API methods

    System provides a wrapper for the system-related functions exposed
    by the ApRES HTTP API.  This includes

    * system/reset
    * system/housekeeping/config
    * system/housekeeping/status
    """

    def __init__(self, api_obj):
        # Call super constructor
        super().__init__(api_obj)

        # Create housekeeping sub object
        self.housekeeping = self.Housekeeping(api_obj)

    # System reset
    def reset(self):
        """
        Reset the ApRES

        Requires a valid API key to be assigned to the API object to
        perform the reset operation.

        No guarantee of a reset can be made, but upon successful
        reception of the request a
        :py:class:`apreshttp.System.ResetMessage` object is returned.

        :raises BadResponseException: If the response is malformed or unexpected.
        """

        # Get response
        response = self.postRequest("system/reset")
        # Check the status code is 202 (i.e. don't wait...)
        if response.status_code != 202:
            raise SystemResetException
        else:
            # Strip message and time from response
            response_json = response.json()

            if not "message" in response_json:
                raise BadResponseException("No message key in response.")
            msg = response_json["message"]

            if not "time" in response_json:
                raise BadResponseException("No time key in response.")
            time = datetime.datetime.strptime(
                response_json["time"],
                "%Y-%m-%d %H:%M:%S"
            )

        return self.ResetMessage(msg, time)

    class ResetMessage:
        """
        Utility class to contain message and time from reset action
        """
        def __init__(self, msg, time):
            #: Reset message, including timestamp.
            self.message = (msg)
            #: Datetime object representing time of reset
            self.time = (time)

    class Housekeeping(APIChild):
        """
        Housekeeping encapsulates system config and status methods

        The Housekeeping object should be a child of the System object
        and exposes methods to download the configuration file, upload
        and new configuration file or retrieve the radar system status,
        packaged in a :py:class:apreshttp.System.Housekeeping` object.

        """

        def __init__(self, api_obj):
            self.api = api_obj
            self.config = self.Config(api_obj)

        def status(self):
            """
            Request an update on the ApRES battery, tiem, GPS, etc.

            Perform a GET request to system/housekeeping/status and
            wrap the response as a
            :py:class:`apreshttp.System.Housekeeping.Status` object.

            :raises BadResponseException: if the response is malformed or missing information.
            :return: If valid a :py:class:`apreshttp.System.Housekeeping.Status` object is returned

            """
            # Get response
            response = self.getRequest("system/housekeeping/status")
            # Check that the status code is 200
            if response.status_code != 200:
                raise SystemHousekeepingException(
                "Unexpected status code: {stat:d}".format(stat=response.status_code))
            else:
                # Convert response body to JSON
                response_json = response.json()

                self.api.debug(response.text)

                # Check response has valid components
                if not "batteryVoltage" in response_json:
                    raise BadResponseException("No batteryVoltage key in response.")
                if not "timeGPS" in response_json:
                    raise BadResponseException("No timeGPS key in response.")
                if not "timeVAB" in response_json:
                    raise BadResponseException("No timeVAB key in response.")
                if not "latitude" in response_json:
                    raise BadResponseException("No latitude key in response.")
                if not "longitude" in response_json:
                    raise BadResponseException("No longitude key in response.")

                return self.Status(
                    response_json["batteryVoltage"],
                    response_json["timeGPS"],
                    response_json["timeVAB"],
                    response_json["latitude"],
                    response_json["longitude"],
                )

        class Status:
            """
            Utility class for representing the ApRES system status.
            """
            def __init__(self, batVoltage, timeGPS, timeVAB, lat, long):

                # Assign batteryVoltage
                if isinstance(batVoltage, float) or isinstance(batVoltage, int):
                    #: Reported ApRES battery voltage (may be 0 if not enabled or connected)
                    self.batteryVoltage = batVoltage
                else:
                    raise BadResponseException("batteryVoltage should be a numeric type.")

                # Assign latitude
                if isinstance(lat, float) or isinstance(lat, int):
                    #: Reported latitude from GPS
                    self.latitude = lat
                else:
                    raise BadResponseException("latitude should be a numeric type.")

                # Assign longitude
                if isinstance(long, float) or isinstance(long, int):
                    #: Reported longitude from GPS
                    self.longitude = long
                else:
                    raise BadResponseException("longitude should be a numeric type.")

                #: GPS timestamp as a :py:class:`datetime.datetime` object, if available.
                self.timeGPS = None
                # Assign GPS time
                if isinstance(timeGPS, str):
                    if len(timeGPS) > 0:
                        self.timeGPS = datetime.datetime.strptime(timeGPS, "%Y-%m-%d %H:%M:%S")
                else:
                    raise BadResponseException("timeGPS should be a string containing YYYY-mm-DD HH-MM-SS timestamp.")


                #: VAB timestamp as a :py:class:`datetime.datetime` object
                self.timeVAB = None
                # Assign VAB time
                if isinstance(timeVAB, str):
                    if len(timeVAB) > 0:
                        self.timeVAB = datetime.datetime.strptime(timeVAB, "%Y-%m-%d %H:%M:%S")
                else:
                    raise BadResponseException("timeVAB should be a string containing YYYY-mm-DD HH-MM-SS timestamp.")

            def __repr__(self):
                str = "Status <0x{:x}>\n\n".format(id(self))
                str += "\tVAB Time       : {}\n".format(self.timeVAB)
                str += "\tGPS Time       : {}\n".format(self.timeGPS)
                str += "\tLatitude       : {}\n".format(self.latitude)
                str += "\tLongitude      : {}\n".format(self.longitude)
                str += "\tBattery Voltage: {}\n".format(self.batteryVoltage)
                return str
            

        class Config(APIChild):
            """
            Config class facilitates up/download of the system config

            The Config class allows for the remote config.ini file to
            be downloaded onto the local filesystem, or a replacement
            config file to be uploaded.

            NOTE: The ApRES must be restarted before a newly uploaded
            config.ini file will take effect.

            """

            def download(self, fileLocation = None, overwrite = False):
                """
                Download ApRES config.ini to the local filesystem

                If a directory is specified for the file location then
                the function will look for an existing `config.ini`
                file.  If an existing `config.ini` file exists in that
                directory then it will be overwritten if the overwrite
                option is enabled.

                If a file is specified for the file location then if it
                does not exist, it will be created.  If it does exist
                and overwrite is enabled it will be overwritten,
                otherwise a FilExistsError is raised.

                :param fileLocation: file system path to where the config.ini file should be downloaded
                :param overwrite: if the file exists, then overwrite

                :type fileLocation: str
                :type overwrite: boolean

                :raises FileExistsError: Raised if the file exists and overwrite is not enabled.

                """
                # If fileLocation is None then default to "config.ini"
                if fileLocation == None:
                    fileLocation = "config.ini"

                # Get response
                response = self.getRequest("system/housekeeping/config")
                # Check whether the file location is valid and exists
                if os.path.isdir(fileLocation):
                    fileLocation = os.path.join(fileLocation, "config.ini")

                if os.path.isfile(fileLocation):
                    if not overwrite:
                        raise FileExistsError

                with open(fileLocation, 'w') as fh:
                    print(response.text, file=fh)

                return True

            def upload(self, fileLocation = None):
                """
                Upload new ApRES config.ini file from the filesystem

                If a directory is specified for the file location then
                the function will look for a config.ini file within
                that directory.  Otherwise, if a file is specified
                then that is uploaded.

                If the file does not exist (or a file named config.ini
                within the directory) then a FileNotFoundError is
                raised.

                The files are renamed to config.ini by the ApRES radar
                when they are uploaded.

                :param fileLocation: file system path to where the config.ini file should be uploaded from.

                :type fileLocation: str

                :raises FileNotFoundError: Raised if the file at fileLocation, or a "config.ini" file within that directory, is not found.
                :raises NoFileUploadedError: Raised if the request was malformed and no file was uploaded.
                :raises BadResponseException: The response was malformed or the response was not a HTTP 201 status code.

                """

                if os.path.isdir(fileLocation):
                    fileLocation = os.path.join(fileLocation, "config.ini")

                if not os.path.isfile(fileLocation):
                    raise FileNotFoundError

                # Get response
                with open(fileLocation) as fh:
                    content = fh.read()
                    fileDict = dict()
                    fileDict["file"] = ("config.ini", content)
                    response = self.postRequest(
                        "system/housekeeping/config",
                        data_obj = None,
                        files_obj = fileDict
                    )

                    if response.status_code == 400:
                        raise NoFileUploadedError
                    elif response.status_code != 201:
                        raise BadResponseException

################################################################################
# RADAR
################################################################################

class Radar(APIChild):
    """
    Wrapper class for radar operation and configuration

    The Radar class exposes methods in the API to update the chirp
    settings, perform trial bursts and collect results, and perform
    a radar measurement (burst).
    """

    VALID_BURST_STATUS_CODE = 303;

    def __init__(self, api_obj):
        super().__init__(api_obj);
        # Create child of type Config
        #: Instance of a Radar.Config object which gets and sets the radar chirp config.
        self.config = self.Config(api_obj)

    def trialBurst(self, callback = None, updateCallback = None, wait = True):
        """
        Perform a trial burst using the current configuration

        Attempts to start an asynchronous trial radar burst, using the
        current configuration. Also retrieves configuration from the
        API.

        If the burst starts successfully then the response status code
        should be 303 and redirect to the "results" API route.

        If the status code is 403 then something is preventing the
        radar from starting the burst.

        To parse the results from the trial burst, the below gives some
        example code:

        .. code-block:: python

            # Create API instance
            api = apreshttp.API("http://radar.localnet")
            api.API_KEY = [...]

            # Define callback function
            def trialResultsCallback(response):
                try:
                    response_json = response.json()
                    # DO SOMETHING WITH RESULTS
                    ...
                except:
                    print("Couldn't read results.")

            # Perform trial burst
            api.radar.trialBurst(trialResultsCallback) # will hang until results are returned.

        :param callback: If provided, callback is executed when results are available.  The callback function should take a single argument of type requests.response
        :type param: callable
        :param updateCallback: callback function executed on each results request (to provide progress updates)
        :type updateCallback: callable
        :param wait: If callback is provided, should the function halt execution or wait in a seperate thread
        :type wait: boolean
        :raises NoChirpStartedException: Raised if the API returns a 403 indicating the radar cannot start the burst and no data is available, i.e. the radar state is idle.
        :raises RadarBusyException:  Raised if the burst could not be started because the radar is already performing a burst.
        """

        if callback != None and not callable(callback):
            raise TypeError("Argument 'callback' should be callable.")

        # Update config locally
        self.config.get()

        try:
        # Make a POST request to trial burst
            response = self.postRequest("radar/trial-burst", allow_redirects=False)
        except (requests.exceptions.ConnectionError) as e:
                raise RadarBusyException

        # Check whether the burst started (any other status codes )
        self.api.debug("Received {rsp:d} response".format(rsp=response.status_code))

        if response.status_code != self.VALID_BURST_STATUS_CODE:

            # Get response
            response_json = response.json()
            if "errorMessage" in response_json:
                raise RadarBusyException(response_json["errorMessage"])
            else:
                raise RadarBusyException

        if callback != None or updateCallback != None:
            return self.results(callback, updateCallback, wait)

    def results(self, callback = None, updateCallback = None, wait = True):        
        """
        Wait for results to be returned by the radar

        Calls the function `callback` when the api/radar/results page
        indicates that the chirp has finished.   If callback is `None`
        then this works as a blocking function until the radar results
        are ready.

        If the `ResultsTimeoutException` is raised, it is a good
        indication that the radar should be reset.

        :param callback: callback function which accepts one argument of type API.Radar.Results
        :type callback: callable

        :param updateCallback: callback function executed on each results request (to provide progress updates)
        :type updateCallback: callable

        :param wait: If False, the request for results takes place in a new thread.
        :type wait: boolean

        :return: If wait = False, returns the thread instance executing the results code.  Otherwise, returns a results object if the results are obtained.
        :rtype: :py:class:`threading.Thread`     

        :raises NoChirpStartedException: If the radar state is idle, no data is returned.
        :raises ResultsTimeoutException: Raised if the timeout period is exceeded and no results are returned within this period.
        """

        if callback != None and not callable(callback):
            raise TypeError("Argument 'callback' should be callable.")

        # If waiting, run in the same thread
        if wait:
            return self.__getResults(callback, updateCallback) 
        # Otherwise create a new thread and start it
        else:
            self.api.debug(self.__getResults)
            resultsThread = threading.Thread(target=self.__getResults, args=(callback, updateCallback))
            resultsThread.start()
            return resultsThread


    def __getResults(self, callback, updateCallback = None):
        """
        Nothing to see here...
        """

        # Update config
        self.config.get()

        # Define initiation time
        init_time = datetime.datetime.now()

        nTx = sum(self.config.txAntenna)
        nRx = sum(self.config.rxAntenna)

        # Calculate timeout (allow 2 seconds for each chirp)
        timeoutSeconds = (nTx * nRx) * (self.config.nSubBursts + self.config.nAverages) * \
                         self.config.nAttenuators * 2 + self.api.timeout

        self.api.debug("Getting results [Timeout = {timeout:f}".format(
            timeout=timeoutSeconds
        ))

        timeout = datetime.timedelta(seconds = timeoutSeconds)

        # Loop until we timeout
        while (datetime.datetime.now() - init_time < timeout):

            # Make GET request to results
            response = self.getRequest("radar/results")
            response_json = response.json()

            # Check if a chirp was requested
            if response_json["status"] == "idle":
                # No chirp was started so break
                raise NoChirpStartedException

            elif response_json["status"] == "finished":
                if callback != None:
                    callback(self.Results(response))
                return self.Results(response)

            if updateCallback != None:
                updateCallback(response)

            # wait until next timeout
            time.sleep(self.api.resultsInterval)

        raise ResultsTimeoutException

    def burst(self, filename = None, userData = None, callback = None, updateCallback = None, wait = True):
        """
        Perform a measurement radar burst using the current config

        Attempts to start an asynchronous radar burst, using the
        current configuration.  Also retrieves configuration from the
        API.

        If the burst starts successfully then the response status code
        should be 303 and redirect to the "results" API route.

        If the status code is 403 then something is preventing the
        radar from starting the burst.

        :param filename: filename to be used when saving the burst to an SD card.
        :type filename: str

        :param callback: callback function which accepts one argument of type API.Radar.Results
        :type callback: callable

        :param updateCallback: callback function executed on each results request (to provide progress updates)
        :type updateCallback: callable

        :param wait: If False, the request for results takes place in a new thread.
        :type wait: boolean

        :raises NoChirpStartedException: Raised if the API returns a 403 indicating the radar cannot start the burst and no data is available, i.e. the radar state is idle.
        :raises RadarBusyException:  Raised if the burst could not be started because the radar is already performing a burst.
        """

        # Update config locally
        self.config.get()

        if filename != None and not isinstance(filename, str):
            raise ValueError("filename parameter should be of type 'str'.")

        data_obj = {
            "filename" : filename
        }

        if isinstance(userData, str):
            data_obj["userData"] = userData

        # Make a POST request to trial burst
        response = self.postRequest("radar/burst", data_obj, allow_redirects=False)

        # Check whether the burst started (any other status codes )
        if response.status_code != self.VALID_BURST_STATUS_CODE:

            # Get response
            response_json = response.json()
            if "errorMessage" in response_json:
                raise RadarBusyException(response_json["errorMessage"])
            else:
                raise RadarBusyException

        # If callback is available then use that
        if callback != None:
            return self.results(callback, wait)

    class Results:
        """
        Container class for burst and trial results

        The `type` parameter can be used to determine whether the
        results arise from trial burst or a full burst, and the
        parameters will depend on this.
        """
        def __init__(self, response):

            response_json = response.json()

            if not "type" in response_json:
                raise BadResponseException("No key 'type' found in results.")

            #: indicates whether the results are a trial or full burst
            self.type = response_json["type"]

            if not "nAttenuators" in response_json:
                raise BadResponseException("No key 'nAttenuators' found in results.")

            self.nAttenuators = response_json["nAttenuators"]

            if not "startFrequency" in response_json:
                raise BadResponseException("No key 'startFrequency' found in results.")
                
            self.startFrequency = response_json["startFrequency"]
            
            if not "stopFrequency" in response_json:
                raise BadResponseException("No key 'stopFrequency' found in results.")
            
            self.stopFrequency = response_json["stopFrequency"]

            if not "period" in response_json:
                raise BadResponseException("No key 'period' found in results.")

            self.period = response_json["period"]

            self.bandwidth = self.stopFrequency - self.startFrequency

            if self.type == "trial":

                self.__loadTrialParameters(response_json)

            elif self.type == "burst":

                self.__loadBurstParameters(response_json)

            else:
                raise BadResponseException("Invalid type '{type:s}'".format(type=self.type))

        def __loadTrialParameters(self, response_json):

            if not "nAverages" in response_json:
                raise BadResponseException("No key 'nAverages' found in results.")

            #: Number of attenuator settings in the response
            self.nAttenuators = int(response_json["nAttenuators"])
            #: Number of averages used to compute the response
            self.nAverages = int(response_json["nAverages"])

            #: histogram counts for each attenuator setting (list of lists)
            self.histogram = [];
            self.histogramVoltage = linspace(0, 2.5, 50)
            #: chirp data for each attenuator setting (list of lists)
            self.chirp = [];

            # Iterate over number of attenuators and assign chirps/histogram
            for hist in response_json["histogram"]:
                self.histogram.append(hist)

            for chirp in response_json["chirp"]:
                self.chirp.append([v / 65536 * 2.5 for v in chirp])

        def __loadBurstParameters(self, response_json):

            if not "filename" in response_json:
                raise BadResponseException("No filename in response.")

            self.filename = response_json["filename"]

    class Config(APIChild):
        """
        Retrieve and modify radar burst configuration

        The Radar.Config class can be updated from the API using the :py:meth:`get` method.

        If it is desired to change values, such as individual
        attenuator settings or the number of sub-bursts, then the
        :py:meth:`set` method should be used.

        NOTE: when instance attributes, such as :py:attr:`nAttenuators`
        are accessed, these are not automatically updated from the API
        and default to their last values, hence care should be taken
        to call :py:meth:`get` when it is desired to have the most
        recent configuration values.

        By default, instance variables are initialised to `None` until
        a :py:meth:`get` request is made.
        """

        def __init__(self, api_obj):
            super().__init__(api_obj);
            #: Number of attenuator settings (int)
            self.nAttenuators = None
            #: Number of sub-bursts per burst (int)
            self.nSubBursts = None
            #: Number of averages for a trial burst (int)
            self.nAverages = None
            #: RF attenuator settings (list of float)
            self.afGain = []
            #: AF gain settings (list of float)
            self.rfAttn = []

        def __repr__(self):
            str = "Radar.Config <0x{:x}>\n\n".format(id(self))
            str += "\tnAttenuators : {}\n".format(self.nAttenuators)
            str += "\tnSubBursts   : {}\n".format(self.nSubBursts)
            str += "\tnAverages    : {}\n".format(self.nAverages)
            str += "\tafGain       : {}\n".format(self.afGain)
            str += "\trfAttn       : {}\n".format(self.rfAttn)
            str += "\tuserData     : {}\n".format(self.userData)
            return str

        def get(self):
            """
            Retrieve the latest radar burst configuration

            :return: Returns `self`

            :raises BadResponseException: Raised in the event of an unexpected error code or missing JSON keys.
            """

            # Get response
            if self.api.debugEnable:
                response = self.getRequest("radar/config", data={"debug":1})
            else:
                response = self.getRequest("radar/config")
            #
            if response.status_code != 200:
                raise BadResponseException(
                "Unexpected status code: {stat:d}".format(stat=response.status_code))
            else:
                self.readResponse(response)
                return self

        def readResponse(self, response):
            """
            Read values from a response to radar/config into Config object

            :raises BadResponseException: Raised if there are missing fields from the radar configuration JSON response.
            """
            # Convert response body to JSON
            response_json = response.json()

            self.api.debug(response.text)

            # Check response has valid components
            if not "nSubBursts" in response_json:
                raise BadResponseException("No nSubBursts key in response.")
            if not "nAttenuators" in response_json:
                raise BadResponseException("No nAttenuators key in response.")
            if not "nAverages" in response_json:
                raise BadResponseException("No nAverages key in response.")
            if not "rfAttn" in response_json:
                raise BadResponseException("No rfAttn key in response.")
            if not "afGain" in response_json:
                raise BadResponseException("No rfAttn key in response.")
            if not "userData" in response_json:
                raise BadResponseException("No userData key in response.")
            if not "txAntenna" in response_json:
                raise BadResponseException("No txAntenna key in response.")
            if not "rxAntenna" in response_json:
                raise BadResponseException("No rxAntenna key in response.")

            self.nAttenuators = response_json["nAttenuators"]
            self.nSubBursts = response_json["nSubBursts"]
            self.nAverages = response_json["nAverages"]
            self.userData = response_json["userData"]
            # Create empty AF gain and RF attenuation arrays

            self.rfAttn = response_json["rfAttn"]
            self.afGain = response_json["afGain"]

            self.txAntenna = tuple(response_json["txAntenna"])
            self.rxAntenna = tuple(response_json["rxAntenna"])

            self.api.debug("NAtts: {}\nN(rfAttn): {}\nN(afGain): {}\n".format(self.nAttenuators, len(self.rfAttn), len(self.afGain)))

            # Sanity check we have the correct number of attenuators
            if len(self.rfAttn) == self.nAttenuators \
            and len(self.afGain) == self.nAttenuators:
                return self
            else:
                raise BadResponseException("Number of attenuator settings did not match nAttenuators in response.")

        def set(
            self, nAtts=None, nAverages = None, nBursts=None, rfAttnSet=None, afGainSet=None,
            txAnt=None, rxAnt=None, userData = None
        ):
            """
            Updates the radar burst configuration with the given parameters

            :param nAtts: Set the number of attenuator settings to be used (1-4)
            :type nAtts: int or `None`
            :param nBursts: Set the number of chirps to be averaged for a trial burst, or repeated for a full burst.
            :type nBursts: int or `None`
            :param rfAttnSet: Set the values of the ApRES RF attenuator.  If using a dictionary, keys should be "rfAttn1", "rfAttn2", etc. and may be excluded if no update is desired.
            :type rfAttnSet: int, list, dict or `None`
            :param afGainSet: Set the values of the ApRES AF gain.  If using a dictionary, keys should be "afGain1", "afGain2", etc. and may be exlcuded if no update is desired.
            :type afGainSet: int, list, dict or `None`
            :param txAnt: If using a MIMO board, set the active transmit antennas
            :type txAnt: int or list
            :param userData: 32-char string representing the current radar task (printed to bursts)
            :type userData: str

            :raises BadResponseException: If an unexpected status code was returned
            :raises DidNotUpdateException: If the config settings were not updated

            **NOTE**: Calling :py:meth:`set` will incur a call to
            :py:meth:`get` to retrieve the latest configuration.

            To update the number of attenuators

            .. code-block:: python

                Config.set(nAtts = 3)

            To update the number of sub-bursts

            .. code-block:: python

                Config.set(nBursts = 10)

            To update RF attenuator or AF gain values (i.e. replace
            rfAttnSet with afGainSett)

            .. code-block:: python

                # Update rfAttn1 to 16.5 dB
                Config.set(rfAttnSet = 16.5)
                # Update rfAttn1, rfAttn2 and rfAttn4 using list
                Config.set(rfAttnSet = [0, 10, None, 23.5])
                # Update using rfAttn2 and rfAttn3 using dict
                rfSettings = {"rfAttn2" : 12.5, "rfAttn3" : 6.0}
                Config.set(rfAttnSet = rfSettings)

            **WARNING**: If nAttenuators has been set in the same or a
            previous call to :py:meth:`set` and an RF attenuator or AF
            gain value with an index greater than nAtts has been set,
            then an error is thrown, i.e.

            .. code-block:: python

                # Set nAtts to 2, but try setting rfAttn3
                Config.set(nAtts = 2, rfAttnSet = [0, 10, 20])
                # Exception occurs!
                ...
                Config.set(afGainSet = [-14, -14, -14])
                # Exception occurs (trying to change nAtts to 3)

            Similarly, trying to assign a single attenuator value when
            nAttenuators is greater than 1 will cause an error

            .. code-block:: python

                # Set nAtts to 2
                Config.set(nAtts = 2)
                # Try to assign a single attenuator value
                Config.set(afGainSet = -4)
                # Exception occurs

            If using a MIMO board, providing txAnt or rxAnt with an eight
            element tuple allows the user to choose which antennas are
            enabled, i.e.

            .. code-block:: python

                # Use the 1st, 4th and 8th antennas to transmit
                Config.set(txAnt = (1,0,0,1,0,0,0,1))
                # Use the 2nd and 7th antennas to receive
                Config.set(rxAnt = (0,1,0,0,0,0,1,0))

            """

            # Update parameters
            self.get()

            # Create an empty dictionary to hold data for post request
            data_obj = dict()

            if nAtts != None:
                # Check whether nAtts is a number
                if isinstance(nAtts, int) or isinstance(nAtts, float):
                    data_obj["nAttenuators"] = nAtts
                else:
                    raise ValueError("nAtts should be numeric")

            if nBursts != None:
                # Check whether nBursts is a number
                if isinstance(nBursts, int) or isinstance(nBursts, float):
                    data_obj["nSubBursts"] = nBursts
                else:
                    raise ValueError("nBursts should be numeric")

            if nAverages != None:
                # Check whether nBursts is a number
                if isinstance(nAverages, int) or isinstance(nAverages, float):
                    data_obj["nAverages"] = nAverages
                else:
                    raise ValueError("nAverages should be numeric")

            if txAnt != None:
                # Check whether it is a tuple or array
                if isinstance(txAnt, tuple) and len(txAnt) == 8:
                    count = 0
                    for v in txAnt:
                        if v != 0 and v != 1:
                            raise ValueError("Value at #{} in txAnt should be 0 or 1 only".format(count))
                        count = count + 1
                    if count > 0:
                        txAntStr = [str(x) for x in txAnt]
                        data_obj["txAntenna"] = ",".join(txAntStr)
                    else:
                        raise ValueError("Must have at least one rxAntenna enabled.")
                else:
                    raise ValueError("txAnt should be an 8-element tuple.")

            if rxAnt != None:
                # Check whether it is a tuple or array
                if isinstance(rxAnt, tuple) and len(rxAnt) == 8:
                    count = 0
                    for v in rxAnt:
                        if v != 0 and v != 1:
                            raise ValueError("Value at #{} in rxAnt should be 0 or 1 only".format(count))
                        count = count + 1

                    if count > 0:
                        rxAntStr = [str(x) for x in rxAnt]
                        data_obj["rxAntenna"] = ",".join(rxAntStr)
                    else:
                        raise ValueError("Must have at least one rxAntenna enabled.")
                else:
                    raise ValueError("rxAnt should be an 8-element tuple.")

            valid_rf = None
            if rfAttnSet != None:
                valid_rf = self.parseRFAttnAFGain("rfAttn", rfAttnSet, nAtts or self.nAttenuators)
                if len(valid_rf) > 0:
                    # Merge valid with data_obj
                    data_obj = {**data_obj, **valid_rf}

            valid_af = None
            if afGainSet != None:
                valid_af = self.parseRFAttnAFGain("afGain", afGainSet, nAtts or self.nAttenuators)
                if len(valid_af) > 0:
                    # Merge valid with data_obj
                    data_obj = {**data_obj, **valid_af}

            if userData != None:
                if isinstance(userData, str):
                    data_obj["userData"] = userData
                else:
                    ValueError("userData should be of type str")

            # Now deal with the request
            response = self.postRequest("radar/config", data_obj)

            # Need to check status codes in response
            if response.status_code == 400:
                response_json = response.json()
                raise BadResponseException(response_json['errorMessage'])

            elif response.status_code == 200:
                # Update object from response
                self.readResponse(response)
                # Check whether new values match updated values
                if nAtts != None and nAtts != self.nAttenuators:
                    raise DidNotUpdateException("nAttenuators did not update.")

                if nBursts != None and nBursts != self.nSubBursts:
                    raise DidNotUpdateException("nSubBursts did not update.")

                if valid_rf != None:
                    # Iterate over valid_rf
                    for key, value in valid_rf.items():
                        # Take last character as index
                        idx = int(key[-1]) - 1
                        # Check values match
                        self.api.debug("RF Assigned: {srv:f} vs. Retrieved: {mem:f}".format(srv = value, mem = self.rfAttn[idx]))
                        if value != self.rfAttn[idx]:
                            raise DidNotUpdateException(key + " did not update.")

                if valid_af != None:
                    # Iterate over valid_af
                    for key, value in valid_af.items():
                        idx = int(key[-1]) - 1
                        # Check values match
                        self.api.debug("AF Assigned: {srv:f} vs. Retrieved: {mem:f}".format(srv = value, mem = self.afGain[idx]))
                        if value != self.afGain[idx]:
                            raise DidNotUpdateException(key + " did not update.")

                # Return config object
                return self

        def parseRFAttnAFGain(self, type, arg, nAtts):
            """
            Validate RF attenuation and AF gain parameters to :py:meth:`get`

            :raises ValueError: Raised if nAtts is greater than 1 and a single AF or RF value is provided.
            :raises KeyError: Raised if the key in `arg` does not match rfAttn[1-4] or afGain[1-4]
            """

            # Check type is valid
            if not (type == "rfAttn" or type == "afGain"):
                raise Exception ("Invalid type, should be 'rfAttn' or " + "'afGain' case sensitive.")

            resp = dict()

            if isinstance(arg, int) or isinstance(arg, float):
                # Value is singular - current nAtts should be 1 and
                # updating value empty, or updating value should be 1
                if (nAtts != None and nAtts == 1) or \
                   (nAtts == None and self.nAtts == 1):
                   # Assign value to rfAttn1 or afGain1
                   resp[type + "1"] = arg
                else:
                    raise ValueError("nAtts or current nAttenuators > 1, cannot add a sigular " + type + " parameter")

            elif isinstance(arg, list):
                # If the argument is a list, it should have the same
                # number of elements as nAtts or nAttenuators
                if ((nAtts != None and len(arg) == nAtts) or (nAtts == None and len(arg) == self.nAtts)):
                   # len(arg) must be valid, therefore iterate
                   for i in range(len(arg)):
                       # Check that the value is numeric
                       if isinstance(arg[i], int) or isinstance(arg[i], float):
                           resp[type + str(i + 1)] = arg[i]
                           # otherwise ignore it and don't add that value
                           # i.e. we can have [0, None, 10] and only assign
                           #  rfAttn1 and rfAttn3 leaving rfAttn2 as is
                else:
                   raise ValueError("If " + type + "Set is a list, it should have the same number of elements as the number of attenuators")

            elif isinstance(arg, dict):
                # If the argument is a dictionary, then iterate over
                # the keys and check they are valid
                #
                # First of all, get the correct number of attenuators
                # and store in nAtts
                if nAtts == None:
                    nAtts = self.nAttenuators

                # Create regexp for key validation
                # (this only works if nAtts <= 9, currently 4)
                regexp = type + "([1-" + str(nAtts) + "])"

                for key, val in arg.items():
                    # Find type in the key at index 0
                    match = re.search(regexp, key)
                     # check that it occurs at the start
                    if match != None and match.span()[0] == 0:
                        resp[key] = val
                    else:
                        raise KeyError("Invalid key '" + key + "' in "
                            + type + " argument.")

            return resp


################################################################################
# DATA
################################################################################

class Data(APIChild):

    def __init__(self, api_obj):
        super().__init__(api_obj);

    def dir(self, path="", startIndex=0, listSize=16):
        """
        Get a directory listing from the path specified

        Returns a :py:class:`apreshttp.Data.DirectoryListing`
        object representing the files and directories in the
        specified path.

        If there are more than `listSize=16` (default) files
        in the directory, the returned list will be truncated
        and the total number of objects in the directory stored
        in `numObjectsInDir`.

        To request the next 'page' of objects in the directory.
        make another call to `dir` with `startIndex=N*listSize`,
        where N is the desired 'page number'.

        :raises ValueError: if path is not a string object
        :raises NotFoundException: if the path is not found on the ApRES file system
        :raises NotADirectoryError: if the path does not point to a directory
        :raises InternalRadarErrorException: if an internal radar error has occured.

        :return: object containing descriptions of files and subdirectories. 
        :rtype: :py:class:`apreshttp.Data.DirectoryListing`
        """

        if not isinstance(path, str):
            raise ValueError("path should be of type 'str'")

        data_obj = {
            "path" : path,
            "index" : startIndex,
            "list" : listSize
        }

        response = self.getRequest("data", data_obj)

        if response.status_code == 404:
            
            raise NotFoundException(path)

        elif response.status_code == 403:

            raise NotADirectoryError(path)

        elif response.status_code != 200:

            raise InternalRadarErrorException(
                "Radar returned unexpected status code " + 
                str(response.status_code)#
            )

        # Now we can parse the response
        response_json = response.json()

        return self.DirectoryListing(response_json)
        
    def download(self, path, dst_path=None):
        """
        Download a file to the working dir or the destination path

        If the file at `path` exists on the ApRES filesystem, 
        it will be downloaded to either the current working directory
        (if `dst_path` is `None`).

        Alternatively, providing a `dst_path` value that refers to
        a directory will download the file to that directory, using 
        its name on the ApRES filesystem.

        Providing a `dst_path` value that refers to a file will
        download the file to that path.

        **NOTE**: If the destination filepath already exists, a
        `FileExistsException` will be thrown.

        :param path: path on the ApRES filesystem of the file to download
        :type path: str
        :param dst_path: destination path to download file to
        :type dst_path: str

        :raises FileExistsException: if the file already exists at `dst_path`
        """
        
        filename = os.path.basename(path)

        if dst_path != None:
            if os.path.isdir(dst_path):
                filename = os.path.join(dst_path, filename)
            else:
                filename = dst_path

        if os.path.exists(filename):
            raise FileExistsError(filename)

        data_obj = {
            "path" : path
        }

        # Get response
        response = self.getRequest("data/download", data_obj)

        # Write file
        with open(filename, 'wb') as fh:
            fh.write(response.text.encode("utf-8"))
        

    class DirectoryListing:
        """
        Represents files stored on the ApRES SD card
        """

        def __init__(self, resp_json):
            """
            Create a new DirectoryListing from parsed JSON data
            """

            #: List of file objects (:py:class:`apreshttp.Data.FileObject`)
            self.files = []
            #: List of directory objects (:py:class:`apreshttp.Data.FileObject`)
            self.directories = []
            #: Root path of directory
            self.path = None
            #: Number of files in directory
            self.numObjectsInDir = 0
            #: Number of files in listing
            self.numObjectsInList = 0

            self.load(resp_json)

        def __repr__(self):
            str = "DirectoryListing <0x{:x}> with {} files and {} directories\nof a total of {} file system objects.\n\n".format(id(self), len(self.files), len(self.directories), self.numObjectsInDir)
            if len(self.directories) > 0:
                str += "\tDirectories\n";
                for direc in self.directories:
                    str += "\t\t{} [{} bytes, last modified {}]\n".format(direc.name, direc.size, direc.date)
                str += "\n"
            if len(self.files) > 0:
                str += "\tFiles\n"
                for fil in self.files:
                    str += "\t\t{} [{} bytes, last modified {}]\n".format(fil.name, fil.size, fil.date)
                str += "\n"
            return str
            
        def load(self, resp_json):

            if not "path" in resp_json:
                raise BadResponseException("No path key in dir listing request.")

            self.path = resp_json["path"]

            if not "files" in resp_json:
                raise BadResponseException("No files key in dir listing request.")
            # Store values
            self.numObjectsInDir = resp_json["length"]
            self.index = resp_json["index"]
            self.pageSize = resp_json["list"]

            # Calculate page (and max page)
            self.pages = math.ceil(self.numObjectsInDir / self.pageSize)
            self.page = math.floor(self.index / self.pageSize)

            self.numObjectsInList = resp_json["fileCount"]

            for file in resp_json["files"]:

                if file["dir"]:
                    self.directories.append(Data.FileObject(file))
                else:
                    self.files.append(Data.FileObject(file))

    class FileObject:
        """
        Class to represent files or directories on the ApRES
        file system
        """
        
        def __init__(self, 
            resp_json
        ):
            # Check whether a response object was passed
            self.__initFromJSON(resp_json)


        def __initFromJSON(self, resp_json):
            datetimeobj = datetime.datetime.strptime(
                resp_json["timestamp"],
                "%Y-%m-%d %H:%M:%S"
            )
            if not isinstance(resp_json["name"], str): 
                raise ValueError("name should be an instance of type 'str'")
            self.name = resp_json["name"]

            if not isinstance(resp_json["path"], str): 
                raise ValueError("path should be an instance of type 'str'")
            self.path = resp_json["path"]

            if not (isinstance(resp_json["size"], int) or isinstance(resp_json["size"], float)):
                raise ValueError("size should be an instance of type 'float' or 'int'")
            self.size = resp_json["size"]

            if not isinstance(datetimeobj, datetime.datetime):
                raise ValueError("date_modified should be a datetime object.")
            self.date = datetimeobj


        def download(self, api, dst_path=None):
            """
            Download the file to the working dir or the destination path

            See the documentation for :py:meth:`apreshttp.Data.download`
            
            :param api: instance of the apreshttp API
            :type api: apreshttp.API
            
            :param dst_path: destination path to download file to
            :type dst_path: str
            """

            api.data.download(self.path, dst_path)



    

################################################################################
# Exceptions

class InvalidAPIKeyException(Exception):
    pass

class InternalRadarErrorException(Exception):
    pass

class RadarBusyException(Exception):
    pass

class NotFoundException(Exception):
    pass

class SystemResetException(Exception):
    pass

class SystemHousekeepingException(Exception):
    pass

class BadResponseException(Exception):
    pass

class NoFileUploadedError(Exception):
    pass

class NoChirpStartedException(Exception):
    pass

class ResultsTimeoutException(Exception):
    pass

class DidNotUpdateException(Exception):
    pass
