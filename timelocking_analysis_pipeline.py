# -*- coding: utf-8 -*-
"""
Created on Tue Aug 23 11:53:55 2022
Script using data import functions to process and get events from calcium imaging data
@author: eacru
"""
#%%Import packages

import numpy as np
import pandas as pd
import os
import seaborn as sns
import matplotlib.pyplot as plt
import csv
import re
from decimal import Decimal as D, ROUND_DOWN
from dataImport import extractData
from dataImport import getSubjectGPIOs
from dataImport import normalizeData
from dataImport import findEvents
from dataImport import identifyEvents
from dataImport import findEventsAllSessions
from dataImport import getEventWindows
from dataImport import getEventWindowsAllSessions
from dataImport import getSessionGPIOs
#%% 1. Import exported calcium data (the file is called 'youWork')
raw_data = pd.read_csv("E:\BNST_calciumImaging_cohort1\Exported_processed_BNST_c1\youWork.csv")

#stupid rearranging of columns for making code easier
raw_data = raw_data[raw_data.columns[[0,2,3,4,1,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39]]]
#as you can only read in GPIOs with one subject at a time to process, pick a subject here:
subject = 163

filepath_GPIOs = "E:\\EAC_BNST_cohort1_GPIO_export"
#%%1a. Import subject GPIO files for all sessions
subject_GPIOs = getSubjectGPIOs(filepath_GPIOs, subject)

#%%2. Filter raw file with all subjects, all sessions into dataframe with all session raw data for one subject

#subject_calcium_data = raw_data.loc[raw_data.Subject == subject]
subject_calcium_data = raw_data.loc[raw_data.Subject == subject].dropna(axis = 1, how = 'all')
#drop columns with cells not from subject (they will be filled with NaN) 



#%%3. Normalize subject calcium data by average fluorescence value across the entire session
# this will need to be grouped based on which session the average is coming from

session_list = subject_calcium_data.Session

subject_data_z_scores = pd.DataFrame()
for session in subject_calcium_data.Session.unique():
   session_normalized = subject_calcium_data.loc[subject_calcium_data.Session == session].pipe(normalizeData)
   session_normalized['Session'] = session
   subject_data_z_scores = subject_data_z_scores.append(session_normalized)
   subject_data_z_scores['Subject'] = subject
#%%

#%%4. Time-lock each type of event from each session to each cell's normalized fluorescent score
#For GPIO-2: Cue ttls
cue_events = findEventsAllSessions(subject_GPIOs, 2, subject_data_z_scores)
lever_events = findEventsAllSessions(subject_GPIOs, 3, subject_data_z_scores)
shock_events = findEventsAllSessions(subject_GPIOs, 4, subject_data_z_scores) 

#%%5. Get Event Windows for all Session Events of each type

cue_windows = getEventWindowsAllSessions(subject_data_z_scores, cue_events)
lever_windows = getEventWindowsAllSessions(subject_data_z_scores, lever_events)
shock_windows = getEventWindowsAllSessions(subject_data_z_scores, shock_events)
#%% 6. Get average for epoch for each cell in each session

 
    #%% Plot time window of an event

sns.set_style(style="darkgrid")
#get time +- 2 seconds from time zero
   
event_window = event_window.drop(['Time', 'Event Time'], axis = 1)
event_reformat = event_window.melt(['Event Time Truncated', 'Event Number', 'Session', 'Subject'], var_name = 'Cell', value_name= 'z-score') #reformat to make cell# categorical variable for color

event_averaged = event_reformat.groupby([event_reformat['Event Time Truncated'], event_reformat['Cell'], event_reformat['Session']])['z-score'].apply(lambda x: sum(x)/x.count()).reset_index(name = 'average z-score')
#%%
#average z-scores across matching time windows for each cell 
for session in event_averaged.Session.unique():
    plt.figure()
    sns.lineplot(x = "Event Time Truncated", y= 'z-score', hue = 'Cell', data = event_reformat.loc[event_reformat.Session == session])

#find closest match in calcium timestamp and use that for getting nearest index 
#%% Plot for each cell all events of that type in a session
for session in event_reformat.Session.unique():
    for cell in event_reformat.Cell.unique():
        plt.figure()
        sns.lineplot(x='Event Time Truncated', y='z-score', hue= 'Event Number',  data = event_reformat.loc[(event_reformat['Cell'] == cell) & (event_reformat['Session'] == session)])
#%% Make event heatmaps rather than linegraphs

sns.heatmap(event_reformat[['Event Time', 'Cell', 'z-score']])

#%% Alternate route: Grab GPIOs for all of a session instead of just one subject and get cells activity based on session
session = 5

session_GPIOs = getSessionGPIOs(filepath_GPIOs, session)

#%%

session_calcium_data = raw_data.loc[raw_data.Session == session].dropna(axis = 1, how = 'all')

#%%
subjects = session_calcium_data.Subject
session_z_scores = pd.DataFrame()

for subject in session_calcium_data.Subject.unique():
    normalized_data = session_calcium_data.loc[session_calcium_data.Subject == subject].pipe(normalizeData)
    normalized_data['Subject'] = subject
    session_z_scores = session_z_scores.append(normalized_data)
    