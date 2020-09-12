# OBSCODE - Level 1

# Analysis report for one second data from BOU

### Issues to be clarified for level 2:

Issue | Observed in months
----- | -----
header StandardLevel missing | 1,2,3,4,5,6,7,8,9,10,11,12
StandardLevel full or partial - see TN8: 4.7 Relevant data standards | 1,2,3,4,5,6,7,8,9,10,11,12
PartialStandDesc required for partial - see TN8: 4.7 Relevant data standards | 1,2,3,4,5,6,7,8,9,10,11,12

### Possible improvements (not obligatory):

Improvements | Applicable for months
----- | -----
provide information on Terms | 1,2,3,4,5,6,7,8,9,10,11,12


### ImagCDF standard levels as provided by the submitter

StandardLevel | Description | Validity
--------- | --------- | ---------
IMOS-01 | Time-stamp accuracy (centred on the UTC second): 0.01s | not provided
IMOS-02 | Phase response: Maximum group delay: ±0.01s | not provided
IMOS-03 | Maximum filter width: 25 seconds | not provided
IMOS-04 | Instrument amplitude range: ≥±4000nT High Lat., ≥±3000nT Mid/Equatorial Lat. | not provided
IMOS-05 | Data resolution: 1pT | not provided
IMOS-06 | Pass band: DC to 0.2Hz | not provided
IMOS-11 | Noise level: ≤100pT RMS | not provided - IMBOT indicates success
IMOS-12 | Maximum offset error (cumulative error between absolute observations): ±2. 5 nT | not provided
IMOS-13 | Maximum component scaling plus linearity error: 0.25% | not provided
IMOS-14 | Maximum component orthogonality error: 2mrad | not provided
IMOS-15 | Maximum Z-component verticality error: 2mrad | not provided
IMOS-21 | Noise level: ≤10pT/√Hz at 0.1 Hz | not provided
IMOS-22 | Maximum gain/attenuation: 3dB | not provided
IMOS-31 | Minimum attenuation in the stop band (≥ 0.5Hz): 50dB | not provided
IMOS-41 | Compulsory full-scale scalar magnetometer measurements with a data resolution of 0.01nT at a minimum sample period of 30 seconds | not provided
IMOS-42 | Compulsory vector magnetometer temperature measurements with a resolution of 0.1°C at a minimum sample period of one minute | not provided

### Too be considered for final evaluation

Level 3 considerations | Observered 
----- | -----
Large amplitude differences between definitive one-minute and one-second data products | 3


### Provided Header information


Header | Content
----- | -----
StationInstitution | YOUR INSTITUTE
DataPublicationLevel | 4
DataStandardLevel | missing
StationIAGAcode | OBSCODE
StationName | YOUR STATIONNAME
DataTerms | missing
DataAcquisitionLatitude | 55.555
DataAcquisitionLongitude | 222.222
DataElevation | 9456
DataComponents | XYZF
DataSensorOrientation | HDZF


### Basic analysis information

>amount  :  1
>type  :  .zip
>lastmodified  :  1594113906.112519
>obscode  :  OBSCODE
>Readability test file  :  /media/leon/Images/DataCheck/tmp/OBSCODE/raw/obs20160210dsec.sec
>Readability  :  OK
>Data format  :  IAGA-2002
>Year  :  2016
>MagPyVersion  :  0.9.7
>Noiselevel  :  10 pT
>NoiselevelStdDeviation  :  1 pT


### Details on monthly evaluation


Month 1 | Value 
------ | ----- 
mean difference - x component | 0.00629 nT
mean difference - y component | 0.00528 nT
mean difference - z component | 0.0056 nT
stddev of difference - x component | 0.041 nT
stddev of difference - y component | 0.0409 nT
stddev of difference - z component | 0.0404 nT
amplitude of difference - x component | 0.229 nT
amplitude of difference - y component | 0.898 nT
amplitude of difference - z component | 0.202 nT
Datalimits | [datetime.datetime(2016, 1, 1, 0, 0), datetime.datetime(2016, 1, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.084 with a std of 0.199
F | found independend f with sampling period: 1.0 sec
Definitive comparison | differences in peak amplitudes between definitive one-minute and one-second data products observed
Contact | ['cafinn@usgs.gov']

Month 2 | Value 
------ | ----- 
mean difference - x component | 0.00617 nT
mean difference - y component | 0.00495 nT
mean difference - z component | 0.00574 nT
stddev of difference - x component | 0.041 nT
stddev of difference - y component | 0.0406 nT
stddev of difference - z component | 0.0409 nT
amplitude of difference - x component | 0.213 nT
amplitude of difference - y component | 0.213 nT
amplitude of difference - z component | 0.2 nT
Datalimits | [datetime.datetime(2016, 2, 1, 0, 0), datetime.datetime(2016, 2, 29, 23, 59, 59)]
N | 2505600
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.150 with a std of 0.174
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 3 | Value 
------ | ----- 
mean difference - x component | 0.00713 nT
mean difference - y component | 0.00305 nT
mean difference - z component | 0.00408 nT
stddev of difference - x component | 0.224 nT
stddev of difference - y component | 0.151 nT
stddev of difference - z component | 0.0575 nT
amplitude of difference - x component | 13.8 nT
amplitude of difference - y component | 13.1 nT
amplitude of difference - z component | 2.62 nT
Datalimits | [datetime.datetime(2016, 3, 1, 0, 0), datetime.datetime(2016, 3, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.104 with a std of 0.222
F | found independend f with sampling period: 1.0 sec
Definitive comparison | Large amplitude differences between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 4 | Value 
------ | ----- 
mean difference - x component | 0.0513 nT
mean difference - y component | 0.0666 nT
mean difference - z component | 0.0591 nT
stddev of difference - x component | 0.0409 nT
stddev of difference - y component | 0.0409 nT
stddev of difference - z component | 0.0407 nT
amplitude of difference - x component | 0.576 nT
amplitude of difference - y component | 0.237 nT
amplitude of difference - z component | 0.211 nT
Datalimits | [datetime.datetime(2016, 4, 1, 0, 0), datetime.datetime(2016, 4, 30, 23, 59, 59)]
N | 2592000
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.191 with a std of 0.196
F | found independend f with sampling period: 1.0 sec
Definitive comparison | differences in peak amplitudes between definitive one-minute and one-second data products observed
Contact | ['cafinn@usgs.gov']

Month 5 | Value 
------ | ----- 
mean difference - x component | 0.00623 nT
mean difference - y component | 0.00519 nT
mean difference - z component | 0.0032 nT
stddev of difference - x component | 0.0409 nT
stddev of difference - y component | 0.0412 nT
stddev of difference - z component | 0.0404 nT
amplitude of difference - x component | 0.214 nT
amplitude of difference - y component | 0.212 nT
amplitude of difference - z component | 0.2 nT
Datalimits | [datetime.datetime(2016, 5, 1, 0, 0), datetime.datetime(2016, 5, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.192 with a std of 0.211
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 6 | Value 
------ | ----- 
mean difference - x component | 0.00611 nT
mean difference - y component | 0.00484 nT
mean difference - z component | 0.00546 nT
stddev of difference - x component | 0.0409 nT
stddev of difference - y component | 0.0408 nT
stddev of difference - z component | 0.041 nT
amplitude of difference - x component | 0.211 nT
amplitude of difference - y component | 0.21 nT
amplitude of difference - z component | 0.2 nT
Datalimits | [datetime.datetime(2016, 6, 1, 0, 0), datetime.datetime(2016, 6, 30, 23, 59, 59)]
N | 2592000
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of -0.008 with a std of 0.195
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 7 | Value 
------ | ----- 
mean difference - x component | 0.00642 nT
mean difference - y component | 0.0045 nT
mean difference - z component | 0.00704 nT
stddev of difference - x component | 0.0408 nT
stddev of difference - y component | 0.0409 nT
stddev of difference - z component | 0.0404 nT
amplitude of difference - x component | 0.347 nT
amplitude of difference - y component | 0.21 nT
amplitude of difference - z component | 0.206 nT
Datalimits | [datetime.datetime(2016, 7, 1, 0, 0), datetime.datetime(2016, 7, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.097 with a std of 0.214
F | found independend f with sampling period: 1.0 sec
Definitive comparison | differences in peak amplitudes between definitive one-minute and one-second data products observed
Contact | ['cafinn@usgs.gov']

Month 8 | Value 
------ | ----- 
mean difference - x component | 0.00641 nT
mean difference - y component | 0.0048 nT
mean difference - z component | 0.00597 nT
stddev of difference - x component | 0.0408 nT
stddev of difference - y component | 0.0408 nT
stddev of difference - z component | 0.0403 nT
amplitude of difference - x component | 0.265 nT
amplitude of difference - y component | 0.21 nT
amplitude of difference - z component | 0.203 nT
Datalimits | [datetime.datetime(2016, 8, 1, 0, 0), datetime.datetime(2016, 8, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.117 with a std of 0.189
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 9 | Value 
------ | ----- 
mean difference - x component | 0.00618 nT
mean difference - y component | 0.00456 nT
mean difference - z component | 0.00501 nT
stddev of difference - x component | 0.0407 nT
stddev of difference - y component | 0.0409 nT
stddev of difference - z component | 0.0405 nT
amplitude of difference - x component | 0.281 nT
amplitude of difference - y component | 0.219 nT
amplitude of difference - z component | 0.202 nT
Datalimits | [datetime.datetime(2016, 9, 1, 0, 0), datetime.datetime(2016, 9, 30, 23, 59, 59)]
N | 2592000
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.096 with a std of 0.189
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 10 | Value 
------ | ----- 
mean difference - x component | 0.00617 nT
mean difference - y component | 0.00476 nT
mean difference - z component | 0.00762 nT
stddev of difference - x component | 0.0407 nT
stddev of difference - y component | 0.0408 nT
stddev of difference - z component | 0.0411 nT
amplitude of difference - x component | 0.269 nT
amplitude of difference - y component | 0.233 nT
amplitude of difference - z component | 0.2 nT
Datalimits | [datetime.datetime(2016, 10, 1, 0, 0), datetime.datetime(2016, 10, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.161 with a std of 0.356
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']

Month 11 | Value 
------ | ----- 
mean difference - x component | 0.00627 nT
mean difference - y component | 0.00488 nT
mean difference - z component | 0.00598 nT
stddev of difference - x component | 0.0407 nT
stddev of difference - y component | 0.0409 nT
stddev of difference - z component | 0.0408 nT
amplitude of difference - x component | 0.307 nT
amplitude of difference - y component | 0.217 nT
amplitude of difference - z component | 0.201 nT
Datalimits | [datetime.datetime(2016, 11, 1, 0, 0), datetime.datetime(2016, 11, 30, 23, 59, 59)]
N | 2592000
Leap second update | None
Filled gaps | 0
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.101 with a std of 0.178
F | found independend f with sampling period: 1.0 sec
Definitive comparison | differences in peak amplitudes between definitive one-minute and one-second data products observed
Contact | ['cafinn@usgs.gov']

Month 12 | Value 
------ | ----- 
mean difference - x component | 0.00657 nT
mean difference - y component | 0.00484 nT
mean difference - z component | 0.00636 nT
stddev of difference - x component | 0.0409 nT
stddev of difference - y component | 0.041 nT
stddev of difference - z component | 0.0398 nT
amplitude of difference - x component | 0.225 nT
amplitude of difference - y component | 0.261 nT
amplitude of difference - z component | 0.201 nT
Datalimits | [datetime.datetime(2016, 12, 1, 0, 0), datetime.datetime(2016, 12, 31, 23, 59, 59)]
N | 2678400
Leap second update | None
Filled gaps | 86400
Difference to expected amount | 0.0
Level | 1
Samplingrate | 1.0 sec
delta F | mean delta F of 0.099 with a std of 0.184
F | found independend f with sampling period: 1.0 sec
Definitive comparison | good agreement between definitive one-minute and one-second data products
Contact | ['cafinn@usgs.gov']
