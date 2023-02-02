# -*- coding: utf-8 -*-
"""
Calcium imaging importing and processing script
Version 1.0 for BNST cohort 1 062022
Created on Wed Aug 10 12:38:52 2022

@author: eacru
"""
import numpy as np
import pandas as pd
import os
import seaborn as sns
import matplotlib
import csv
import re
from decimal import Decimal as D, ROUND_DOWN
#%% Get list of filepaths
path = "E:\\BNST_calciumImaging_cohort1\\Exported_processed_BNST_c1"
def extractData(path):
    data_list = [] 

    for subdir, dirs, files in os.walk(path):
        file_list = [ file for file in files if not file.endswith( ('.png','.tiff', '.tif') ) ] #exclude image files
    # initialize empty array to fill with file names
        for file in file_list:
            extracted_data = str(os.path.join(subdir,file))
            data_list.append(extracted_data)
    return data_list

#%%
# Import data from .csv files: columns are individual cells, rows are time (s/cell status)

def readCalciumData(filepath_preprocessed):
    
    filepath = filepath_preprocessed                        #temporary solution just copy and paste the filepath for each individual file here
    raw_data = pd.read_csv(filepath)
    try:
#keep only accepted cells - filter out rejected
        raw_data = raw_data.rename(columns = {' ': 'status'}) #this column has no heading
        raw_data_no_time = raw_data.drop('status', axis = 1) #this column contains all of the time information
        accepted_cells = raw_data.iloc[0, 1:] == ' accepted' #boolean filter
        raw_data_no_time = raw_data_no_time.transpose()
        raw_data_filtered = raw_data_no_time.loc[accepted_cells]

        raw_data_time = raw_data.iloc[:,0] #select out timeinformation and transpose to add back into newly filtered dataframe
#raw_data_time = pd.DataFrame(raw_data_time) #this bullshit is making me make the single column of time values a dataframe to join to filtered data

        transformed_data = raw_data_filtered.transpose()
        transformed_data['Time'] = pd.Series(raw_data_time)
        transformed_data = transformed_data.drop([0,]) #drop the accepted identifier since you've already filtered

        return transformed_data
    except:
        print(filepath_preprocessed)

#%% Will need to incorporate in code that auto-identifies and adds subject id and session number when reading in file as separate columns in the dataframe

def getSubjectAndSession(data_lines):
    subject_id = []
    session_id = []
        #remove the extension by finding last occurrence of \\ directory separator for file
    remove_extension = data_lines[data_lines.rfind('\\'):]
    if 'raw' in remove_extension:
        remove_extension = remove_extension.replace('_raw','')
            
        [subject_id,session_id]= re.split('\\_', remove_extension )
        subject_id = subject_id.replace('\\','')
        session_id = session_id.replace('.csv','')
    elif 'ttl' in remove_extension:
         remove_extension = remove_extension.replace('_ttl', '')
         [subject_id,session_id, *kwargs]= re.split('\\_', remove_extension )
         subject_id = subject_id.replace('\\','')
         session_id = session_id.replace('.csv','')
    else:
        [subject_id,session_id]= re.split('\\_', remove_extension )
        subject_id = subject_id.replace('\\','')
        session_id = session_id.replace('.csv','')
                
    return subject_id, session_id
#%% Bulk read in only the raw data into a single dataframe

def readRawData(path):
    data_list = extractData(path)
    data = pd.DataFrame()
    new_list = []
    for file in data_list: 
        if "props" not in file and "events" not in file: #event only data and the properties files you don't want should be saved with these key words in their names
            new_list += [file]
            for new_file in new_list:
                reader = readCalciumData(new_file)
                subject_id, session_id = getSubjectAndSession(new_file)
                reader['Subject'] = subject_id
                reader['Session'] = session_id
                data = data.append(reader)
        #data.pop(0)
    return data
    #return new_list


#subdirectory_path ,unique_file_identifier = os.path.split(filename)



#%% Import GPIO data for ttl stamps
filepath_GPIOs = "E:\\EAC_BNST_cohort1_GPIO_export"
def readGPIOFile(filepath_GPIO_list):
    
    GPIO_all = pd.DataFrame()
    
    
    for filepath_GPIO in filepath_GPIO_list: 
            GPIO = pd.read_csv(filepath_GPIO)
            labels = [' GPIO-1', ' GPIO-2', ' GPIO-3', ' GPIO-4', ' EX-LED', ' BNC Trigger Input'] #list of identifiers for rows to keep
            GPIO_filtered = GPIO.loc[GPIO[' Channel Name'].isin(labels)] #filter out irrelevant channels
            subject_id, session_id = getSubjectAndSession(filepath_GPIO)   
            GPIO_filtered['Subject'] = subject_id
            GPIO_filtered['Session'] = session_id
        
            GPIO_all = GPIO_all.append(GPIO_filtered)      
        
    return GPIO_all

#%% For each subject, read an create a dataframe of a GPIO file

def getSubjectList(filepath_GPIOs):
    subject_list = []
    filepath_GPIO_list = extractData(filepath_GPIOs)
    for filepath_GPIO in filepath_GPIO_list:
        try:
            subject, session = getSubjectAndSession(filepath_GPIO)
            subject_list.append(subject)
            #subject_list = [*subject_list, subject]
            subject_list = [*set(subject_list)]
        except:
            print(filepath_GPIO)
    
    return subject_list
    

#%%
#1. Read in GPIO files only for a selected subject (input) to output dataframe of GPIOs for all sessions for one subject
def getSubjectGPIOs(filepath_GPIOs, subject):
    filepath_GPIO_list = extractData(filepath_GPIOs)
    subject_GPIO_list = []
    for filepath in  filepath_GPIO_list:
        if str(subject) in filepath:
            print(filepath)
            subject_GPIO_list.append(filepath)
    globals()['GPIOs' + str(subject)] = readGPIOFile(subject_GPIO_list)
            
    return globals()['GPIOs' + str(subject)]
            
            
            
#%%
# Read in GPIOs for a given session but all subjects to ouptut as dataframe of single sessions gpios for all subjects
def getSessionGPIOs(filepath_GPIOs,session):
    filepath_GPIO_list = extractData(filepath_GPIOs)
    session_GPIO_list = []
    for filepath in filepath_GPIO_list:
        if f'_{session}_' in filepath:
            print(filepath)
            session_GPIO_list.append(filepath)
            globals()['GPIOsSession'+str(session)] = readGPIOFile(session_GPIO_list)
    return globals()['GPIOsSession'+str(session)]
#%% 1. Normalize df values based on average fluorscence chance (df) throughout the session
# must be done for each individual cell. Will need to iterate through all columns -last column (time)
#note as of 1/10/2023 -- IDPS data output has unknown mean substraction to get dF, so average across session for this normalization will not necessarily correspond to subtracted mean
def normalizeData(transformed_data):
    
    
    #average_session_df = transformed_data.iloc[:,4:(transformed_data.shape[1])] #fill with all but time column (time column should always be last column!)
    average_session_df = transformed_data.iloc[:,0:(transformed_data.shape[1])]
    average_session_df = average_session_df.astype(str).astype(float) #original datatype is 'object' so first convert values to 'string' types and then strings to 'floats'
    normalized = average_session_df/ average_session_df.mean(axis = 0)
    
    #add back in timecolumn
    
    # make sure that z score normalization is done across cells or z scored within a cell across the session
    #z_scored = normalized.iloc[:, 0:-1].apply(lambda x: (x-x.mean()) / x.std() , axis = 0)
    
    normalized['Time'] = transformed_data['Time']
   # normalized['Subject'] = transformed_data['Subject']
    
    return normalized

#%%
def zScore(normalized_data):
    no_time = normalized_data.drop(['Time'], axis = 1)
    z_scored_data = no_time.apply(lambda x: (x-x.mean()) / x.std(), axis = 0)
    
    return z_scored_data
#%%
'''in some instances, we have differences in the ttl high-low change that are close together
    (i.e. within 50 ms). to remove identifying false event
    starts, add in if/else statement to take lowest index/
    timestamp between consecutive values and ignore the next 
    consecutive timestamp
    
    from Grace's AB task files - consecutive diffs 0.0002 (0.2 ms difference)'''
    
def removeFalsePositives (events_times):
    false_positives = events_times[(events_times['Time (s)'].diff()) < 0.05 ].index
    events_times.drop(false_positives, inplace = True)
    
    return events_times
    
                
                


#%% With df/f data or z-scored data, identify for each cell (column) each timepoint around events

#1. Select which GPIO value you are interested in, take change in values, and threshold (-20000) to get index of events
def identifyEvents(GPIO_filtered, number):
    cue_ttls = GPIO_filtered.loc[GPIO_filtered[' Channel Name'] == ' GPIO-{}'.format(number)]
    cue_ttls['ttl_change'] = cue_ttls[' Value'].diff()

    events_times = cue_ttls.iloc[np.where(cue_ttls.ttl_change < -20000)]
    
    events_times = removeFalsePositives(events_times)
    
    return events_times

#for function -- downsample gpio file 
# for function -- add in check to look and eliminate consecutive tiemstamps

#%% Use timestamp for ttls to bin calcium events around ttls

def  findEvents(events_times, GPIO_filtered, z_scored):
# before alignings, subtract trig onset timestamp from Time (s) values for each GPIO (this will be BNC Trigger Input has a value of 0.0)
    ttl_timestamp = events_times['Time (s)'] # timestamps you will refer to to find indices of calcium imaging events

 # pull out the BNC trigger input
    session_start = GPIO_filtered['Time (s)'].loc[(GPIO_filtered[' Channel Name'] == ' BNC Trigger Input') & (GPIO_filtered[' Value'] == 0.0)]

    session_start = session_start.tolist() #convert to list type for indexing in loop
#subtract session start from GPIO timestamps for correct time alignment to calcium recording file

    ttl_timestamp_correct = np.array(ttl_timestamp) - np.array(session_start)[0]

#now that corrected timestamps are in an array, use this to find values within range of GPIO timepoints in the calcium dataframe

    events_timelocked = pd.DataFrame()  # initialize empty dataframe
    events_timelocked['Event Number'] = ""

    z_scored['Time'] = z_scored['Time'].astype(str).astype(float)


    for index in range(len(ttl_timestamp_correct)):
    
        time_zero = z_scored.iloc[(abs(z_scored['Time'] - ttl_timestamp_correct[index]).argmin())]
        
        
        events_timelocked = events_timelocked.append(time_zero)
        events_timelocked['Event Number'].iloc[index] = index
         # add result of zero timepoint as dataframe
        
   # events_timelocked = pd.concat(events_timelocked, ignore_index=True)
   

    return events_timelocked
#%% scale findEvents to automate for a single subject across all sessions
def findEventsAllSessions(subject_GPIOs, GPIO_number, subject_data_z_scores):
    events_all_sessions = pd.DataFrame()
    for session in subject_data_z_scores.Session.unique():
        session_GPIOs = subject_GPIOs.loc[subject_GPIOs.Session.astype(int) == session]
        identify_session_ttls = identifyEvents(session_GPIOs, GPIO_number)
        find_session_event = findEvents(identify_session_ttls, session_GPIOs, subject_data_z_scores.loc[subject_data_z_scores.Session == session])
        events_all_sessions = events_all_sessions.append(find_session_event)
    return events_all_sessions
               
#%%

def getEventWindows(z_scored, events_timelocked):
    event_window = pd.DataFrame()
    event_number = 1
#1. first get range for each event of 0 to 2 seconds
    for event in range(len(events_timelocked)):
        
        event_range = z_scored.loc[z_scored['Time'].between(events_timelocked['Time'].iloc[event] - 2, events_timelocked['Time'].iloc[event] + 2)]
        event_range['Event Time'] = event_range['Time'] - events_timelocked['Time'].iloc[event]
        event_range['Event Time Truncated'] = event_range['Event Time'].apply(lambda x: float(D(str(x)).quantize(D('0.01'), rounding = ROUND_DOWN)))
        event_range['Event Number'] = event_number
        event_number = event_number+1
    
        event_window = event_window.append(event_range)
        

    return event_window


#%%
def getEventWindowsAllSessions(z_scored, events_all_sessions):
    event_window_df = pd.DataFrame()
    for session in events_all_sessions.Session.unique():
        session_z_scored = z_scored.loc[z_scored.Session == session]
        session_events = events_all_sessions.loc[events_all_sessions.Session.astype(int) == session]
        event_windows = getEventWindows(session_z_scored, session_events)
        event_window_df = event_window_df.append(event_windows)
    return event_window_df


#%% 



    
    






    

