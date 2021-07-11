#Standard data manipulations
import pandas as pd
import numpy as np
import datetime

#SQL
import sqlite3
#Including custom functions, stored elsewhere in the repo
from PythonFunctions.sqlfunctions import *
from PythonFunctions.apicallers import *


#We need some SQL functionality for the classes
#Connect to the database 'fpl.db' (fantasy premier league!)
conn = sqlite3.connect('Data/20_21fpl.db')

#Instantiate a cursor
c = conn.cursor()
df_teams = sql('SELECT * FROM teams_basic', c).head(20)
df_players = sql('SELECT * FROM players_basic', c)
df_matches = sql('SELECT * FROM matches_basic', c)

#Create a dataframe of all known shots
shots_19_20 = sql('select * from shot_detail_19_20', c)
shots_20_21 = sql('select * from shots_detail', c)

df_all_shots = pd.concat([shots_19_20, shots_20_21])



#We now need a few functions that will calculate our XG and XGA metrics

#Create some custom columns for our shot detail dataframe.
def solo(x):
    if x=='N/A':
        return 'Solo'
    else:
        return 'Assisted'
    
def central(x):
    if x=='the centre':
        return 'Central'
    else:
        return 'NonCentral'

def strike(x):
    if x=='header':
        return 'Header'
    else:
        return 'Strike'

#Turn ShotPosition into camel case
def camel(x):
    x = x.title()
    return x.replace(' ', '')


def shot_classifier(df):
    '''
    takes a shot_details dataframe, and adds a new column that
    defines what kind of shot it was.
    '''
    
    df['Solo'] = df['AssistedBy'].map(solo)
    df['Central'] = df['ShotSide'].map(central)
    df['Strike'] = df['ShotType'].map(strike)
    df['ShotPosition'] = df['ShotPosition'].map(camel)
    
    df['ShotClass'] = df['ShotPosition'] + df['Solo'] + df['Central'] + df['Strike']
    
    #Merge some categories together and otherwise tidy
    df['ShotClass'] = df['ShotClass'].map(lambda x: 'Penalty' if x[:3]=='Pen' else x)
    df['ShotClass'] = df['ShotClass'].map(lambda x: x.replace('Central','') if x[:4]=='Very' else x)
    df['ShotClass'] = df['ShotClass'].map(lambda x: 'LongRange' if x[:4]=='Long' else x)
    df['ShotClass'] = df['ShotClass'].map(lambda x: x.replace('Solo','').replace('Assisted','')
                                          if 'Header' in x else x)
    
    return df



def xg_prob_constructor(df=df_all_shots):
    
    '''
    Takes a shot_df and calculates the probability
    that each type of shot results in a goal (returns a dataframe
    with these statistics).
    '''
    
    #construct the shot table
    df_shots = shot_classifier(df)
    
    #Get a count of each shot type
    df_shots = df.groupby('ShotClass').count()[['Player']]
    df_shots.columns = ['Total']

    #Get a count of the shots on target / goals scored
    df_shots['OnTarget'] = df.loc[df['ShotOutcome'].isin(['Goal','Saved'])].groupby(
        'ShotClass').count()[['Player']]
    df_shots['Goals'] = df.loc[df['ShotOutcome']=='Goal'].groupby('ShotClass').count()[['Player']]

    df_shots.fillna(0, inplace=True)

    #Goal ratio
    df_shots['TotalOnTarget'] = df_shots['OnTarget'] / df_shots['Total']
    df_shots['TotalXG'] = df_shots['Goals'] / df_shots['Total']
    df_shots['OnTargetXG'] = df_shots['Goals'] / df_shots['OnTarget']
    df_shots.fillna(0, inplace=True)
    
    return df_shots


#Create a stock 
df_xg = xg_prob_constructor(df=df_all_shots)



def xg_col_constructor(df, df_xg=df_xg):
    
    '''
    Takes a shot dataframe, df, and a dataframe of shot classes and their
    associated XGs, df_xg (as created by xg_prob_constructor)
    and creates new columns about the XG of each shot
    '''
    
    #Identify the shot type of each
    df = shot_classifier(df)
    
    #Create a blank list
    xg_column = []
    
    #Iterate through each shot
    for row in df.itertuples():
        row_outcome = row.ShotOutcome
        row_class = row.ShotClass

        if row_outcome in ['Goal', 'Saved']:
            row_xg = df_xg.loc[row_class, 'OnTargetXG']
        else:
            row_xg = df_xg.loc[row_class, 'TotalXG']

        xg_column.append(row_xg)

    df['XG'] = xg_column
    
    return df


def df_pm_generator():
    '''
    Generates a player matches dataframe with XG, XA, and XGI columns
    '''
    
    #Get player matches detail dataframe, and set index for joining
    df_pm = sql('select * from player_matches_detail',c).set_index(['MatchID','Player'], drop=True)
    
    #Create an XG view of shots
    temp_xg = xg_col_constructor(sql('select * from shots_detail', c))
    
    #Goals
    df_pm['XG'] = temp_xg.groupby(['MatchID','Player']).sum()[['XG']]
    #Assists
    df_pm['XA'] = temp_xg.groupby(['MatchID','AssistedBy']).sum()[['XG']]

    #Fill NAs with 0s
    df_pm.fillna(0, inplace=True)
    
    #Calculate goal Involvement
    df_pm['XGI'] = df_pm['XG'] + df_pm['XA']
    
    df_pm.reset_index(inplace=True)
    
    #Add player positions
    df_pm = pd.merge(df_pm, df_players[['CommentName','Position']],
                     how='left', left_on = 'Player',
                     right_on = 'CommentName').drop('CommentName', axis=1)
    
    return df_pm


def df_tm_generator():
    '''
    Generates a team matches dataframe with XG, XA, and XGI columns
    '''
    
    #Get team matches detail dataframe, and set index for joining
    df_tm = sql('select * from team_matches_detail', c).drop('TableIndex', axis=1)
    
    #Generate a player detail dataframe, with the XG stats 
    df_pm = df_pm_generator()
    
    #Groupby to get the total team stats for XG and XGC
    df_txg = df_pm.groupby(['MatchID','ForTeam']).sum()[['XG']].reset_index()
    df_txg.columns = ['MatchID', 'ForTeam', 'XG']

    df_txgc = df_pm.groupby(['MatchID','AgainstTeam']).sum()[['XG']].reset_index()
    df_txgc.columns = ['MatchID', 'ForTeam', 'XGC']
    
    #Merge XG and XGC together
    df_txg = pd.merge(df_txg, df_txgc, on=['MatchID','ForTeam'])
    
    #Merge XG/XGC stats onto the full team data
    return pd.merge(df_tm, df_txg, on=['MatchID','ForTeam'])



def api_stat_generator():
    
    '''
    Generates a table of stats that can only be accessed through the FPL API
    '''
    
    #Generate a basic API stat table
    api_stats = PlayersAPIStats(list(df_players['PlayerID']))
    
    #Merge it with the players table to get more data
    api_stats = pd.merge(api_stats, df_players[['PlayerID','CommentName','Team']], on='PlayerID')
    
    #Merge again to get the match ID data, so that we can join it later
    api_stats = pd.merge(api_stats, df_matches[['MatchID','Date','Team']],
                         how='left', on=['Date','Team'])
    
    #Drop some columns
    api_stats = api_stats[['MatchID', 'Date', 'CommentName', 'BPS',
                           'CleanSheet', 'MinutesPlayed', 'NetTransfersIn',
                           'Points', 'Price', 'Saves', 'SelectedBy']]
    
    #And rename some...
    api_stats.columns = ['MatchID', 'Date', 'Player', 'BPS',
                         'CleanSheet', 'MinutesPlayed', 'NetTransfersIn',
                         'Points', 'Price', 'Saves', 'SelectedBy']
    
    return api_stats