from Coliform import RPiCameraBackend
from Coliform import RPiCamera
from Coliform import OneWire
from Coliform import MultiPlot
import RPi.GPIO as GPIO
from time import sleep, time
import threading
import os

# Setup Counters:
j = -1  # image counter
i = 0  # hour counter for led
k = 0  # time counter for image loading and processing into array
imagePlotInstanceIndicator = 0  # Used to initialize plot only once, so as to not try to call plot multiple times.

# global variable placeholder list:
intensity_array = []

OneHourMilliseconds = 3600*1000  # one hour in milliseconds
filepath = os.sep.join((os.path.expanduser('~'), 'Desktop'))  # set filepath to desktop
tf = 'PlotTextFile.txt'  # temporary plot text file
itf = 'IntensityTextFile.txt'  # temporary plot file for intensity
if os.path.isfile(tf):  # searches for preexisting temporary plot text file.
    os.remove(tf)  # destroys temporary plot text file, if it exists.
if os.path.isfile(itf):  # searches for preexisting temporary plot text file.
    os.remove(itf)  # destroys temporary plot text file, if it exists.
ids = OneWire.getOneWireID()  # Get IDs for connected onewires

HeatSignalPin = 11  # pin that sends heat signal to arduino
LEDSignalPin = 13  # pin that sends led control signal to arduino
GPIO.setmode(GPIO.BOARD)  # sets GPIO in board mode, refers to pin number as board pin number in stead of GPIO number
GPIO.setup(HeatSignalPin, GPIO.OUT)  # sets heatsignalpin as out
GPIO.setup(LEDSignalPin, GPIO.OUT)  # sets ledsignalpin as out


def firstPicture():
    camera = RPiCameraBackend.PiCamera()  # camera initialization
    camera.resolution = (2952, 1944)  # image resolution
    camera.brightness = 50  # image brightness 0-100
    camera.contrast = 0  # image contrast 0-100
    camera.iso = 0  # camera iso 0-800
    camera.zoom = (0.0, 0.0, 1.0, 1.0)  # set image region of interest. all values are normalized, ranges are 0.0 - 1.0
    camera.timeout = 2  # time for camera to shutdown in milliseconds
    camera.quality = 75  # image quality 0-100, the higher the quality, less compression
    camera.exposure_mode = ''  # exposure mode set, default is auto
    camera.awb_mode = ''  # auto white balance set, default is auto
    camera.preview = (100, 100, 300, 200)  # set preview screen location and dimension
    camera.capture(mode='JPG', filename='Firstimage.jpg')  # send capture function command to camera.

GPIO.output(LEDSignalPin, GPIO.HIGH)  # sends LED on signal to arduino
firstPicture()
sleep(3)
GPIO.output(LEDSignalPin, GPIO.LOW)  # sends LED off signal to arduino
    
def takePicture():
    camera = RPiCameraBackend.PiCamera()  # camera initialization
    camera.resolution = (2952, 1944)  # image resolution
    camera.brightness = 50  # image brightness 0-100
    camera.contrast = 0  # image contrast 0-100
    camera.iso = 0  # camera iso 0-800
    camera.zoom = (0.0, 0.0, 1.0, 1.0)  # set image region of interest. all values are normalized, ranges are 0.0 - 1.0
    camera.timeout = 23*OneHourMilliseconds  # time for camera to shutdown in milliseconds
    camera.timelapse = OneHourMilliseconds  # time in between each image capture in milliseconds
    camera.quality = 75  # image quality 0-100, the higher the quality, less compression
    camera.exposure_mode = ''  # exposure mode set, default is auto
    camera.awb_mode = ''  # auto white balance set, default is auto
    camera.preview = (100, 100, 300, 200)  # set preview screen location and dimension
    camera.capture(mode='JPG', filename='image%04d.jpg')  # send capture function command to camera.


def startTemperaturePlot():
    y_title_axis = ['Temperature Plot', 'Temperature vs Time', 't(s)', 'T(C)', 'Sensor']  # plot title and axis labels
    MultiPlot.Plot(tf, len(ids), y_title_axis)  # start plot


def intensityDataGeneration():
    global j  # references global j variable (counter)
    global intensity_array  # references global intensity_array variable
    if j == -1:
        rgb_array = RPiCamera.importImage('Firstimage.jpg')  # imports previously taken image as rgb array
        red_avg, green_avg, blue_avg, intensity_avg = RPiCamera.returnIntensity(rgb_array)  # takes average values for rgb found in the array
        intensity_array = [str(red_avg), str(green_avg), str(blue_avg), str(intensity_avg)]  # adds previous values to a list
        MultiPlot.GeneratePlotDataFile(itf, intensity_array, start_time)  # create image intensity data file
        print('Processed Data for Image {} and added to raw data file.'.format(j+1))  # print when processing intensity data for each image
        j += 1
    else:
        rgb_array = RPiCamera.importImage('image{:04d}.jpg'.format(j))  # imports previously taken image as rgb array
        red_avg, green_avg, blue_avg, intensity_avg = RPiCamera.returnIntensity(rgb_array)  # takes average values for rgb found in the array
        intensity_array = [str(red_avg), str(green_avg), str(blue_avg), str(intensity_avg)]  # adds previous values to a list
        MultiPlot.GeneratePlotDataFile(itf, intensity_array, start_time)  # create image intensity data file
        print('Processed Data for Image {} and added to raw data file.'.format(j+1))  # print when processing intensity data for each image
        j += 1  # adds to counter, to process next image


def startIntensityPlot():
    global intensity_array  # references global intensity array variable
    y_title_axis = ['Light Intensity Plot', 'Intensity vs Time', 't(s)', 'I(RGB Value)', 'Color']  # plot title and axis labels
    MultiPlot.Plot(itf, len(intensity_array), y_title_axis)  # start plot

captureThread = threading.Thread(target=takePicture)  # sets up new thread to run takePicture function
captureThread.start()  # start the thread that was setup in the previous line
print('Start Camera Thread.')

start_time = time()  # save initial run time, for reference
elapsed_time = 0  # time elapsed since start_time value
led_run_time_start = 0  # time counter for led run time
LEDStatus = 0  # led status indicator 0 = off, 1 = on

while elapsed_time < (3600*24)+60:  # starts loop for an hour and one minute
    # LED control loops:
    if elapsed_time >= i-30:
        GPIO.output(LEDSignalPin, GPIO.HIGH)  # sends LED on signal to arduino
        LEDStatus = 1  # sets LED status as ON
        i += 3600  # adds an hour for the next LED ON iteration
        led_run_time_start = elapsed_time  # sets current elapsed time as start for current LED run
        print('LED On')
    run_time = elapsed_time - led_run_time_start  # calculates run time from led start time
    if run_time > 60:  # set runtime in seconds
        if LEDStatus == 1:
            GPIO.output(LEDSignalPin, GPIO.LOW)  # after 5 minutes of ON time, if led is on, it is turned OFF
            LEDStatus = 0  # sets LED status to OFF
            print('LED Off.')

    # Image Intensity Data Recording Loops:
    if elapsed_time >= k+10:  # initialize image data processing 10 seconds after image capture
        intensityDataThread = threading.Thread(target=intensityDataGeneration)  # sets up new thread to run intensityDataGeneration function
        intensityDataThread.start()  # start the thread that was setup in the previous line
        k += 3600  # adds an hour to image counter, in order to wait for next image capture
    if elapsed_time >= 25:  # initialize plot 15 seconds after data generation of image processing is started, this in order to give ample time for processing.
        if imagePlotInstanceIndicator == 0:  # ensures this code only runs on first instance
            intensityPlotThread = threading.Thread(target=startIntensityPlot)  # sets up new thread to run startTemperaturePlot function
            intensityPlotThread.start()  # start the thread that was setup in the previous line
            imagePlotInstanceIndicator = 1  # after first instances this inactivates this 'if' statement code
            print('Initialized Image Intensity Plot.')  # print indicating when plot is initialized.

    # Temperature Data Recording and Heater Control Loops:
    TemperatureString, TemperatureFloat = OneWire.getTempList()  # gets temperature values from onewires
    MultiPlot.GeneratePlotDataFile(tf, TemperatureFloat, start_time)  # create temperature plot data file
   # if elapsed_time == 0:
   #     temperaturePlotThread = threading.Thread(target=startTemperaturePlot)  # sets up new thread to run startTemperaturePlot function
   #     temperaturePlotThread.start()  # start the thread that was setup in the previous line
    if float(TemperatureFloat[1]) < 41.0:  # if temp is lower than 41 C NOTE: the number between the [] in Temperature float is the OneWire it will be reading the data from. 0 being the one in the first position, 1 the second position, et cetera...
        GPIO.output(HeatSignalPin, GPIO.HIGH)  # sends high signal to heatsignalpin, which is sent to arduino. HIGH = ~3.3V
    elif float(TemperatureFloat[1]) >= 41.0:  # if temp is higher or equal to 41 C
        GPIO.output(HeatSignalPin, GPIO.LOW)  # sends low signal to heatsignalpin, which is sent to arduino. LOW = ~0V
    # Print Values for Debugging Purposes:
    print(TemperatureString)  # print temperature values
    print('Elapsed Time: {}'.format(elapsed_time))  # Print Elapsed time
    print('LEDStartCounter(i) = {}'.format(i))  # Print Led Counter
    print('ImageProcessingCounter(k) = {}'.format(k))  # Print image processing counter
    # Timekeeping Loops:
    sleep(1)  # sets code to wait 1 second before running again
    elapsed_time = int(time() - start_time)  # calculates elapsed time from difference with start time

GPIO.cleanup()  # cleans GPIO bus

# Save Data to Permanent Files
tempfilename = 'TemperatureData.csv'  # sets filename for temperature data csv
y_variablename = 'TemperatureSensor'  # sets variable name for temperature data csv
MultiPlot.SaveToCsv(tf, tempfilename, filepath, len(ids), y_variablename)  # saves temperature data to csv file

ifilename = 'IntensityData.csv'  # sets file name for intensity data csv
iy_variablename = 'Intensity'  # sets variable name for intensity data csv
intensityDataGeneration()  # adds data from last image to file before saving as csv
MultiPlot.SaveToCsv(itf, ifilename, filepath, len(intensity_array), iy_variablename)  # saves temperature data to csv file
