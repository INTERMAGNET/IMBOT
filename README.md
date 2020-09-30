# IMBOT - an automatic one-second data checker for INTERMAGNET

R. Leonhardt, ZAMG, Conrad Observatory, Vienna

## Abstract

IMBOT provides automatic routines to convert and evaluate INTERMAGNET (IM) one-second data submissions. The primary aims of IMBOT is to (1) simplify one-second data submissions for data providers, (2) to speed up the evaluation process significantly, (3) to consider current IM archive formats and meta information (e.g. on leap seconds), (4) to simplify and speed up the review process for data submitter and finally (5) to reduce the workload of human data checkers. IMBOT continuously access the upload directory of the geomagnetic information nodes and checks for new one-second data submissions. If new data submissions are found these data sets, independent of packing routines and format, are downloaded and eventually extracted. A basic read test is performed and, if successful, submitted data sets are converted to a current version of the IM [IMAGCDF] archiving format. While conversion, meta information and data content are evaluated. Depending on success and completeness of the data products, different levels will be assigned between level0 (significant problems) to level2 (data fully meets the IM submission standards). A detailed [IMBOT report] is automatically produced and, if contact information is available, automatically send out to the submitting institute. Corrections to data products are easily possible, by either uploading corrected data files or a simple configuration file for updating meta information. Such templates are generated automatically and are contained in the evaluation report. Re-evaluation is triggered automatically by updating this information in the submission directory. The full evaluation process is usually finished within 24 hours after data submission, and the data product can be provisionally accepted by INTERMAGNET.  If level2 is obtained, most time-consuming and typical problems have been solved already (mostly by the conversion routine) and for any further evaluation a human data checker can focus on quality considerations. The [IMBOT report] and level grade is available for end users, so that one-second data sets are in most cases already usable within hours after data submission.
     

## 1. Introduction

Since 2014 [INTERMAGNET] welcomes submissions of data products with one-second resolution. For effective archiving of such data sets a new data format, [IMAGCDF], was suggested. All INTERMAGNET observatories are invited to submit such data sets along with their traditional one-minute data products. The acceptance of an observatory for INTERMAGNET is still solely based on the quality of definitive one-minute products. Nevertheless, submitted one-second data should meet high INTERMAGNET standards as well and the quality of these data products needs to be tested and evaluated by a transparent and conclusive process. Ideally, an end user of such data products can also access and understand the quality assessment scheme. 
A major problem of evaluating one-second data products is the large amount of data and big file sizes, which usually make it more complicated to handle them for data checkers. On the other side, the amount of data, the need for more sophisticated data formats and meta information lead also to problems on the supplier side. At the moment (mid 2020) most submitted data sets have not been checked so far.
Most one-second data has been submitted for the year 2016 by the time of writing this summary. Therefore, this year was selected to develop and evaluate the INTERMAGNET automatic data checker (IMBOT). Data files from 36 observatories are available for 2016. These data files have been submitted in various different ways. The underlying data formats are either IAGA-2002 or different versions of IMAGCDF. IAGA-2002 submissions cover daily records which then have been packed into either daily, monthly or yearly zip files using zip or tgz compressions. IMAGCDF file submissions consist mostly of daily files, compressed in gnuzip or zips or just tared. Monthly IMAGCDF files without any additional compression as requested by IM are provided by few observatories only. When looking at the file coverage it is found that about 20% of the submissions do not cover the expected time range. These files usually contain one second of the previous month and end at 23:59:58 of the last day in the month. When it comes to expected meta information, requested information is missing in more than 75% of all submissions. Nevertheless, most of these issues are not difficult to solve, altough they would require a significant amount of discussion between data checker and submitting institut.
The principle idea of IMBOT, the automatic data checker, is to minimize the work load on both sides, data supplier and data checker, and provide one-second data as fast as possible to end-users. IMBOT accesses data uploads from the observatories and automatically converts the uploaded data sets into an INTERMAGNET conform [IMAGCDF] archive format. During the conversion process, data and meta information content is checked and any missing information is requested from the uploading institute. Missing meta information can be easily supplied, by providing this data in an automatically produced and pre-configured text file to be uploaded into the submission directory minimizing the amount of data needed to be transferred to the GIN. Thus, at time when data checkers need to finally evaluate such data sets, most technical problems have been solved already, and the basic content should be conform to IM rules. The evaluation process makes use of a level description, similar as in other disciplines and as used for satellite data products. Therefore most end users are already well acquainted with such evaluation process. In dependency of data content, meta information and data quality, data is assigned to different quality levels from 0 to 3, from which the highest level 3 can only be reached after manual control from a data checker.

## 2. Basic concept

### 2.1 How does IMBOT work

IMBOT is running on an independent Linux server, which currently is a poc120 industrial computer, located in southern Germany, hereinafter denoted as IMBOT server. The IMBOT server is maintained by an observer, the IMBOT manager, who monitors run time and data processing on the machine. The IMBOT server accesses periodically, e.g. twice a day, the INTERMAGNET GIN in Paris, and scans the one second submission directories of the last three years for new and modified files and directories. The scanned directory is GINSERVER/YEAR/second/YEAR_step1/OBSCODE. New or modified files are identified by their creation and modification time, and by comparing this information with an "already processed" memory on the IMBOT server. If a new directory or new data is found within an observatories directory at the GIN, which has not changed for at least 3 hours, then data within is directory will be analyzed. The three hour rule, at which no further change occurred, ascertains that the upload process of files for this directory is finished. 
For analysis, the new data set will automatically be downloaded and eventually extracted (supported are zip, gz and tar) to a temporary directory on the IMBOT server. An initial read test on a random data file will be performed based on [MagPy]'s format library, supporting e.g. [IAGA-2002] and [IMAGCDF] submissions. If successful, all data sets will be read and subsequently the evaluation steps as outlined below will be performed. Finally, data will be exported into monthly [IMAGCDF] archive files as requested by INTERMAGNET and uploaded to the GIN. The full evaluation process is summarized within an individual [IMBOT report] for each observatory. The report, eventually including instructions on updates/fixes, will then be send to the submitting institute, provided that an e-mail address is available. The report is written in markdown language, which can be viewed in freely available programs (e.g. [dillinger.io]), on [GitHub] and also opened in any text editor. If the data set already satisfies all conditions for final evaluation, then a data checker will be assigned and the [IMBOT report] will also be send directly to the data checker. All automatic processes are logged and reports on newly evaluated data and eventual problems are send to the IMBOT manager. Converted data files, the reports, and if necessary, a template for meta information updates, will also be uploaded to the GIN into a new subdirectory called "level" to be found here: GINSERVER/YEAR/level/OBSCODE. Original submission in step1 are kept until final evaluation from the data checker. The data submitter is asked to briefly check, whether all converted files have been uploaded into the "level" directory.
  

### 2.2 Quality levels

Any data set which is automatically evaluated will be transferred into a new directory structure on the GIN. If data is unreadable, original data sets will solely remain in the submission directory "step1". The IMBOT manager will be informed on such failures and will contact the submitting institute to check their data submission. Data passing a read test will be moved towards a new directory called level. Within the level directory, subdirectories with the [IAGA] obscode as directory name will be established. A file called e.g. **level1_underreview.md** will provide information on the evaluation state of the data set. **underreview** indicates, that the data set can reach the next evaluation level if appropriate information is provided or data checking is finished. If no updates happen within a certain time limit (suggested here are three months) then the current level will be fixed (e.g. **level1.md**). All data sets within the level directory are provisionally accepted by INTERMAGNET.

#### Level 1

Any uploaded data set which is readable and can be converted to an [IMAGCDF] format is automatically assigned to level 1. The uploaded data sets can be either [IAGA-2002] files or [IMAGCDF] files. Compressed archives containing these files using ZIP, GNUZIP and/or TAR are also supported. Level 1 data is already published by INTERMAGNET and made available to end users, including information on the level determination. A level 1 test is performed completely automatic by IMBOT. 

#### Level 2

Level 2 acceptance requires that all requested meta information is provided, including information on standard levels as outlined in the [IMAGCDF] format description, like timing accuracy, instruments noise levels etc. IMBOT will check the supplied meta information and, if anything is missing or unclear, will request this information from the submitting institute. Missing information can be uploaded by a simple sheet, triggering IMBOT to re-evaluate the data set. If such information cannot or is not provided within a certain time limit, the evaluation level will remain on Level 1. Besides, a level 2 check includes some basic test on data content (completeness, time stamping etc) and (suggested here) includes a basic comparison with submitted/accepted one-minute data products to evaluate the definitive character. If successful, a [IMBOT report] is constructed (e.g. level2*.md) and the data set is assigned to a data checker for level 3 evaluation. Level 2 test are also performed completely automatically by IMBOT.

#### Level 3

The final level, Level 3, requires a review of the data set by a data checker, with the primary focus on data quality. As soon as level 2 is successfully obtained, a data checker is assigned and will get a basic evaluation summary from an automatic report by IMBOT. The data checker can directly focus on checking contents and data quality of the submitted data sets.


### 2.3 Updating missing information 

After submitting your data, IMBOT will check your data for general readability and completeness. It will create a [IMBOT report] which will be send to the submitting institute. 
Within this report you will see, what level has been assigned to your submission. In dependency of this level, you eventually need to take action:  

#### If your data was assigned level 0

Your data could not be read or significant problems with your submission were encountered (e.g. no one second data, empty files). Please correct the issues and upload a new data set. If you do not know how to proceed, contact the IMBOT manager.

#### If your data was assigned level 1

Some meta information or data is missing. If data is missing, please upload such data files. If meta information is missing, please locate the "meta_OBSCODE.txt" file within the level directory and download this file. Please add any missing meta information into this file as outlined and described within this text file (an example is given below). Finally upload this meta_OBSCODE.txt file to the step1 upload directory. DO NOT CHANGE THE FILENAME. Uploading this file or any new data file will trigger an automatic re-evaluation.

#### If your data was asigned level 2

Everything is fine. There is nothing you need to do. A data checker will contact you regarding quality checks and final level assignment.


#### Typical example of a meta_OBSCODE.txt file

```sh
## Parameter sheet for additional/missing metainformation
## ------------------------------------------------------
## Text to explain how to fill it
## Use "None" if not available
 
# Provide a valid standard level (full, partial), None is not accepted
StandardLevel  :  partial
 
# If Standard Level is partial, provide a list of standards met
PartialStandDesc  :  IMOS11,IMOS14,IMOS41
 
# Reference to your institution (e.g. webaddress)
ReferenceLinks  :  www.my.observatory.org
 
# Provide Data Terms (e.g. creative common lisence)
TermsOfUse  :  Do whatever you want with my data

# Missing data treatment (if data is not available please uncomment) 
#MissingData  :  ignore
```


#### Using meta_OBSCODE.txt with original submission

It is possible to supply a meta_OBSCODE.txt file directly with original submission. If you submit [IAGA-2002] files some required information for creating INTERMAGNET CDF archives is always missing. By supplying this data directly with the submission, you can directly reach level 2 grades without any further updates.


## 3. Summary of all aspects checked


 -   Submitted files and formats
        It is tested whether all requested files are available in readable formats (IAGA-2002, IMAGCDF).
        Submitted data is converted to 12 monthly IMCDF files with IM recommended filenames.

 -  Meta information
        Do all files contain the requested meta information and is this meta information consistent between all different files.
        Required meta information is described in the [IMAGCDF] format descriptions. If meta information is missing, a summary will be given in the [IMBOT report] and a template will be created to support the submitting institute in providing this information. Besides, the report will contain some information on non-obligatory meta information which might, however, be helpful for end users. 

 -  Data content
        IMBOT is checking data coverage in all files. If individual data points are missing (time step and values), the report will contain amount and month of occurrence. Sometimes, the last second in month is missing, particularly in December submission. If more then just individual points are missing, the data set might be classified as level0, as such observation might be caused by corrupted uploads and downloads, until the submitting institute confirms the unavailability of such data. If F values are provided, IMBOT tests whether these values are independent measures of the field (S), as requested by INTERMAGNET. This test is done by calculating delta F and its standard deviation from the vectorial components. If both values are negligible small, non-independency is assumed. 

 -  Data quality
        Data quality is not used as a criteria for level classification. Nevertheless, IMBOT runs a few tests and provides this information within the report, so that the submitting institute as well as the data checker gets some initial feedback about quality parameters. The first test is performed if independent F values are provided. Delta F variations are calculated on a monthly basis. Average delta F, which is expected to be close to zero, and its standard deviation are listed in the report. A predefined list of quiet days is used to extract data from these days and to calculate the power spectral density function for each day. Using periods below 10 seconds, the noise level is determined from each daily record and all individual noise levels are then averaged. This average noise level and its standard deviation are also given in the report. As noise level is part of the requested StandardLevel description of the IMAGCDF's meta information, you will get some recommendation for IMOS-11 (see [IMAGCDF]). If the standard deviation of the noise level is relatively high (e.g. approaching or exceeding mean value) the submitting institute might want to check for technical and other disturbances. 

 -  Data consistency
        Finally, as the data product is termed "definitive", the consistency with submitted one-minute data products is tested. Like for data quality these tests are listed in the [IMBOT report], but only severe differences between average monthly values of each component exceeding 0.3 nT might influence the assigned level. Besides, the standard deviation of the difference and individual maximal amplitude differences are tested and listed in the report. If amplitude differences are small e.g. below 0.1 nT, this indicates that obviously one-second data is the primary analyzed signal of the submitting institute, and all "cleaning" as been performed on this data set. Minute data is just a filtered product of the one-second data set. If larger amplitudes are observed, e.g. independent cleaning has been performed or even different instruments are used. 


## 4. Results for a complete analysis of 2016

Below a table summarizes IMBOT analyses of 2016. The 2016 analysis has also been used for development and error analysis of the underlying packages. IMBOT makes use of [MagPy] and requires version 0.9.7 or larger particularly for the one-minute data comparison, as some reading issues with [IAF] data have been solved in this version. All reports and converted files are readily available, but have not yet been send out to the submitting institute. As IMBOT firstly requires a conceptual acceptance from [INTERMAGNET] and reviews of its methodology, all these results are preliminary and do not indicate any decision from [INTERMAGNET]. 

Parameter | Amount
--------- | ------
Available submissions | 36
IMBOT successful analyses | 36
Submitted as IAGA-2002 | 13
Submitted as ImagCDF | 23
Level 0 | 3
Level 1 | 25
Level 2 | 8
Most common level0 reason | empty file for one month
Most common level1 reason | StandardLevel description missing (in all level 1 cases)

Predominantly level 1 classifications are found. The basic reason for this classification, found in all level 1 data sets, is the absence of a StandardLevel description as requested in [IMAGCDF]. This information is missing for all IAGA-2002 submissions. StandardLevel description supports two inputs: **full** or **partial**. In case of **partial**, details on the standard levels are required. A full list is provided in the [IMBOT report]. In order to deal with this issue, the observatory just needs to fill out the provided template, which is sent out with the report. After uploading the meta template to the submission directory the data set is re-evaluated. This way, most of the level 1 submissions will get re-evaluated for level 2 with minimal workload and data transfer. The second most important reason for level one is usually an incomplete December record with one second missing on 31 December. Uploading this data file with a complete amount of seconds will also trigger a re-evaluation. 
The most common reason for level 0 is a missing record for one month although an empty data file is provided. The most likely cause for this observation is a corrupted file structure. Details are provided in the [IMBOT report]. Uploading the data file again and checking its size will most likely solve this issue. In one case, indications for many duplicates are found within the file structure for a few months.
Overall, all submissions have been carefully prepared and submitted data generally is of high quality. 


Table with all results for appendix

OBSCODE | Level |  sub. DataFormat | IMBOT vers |   Level 0 problem   |    Level 1 problem   |   Other issue
------- | ----- | ---------------- | ---------- | ------------------- | -------------------- | ------------------
ABK     |   2   |   IMAGCDF 1.2    |    0.9.1   |                     |                      |
ASP     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
BDV     |   0   |   IMAGCDF 1.1    |    0.9.1   |   Duplicates        |                      |
BEL     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
BOU     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
BRW     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
BSL     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
CKI     |   2   |   IMAGCDF 1.1    |    0.9.1   |                     |                      |
CMO     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
CNB     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev              |
CSY     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev              |
CTA     |   0   |   IMAGCDF 1.1    |    0.9.1   |  Month missing      |                      |
DED     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
EBR     |   0   |   IMAGCDF 1.1    |    0.9.1   |  Month missing      |                      |
FRD     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
FRN     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |  7z, very high noise level?
GNG     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
HER     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev              |
HLP     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
HON     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |  7z
HRN     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
KAK     |   2   |   IMAGCDF 1.x    |    0.9.1   |                     |                      |  min with 0.9.7
KDU     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
KNY     |   1   |   IMAGCDF 1.x    |    0.9.1   |                     |  Amount6,7           |  memory issue (firefox?)
LRM     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev              |
LYC     |   2   |   IMAGCDF 1.2    |    0.9.1   |                     |                      |
MAW     |   1   |   IMAGCDF 1.1    |    0.9.1   |                     |  StdLev, Amount12    |
MCQ     |   2   |   IMAGCDF 1.1    |    0.9.1   |                     |                      |
MMB     |   2   |   IMAGCDF 1.x    |    0.9.1   |                     |                      |  min with 0.9.7
NEW     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |  7z
SHU     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |
SIT     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |      
SJG     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |      
TUC     |   1   |   IAGA-2002      |    0.9.1   |                     |  StdLev              |      
UPS     |   2   |   IMAGCDF 1.2    |    0.9.1   |                     |                      |      
WIC     |   2   |   IMAGCDF 1.2    |    0.9.1   |                     |                      |


## 5. Discussion

### 5.1 Server issues 

With version 1.0.0, IMBOT requires that the GIN data source is mounted on the analysis server. At present this is done using an ftp mount based on curlftpfs. IMBOT solely analyses files within the step1/OBSCODE directory. Any further subdirectories are neglected. To minimize security issues it would be advisable to change from FTP access towards a more secure connection protocol in the future. Possible options which are easy to integrate would be ssl connections. The IMBOT server itself requires a suitable amount of memory in order to deal with yearly one-second data sets. In particular, if several data sets are uploaded at once, all analysis are performed in one run. The current hardware (8GB ram) allows for contemporaneous analysis of up to 10 records without memory issues, although this strongly depends on data content. Large data sets with high resolution scalar and temperature readings need significantly more memory. As it is rather unlikely that more than 10 data sets are uploaded within three hours of the year, this limitation should not be an issue. Nevertheless, failures are monitored and if the data submitter does not receive a [IMBOT report] within 24 hours after submission, please contact the IMBOT manager. 

### 5.2 Format issues

Although IMBOT supports many different data formats and packing routines, it is not meant to be an universal interpreting machine. Please stick to the most common packing methods and avoid, if possible, commercial packing routines. Currently supported are [IAGA-2002] sec files, [IMAGCDF] files, as well as .tar, .tar.gz (.tgz) and .zip compressions. From the tested 2016 data set, 3 zipped records produced an "End-of-central-directory signature not found" error. IMBOT deals with such incomplete/corrupted files by using the external [7z] routine. Data content was fully recovered for all these files. Nevertheless, please check your files thoroughly before uploading. Data submission should be based preferably on [IMAGCDF] data or [IAGA-2002]. Please add any missing meta information within these data structures, or submit them along with your files by using the IMBOT meta file as described above. Nevertheless, there might be formatting and interpretation issues. You can easily test your files before: If [MagPy] can read and interpret the data sets, then IMBOT should be able as well. The version of MagPy, which is used for format conversion, is given in the [IMBOT report].

### 5.3 General issues

A couple of issues showed up while developing the program. A small list containing description and how it was solved is given below. This should provide an example on how upcoming issues should be reported. The project folder on GitHub provides an issue section where you can write down a detailed description. The developers are automatically informed. All user can access issues and comment on them. If an issue is solved, a reference to the changed code fragments and a description from the developers will be added before closing. Closed issues can always be accessed later. This way, IMBOT undergoes a permanent and transparent review process.  
 

> Issue: Bug - Scalar data of different resolution not correctly exported in new ImagCDF
>
>MagPy does not export cdf with f values in different resolution correctly.
>This eventually is already an input problem. -> find a solution
>The file converter extracts variometer and scalar data from the original file. 
>If scalar data is of different resolution, this data is joined into a common 
>timeseries, where missing points due to the reduced resolution are denoted by NaN. 
>Thus, real missing data is not easy distinguishable from spaces due to reduced 
>resolution. Check the final monthly ImagCDF structures whether this is transferred
>into these files.
>
> -> solved with MagPy 0.9.7


> Issue: Test - Check whether raw data and converted data are identical
>
> Test case 1: analyse raw data and the resulting converted files. Compare the reports for differences.
> -> done for MCQ > report of converted data identical to raw data (updated are only leap seconds, and data format)
> Test case 2: use MagPy to load raw and converted level data. Subtract both streams: Difference needs to be zero
> -> done for EBR > perfect


> Issue: Bug - Meta information needs to be conform with ImagCDF ruleset
> 
> e.g. References, DataReferences not existing. ImagCDF type is called ReferenceLinks.
> has been corrected before uploading --- check


> Issue: Bug - One-minute IAF files of a few observatories cannot be read
> 
> For some observatories (2016: KAK, BEL, ) one-minute IAF binary files cannot be read.
> The reading process terminates and returns an empty file structure. This error
> requires a review of the MagPy readIAF method. 
>
> -> solved with MagPy 0.9.7


> Issue: Discussion - Auxiliary data like temperature.
>
> If such data is confirmed in meta information, is it then necessary/obligatory
> to provide such data along with the cdf file?
> Currently, this is sometimes done, sometimes not.
> Dealing with this issue requires a decision by the definite data committee of IM.


### 5.4 Test criteria

Currently it is an ongoing discussion which criteria and thresholds are necessary in order to evaluate submitted data sets. IMBOT makes use of a minimal approach. The highest automatic grade requires that the data sets are readable, complete and (correctly) contain all requested information for the [IMAGCDF] file format. There is no evaluation of data quality and only a single test regarding its definitive character, which was met by all submissions tested so far. Any test of data quality or more sophisticated analysis of its definitive character is currently subject of a final analysis by a human data checker.
Nevertheless, it is suggested here that any submitted data set, which is readable and convertable, will already be provisionally accepted by INTERMAGNET using the IMBOT automatic procedure. As the data sets are automatically converted to a common data format, further data access is straight forward. A detailed level report allows to judge the classification for end users and eventually select data which suit their needs. Due to the detailed standard level description of the [IMAGCDF] format, a level 2 product already contains essential details on data quality as provided by the data submitter. Part of this information is cross checked by IMBOT (e.g. noiselevel). Based on this information it is suggested here that a level2 data set is complete, conclusive and usable for end users. From a modelers perspective, this information is sufficient to work with the data products.


### 5.5 Open aspects for the future

  - data checker duties
  - can data checker handle the files ?-> yes
  - data checker mailing list (each one connected to a list of observatories, or random?)
  - can submitter add a blacklist/whitelist on possible data checkers?
  - resubmission (could be just done into step1 - datachecker is informed if level2 is satisfied)
  - is data quality a criteria (?) or just meta information 
       - should there be something like level 3 or not?
       - do we need grades at all?
       - INTERMAGNET defined Standard levels for one second data. Which ones are obligatory to obtain highest grades?
       - Noise level analysis is very simple at the moment, too be improved.
       - How to deal with amplitude deviations between definitive one-minute and definitive one-second?

### 5.6 Further improvements

Suggested further improvements include a revision check. If no revision is performed or final revision requested for a certain time range, e.g. 3 months, than the current level of data submission is confirmed by simply renaming the "level1_underreview.txt" to "level1.txt". Obviously this can be done automatically as well.

Although IMBOT has been created for definitive one-second data it can also be modified and used for other data sets as well. A possible application would be high resolution variation data which could be quickly checked with such routine and provided as a tested data product by INTERMAGNET basically on the fly. Further data sources might also be included. It is also not too difficult creating a similar routine helping with one-minute data analysis.

IMBOT is written completely modular. Each checking technique is described and coded in an individual method. Thus, IMBOT can be simply extended or modified towards others tests and other data sets.


## Conclusion

IMBOT can be used instantly for all future processing of new one second uploads. It can also be used to start an evaluation of all submitted data sets from 2014 onwards and provides the possibility to get this data sets published on INTERMAGNET within hours. For testing the capabilities of IMBOT and for reviewing of its methods, it is possible to run IMBOT for selected observatories and to send reports and mails only to a selected group of referees. It is our intention to describe IMBOT and all methods as good as possible. The source code is accessible and, thus, the evaluation process is transparent both for submitters and end users. 



   [INTERMAGNET]: <https://intermagnet.github.io/>
   [IMAGCDF]: <https://www.intermagnet.org/publications/im_tn_8_ImagCDF.pdf>
   [MagPy]: <https://github.com/geomagpy/magpy>
   [dillinger.io]: <https://dillinger.io/>
   [7z]: <https://www.7-zip.org/>
   [GitHub]: <https://github.com/>
   [IAGA]: <http://www.iaga-aiga.org/>
   [IAGA-2002]: <https://www.ngdc.noaa.gov/IAGA/vdat/IAGA2002/iaga2002format.html>
   [IAF]: <https://www.intermagnet.org/data-donnee/formats/iaf-eng.php>
   [IMBOT report]: <https://github.com/INTERMAGNET/IMBOT/blob/master/examples/level1_underreview.md>


