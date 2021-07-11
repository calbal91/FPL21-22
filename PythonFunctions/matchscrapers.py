#Standard data manipulations
import pandas as pd
import numpy as np
from datetime import date
from datetime import datetime
import time

#SQL
import sqlite3
#Including custom functions, stored elsewhere in the repo
from PythonFunctions.sqlfunctions import *

#We need some SQL functionality for the classes
#Connect to the database 'fpl.db' (fantasy premier league!)
conn = sqlite3.connect('Data/20_21fpl.db')
#Instantiate a cursor
c = conn.cursor()
df_teams = sql('SELECT * FROM teams_basic', c).head(20)
df_players = sql('SELECT * FROM players_basic', c)
df_matches = sql('SELECT * FROM matches_basic', c)


#Webscraping libraries
import requests
from splinter import Browser
from bs4 import BeautifulSoup
import time
from datetime import datetime

#For text manipulation
import unicodedata


#Set up a browser for scraping
executable_path = {"executable_path": "/Users/callumballard/Documents/Python/FPL20-21/geckodriver"}

#Uncomment below to initiate browser
browser = Browser("firefox", **executable_path, headless=False)


#We should create a function that will remove accents from player names
#e.g. "à" should become "a", and so forth. This will help with commentary
#recognition later...
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


#MATCH SCRAPER
#_____________________________________________________________

def get_match_commentary_html(match, threshold = 'Lineups are announced and players are warming up.', browser=browser):
    
    '''
    Takes a 5-digit integer, referring to the code of the match on premier league website.
    
    Returns the full HTML, having scrolled to the bottom of the page.
    
    '''
    
    #Create the url for the match
    match_url = f'https://www.premierleague.com/match/{match}'

    #Initiate a splinter instance of the URL
    browser.visit(match_url)
    
    #Initiate a 'first content' variable. This will allow us to identify when the
    #scrolling has reached the bottom of the page
    first_content = ''

    #Have a while loop that says, so long as the first_content variable isn't the
    #standard first piece of commentary that we see in the HTLM, keep scrolling down
    while first_content != threshold:
        browser.execute_script("window.scrollTo(10000, document.body.scrollHeight);")
        soup = BeautifulSoup(browser.html, 'html.parser')
        innerContent = soup.findAll('div',class_="innerContent")
        #This condition just makes sure we don't get an error on the first loop
        if len(innerContent) > 0:
            first_content = soup.findAll('div',class_="innerContent")[-1].get_text()
        browser.execute_script("window.scrollTo(100, -document.body.scrollHeight);")
    
    #Return the full HTML soup for analysis
    return soup


def get_commentary(match, threshold = 'Lineups are announced and players are warming up.'):
    
    '''
    Takes a 5-digit integer, referring to the code of the match on premier league website.
    
    Returns a list of match events, with the minutes in which they took place
    '''
    #get the html soup using function
    html = get_match_commentary_html(match, threshold = threshold)
    
    #create two lists for events and minutes each event happened
    events = [i.get_text() for i in html.findAll('div',class_='innerContent')]
    minutes = [i.get_text().replace(' ','').replace("'","")
               for i in html.findAll('div',class_='cardMeta')]
    
    #merge the minutes and events lists
    commentary = [remove_accents(f"{minutes[i]}. {events[i]}") for i in range(len(events))]    
    
    return commentary



def get_match_lineup_html(match):
    
    '''
    Returns the html for the line up page of the given match
    
    '''
    
    browser.visit(f'https://www.premierleague.com/match/{match}')
    #click on the 'line ups' tab to load that html
    browser.find_by_tag('li[class="matchCentreSquadLabelContainer"]').click()
    return BeautifulSoup(browser.html, 'html.parser')



def lineup_clean(player):
    #strip the strings so that we only get player names
    return player.split(
        'Yellow Card')[0].split(
        'Red Card')[0].split(
        'Substitution')[0].split(
        'Goal')[0].split(
        'Pen.')[0].split(
        'Own ')[0]



def get_match_players(match):
  
    '''
    Returns a dictionary of players who were either starters or substitutes
    for the home or away team in the match
    
    '''
    soup = get_match_lineup_html(match)
    
    #get the team names
    home_long = soup.findAll('span',class_='long')[0].get_text()
    home_short = soup.findAll('span',class_='short')[0].get_text()
    away_long = soup.findAll('span',class_='long')[1].get_text()
    away_short = soup.findAll('span',class_='short')[1].get_text()
   
    #get the player names, removing accents
    players = [remove_accents(lineup_clean(i.get_text()))
               for i in soup.findAll('span',class_='name')[20:]]
    
    #sort these into sub-groups
    home_starts = players[:11]
    home_subs = players [11:18]
    away_starts = players [18:29]
    away_subs = players[29:]
    
    return {'HomeTeam': home_long,
            'HomeStarts': home_starts,
            'HomeSubs': home_subs,
            'AwayTeam': away_long,
            'AwayStarts': away_starts,
            'AwaySubs': away_subs}



def get_match_stats_html(match, browser=browser):
    
    '''
    Returns the html for the stats page of the given match
    
    '''
    
    browser.visit(f'https://www.premierleague.com/match/{match}')
    #click on the 'line ups' tab to load that html
    browser.find_by_tag('li[data-tab-index="2"]').click()
    return BeautifulSoup(browser.html, 'html.parser')



def get_match_stats(match):
    
    '''
    Takes a match ID and Returns a dictionary of dictionaries,
    describing aggregate team stats for home and away teams in the match
    
    '''
    html = get_match_stats_html(match)
    
    score = html.findAll('div',class_='score fullTime')[0].get_text().split('-')
    
    stats_table = [i.get_text() for i in html.findAll('td')]

    home_stats = {stats_table[3*i + 1]:stats_table[3*i]
                  for i in range(int(len(stats_table)/3))}
    
    home_stats['Goals'] = score[0]

    away_stats = {stats_table[3*i + 1]:stats_table[3*i + 2]
                  for i in range(int(len(stats_table)/3))}
    
    away_stats['Goals'] = score[1]
    
    gameweek = html.findAll('div',class_='current')[0].get_text(
    ).split('\n')[-2][3:]

    return {'GameWeek':gameweek,
            'HomeStats':home_stats,
            'AwayStats':away_stats}



def get_full_match_info(match):
    
    '''
    Returns the line ups and match commentary for a given match
    '''
    #Break out gameweek from the match_stats dictionary
    match_stats = get_match_stats(match)
    
    gameweek = match_stats['GameWeek']
    
    stats = {'HomeStats':match_stats['HomeStats'],
             'AwayStats':match_stats['AwayStats']}
    
    return {'MatchID':match,
            'GameWeek':int(gameweek),
            'Players':get_match_players(match),
            'Events':get_commentary(match),
            'Stats':stats}






#FIXTURES
#______________________________________________________________

def fixture_detail(match):
    '''
    Takes a match code and returns a single row datafrmae showing
    the match id, the date, the gameweek, and the home and away teams
    '''
    
    #Send the splinter instance of the URL
    match_url = f'https://www.premierleague.com/match/{match}'
    browser.visit(match_url)
    #Let it load!
    time.sleep(2)

    #Get the HTML
    html = BeautifulSoup(browser.html, 'html.parser')
    
    #Get the date of the match
    try:
        date_html = html.findAll('div',class_='matchDate')[0].get_text()
        date = datetime.strptime(date_html, '%a %d %b %Y').strftime("%Y-%m-%d")
    except:
        date = 'TBC'
    
    #Get the gameweek
    gameweek = html.findAll('div',class_='long')[0].get_text().replace('Matchweek ','')
    
    #Get the home and away teams
    home = html.findAll('div',class_='team home')[0].findAll(
        'span',class_='long')[0].get_text()
    away = html.findAll('div',class_='team away')[0].findAll(
        'span',class_='long')[0].get_text()
    
    columns = ['MatchID','GameWeek','Date','HomeTeam','AwayTeam']
    
    return pd.DataFrame({'MatchID':[match],
            'GameWeek':[gameweek],
            'Date':[date],
            'HomeTeam':[home],
            'AwayTeam':[away]}, columns = columns)


def fixture_details(matches):
    '''
    Takes a list of match codes and returns a dataframe showing
    the match id, the date, the gameweek, and the home and away teams    
    '''
    
    #Instantiate a dataframe
    columns = ['MatchID','GameWeek','Date','HomeTeam','AwayTeam']
    temp_df = pd.DataFrame(columns=columns)
    
    for i in matches:
        try:
            new_row = fixture_detail(i)
            temp_df = pd.concat([temp_df, new_row])
        except:
            pass
        
    temp_df.reset_index(drop=True, inplace=True)
        
    return temp_df



def df_matches_constructor():
    '''
    Generates a full dataframe of matches
    '''
    
    df = pd.DataFrame()
    
    for i in range(58896, 59276):
        
        browser.visit(f'https://www.premierleague.com/match/{i}')
        time.sleep(1.5)
        
        html = BeautifulSoup(browser.html, 'html.parser')
        
        try:
            date = html.findAll('div',class_="matchDate")[0].get_text()[4:]
            date = datetime.strptime(date, '%d %b %Y').strftime("%Y-%m-%d")

        except:
            date = 'TBC'            
       
        try:
            gameweek = int(html.findAll('div',class_="long")[0].get_text().replace('Matchweek ','')) 
            if date == 'TBC' and gameweek == 38:
                gameweek = 'TBC'
            
        except:
            gameweek = 'TBC'
            
        home = html.findAll('span',class_="long")[0].get_text()
        away = html.findAll('span',class_="long")[1].get_text()

        match_ids = [i,i]
        dates = [date,date]
        teams = [home,away]
        oppositions = [away,home]
        gameweeks = [gameweek,gameweek]

        new_rows = pd.DataFrame({
            'MatchID':match_ids,
            'GameWeek':gameweeks,
            'Date':dates,
            'Team':teams,
            'Opposition':oppositions,
            'Home':['Home','Away']
        })
        
        df = pd.concat([df, new_rows])
        
    return df.reset_index(drop=True)



#MATCH CLASS
#__________________________________________________________

#Note - we have some players who are referred to differently in the
#line up, vs the commentary. We need to correct this in the match
#line ups now to save us some bother later on...

def ProblemChildReplacer(text):
    '''
    Takes a string (text) and checks if its contains an
    entry in the dictionary of problem names. If so,
    then it replaces with the key of that player's name.
    '''
    problem_children = {
        'Joseph Willock':'Joe Willock',
        'Ki Sung-Yueng':'Ki Sung-yueng' }
    
    for name in list(problem_children.keys()):
        if name in text:
            text = text.replace(name,problem_children[name])
            
    return text
    

class Match(object):
    
    def __init__(self, match):
        #Record of match ID
        self.match_id = int(match['MatchID'])
        self.game_week = int(match['GameWeek'])
        
        #Team names for a given match
        self.home_team = match['Players']['HomeTeam']
        self.away_team = match['Players']['AwayTeam']
        self.teams = [self.home_team, self.away_team]
        
        #Player lists for a given match
        self.home_starts = [ProblemChildReplacer(i)
                            for i in match['Players']['HomeStarts']]
        self.home_subs = [ProblemChildReplacer(i)
                            for i in match['Players']['HomeSubs']]
        self.away_starts = [ProblemChildReplacer(i)
                            for i in match['Players']['AwayStarts']]
        self.away_subs = [ProblemChildReplacer(i)
                            for i in match['Players']['AwaySubs']]
        
        self.starts = self.home_starts + self.away_starts
        self.subs = self.home_subs + self.away_subs
        
        self.home_players = self.home_starts + self.home_subs
        self.away_players = self.away_starts + self.away_subs
                
        self.players = self.home_players + self.away_players
        
        
        #Stats for a given match
        self.stats = match['Stats']
        self.home_stats = match['Stats']['HomeStats']
        self.away_stats = match['Stats']['AwayStats']    
        
        #Events for a given match
        self.events = list(map(lambda x: ProblemChildReplacer(x),
                               match['Events']))

        #Shots
        self.goals = list(filter(lambda x: ('Goal!' in x) and ('Own Goal' not in x), self.events))
        self.shots_missed = list(filter(lambda x: 'Attempt missed' in x, self.events))
        self.shots_blocked = list(filter(lambda x: 'Attempt blocked' in x, self.events))
        self.shots_saved = list(filter(lambda x: ('Attempt saved' in x) or
                                       ('Penalty saved' in x), self.events))
        self.woodwork = list(filter(lambda x: ' hits the ' in x, self.events))
        self.own_goals = list(filter(lambda x: 'Own Goal' in x, self.events))
        
        #Penalties
        self.pens_awarded = list(filter(lambda x: 'foul in the penalty area' in x, self.events))
        self.pens_saved = list(filter(lambda x: 'Penalty saved' in x, self.events))
        
        #Assists
        self.assists = list(filter(lambda x: 'Assisted by ' in x, self.events))
        
        #Fouls
        self.fouls = list(filter(lambda x: ('Card!' in x) or ('. Foul by' in x), self.events))
                
        #Corners
        self.corners = list(filter(lambda x: '. Corner,' in x, self.events))
        
        #Substitutions
        self.substitutions = list(filter(lambda x: 'SubstitutionSubstitution' in x, self.events))
    
    
    def player_minutes(self):

        '''
        Returns a dataframe of minutes played by
        each player in the match
        '''

        #Declare the starting players and subs.
        #Create an initial dataframe, assuming 90 minutes for starts,
        #and 0 minutes for subs
        starts = pd.DataFrame({'Player':self.starts,
                               'GameWeek':[self.game_week
                                           for i in range(len(self.starts))],
                               'Minutes':[90 for i in range(len(self.starts))]})
        subs = pd.DataFrame({'Player':self.subs,
                             'GameWeek':[self.game_week
                                         for i in range(len(self.subs))],
                             'Minutes':[0 for i in range(len(self.subs))]})
        df = pd.concat([starts,subs])


        #Iterate through all the match substitution events,
        #and update the player table accordingly...
        for i in self.substitutions:

            #Split the event string by 'full stop'
            event_split = i.split('. ')
            time = event_split[0]

            #Account for when substitutions happen in stoppage time
            if '+' in time:
                time = time.split('+')[0]

            #Convert time to integer
            time = int(time)

            #Split the player names in the last sentence
            player_split = event_split[-1].split(' replaces ')
            on = player_split[0]
            off = player_split[1][:-1]

            #Update the dataframe with the new, known minutes
            df.loc[df['Player'] == on, 'Minutes'] = 91-time
            df.loc[df['Player'] == off, 'Minutes'] = time

        return df
    
    
    
def get_matches(matches, verbose=False):
    
    '''
    Takes a list of match codes, then gets their data.
    Returns a list of dictionaries encompassing the match data.
    '''
    
    #Initiate an empty list to store them in
    match_list = []
    
    #Iterate through the match codes...
    for n, i in enumerate(matches):
        #Get the match information
        match = get_full_match_info(i)

        #Store it in the list
        match_list.append(match)
                
        if verbose==True:
            print(f'Stored match {n/len(matches)} (ID: {i})')
    
    return match_list


def match_objects(matches):
    
    '''
    Takes a list of match dictionaries. Returns a list of 
    match objects, instantiated from the dictionaries.
    '''
    
    match_list = [Match(i) for i in matches]
    
    return match_list



#EVENT CLASSES
#__________________________________________________________


class Event(object):
    
    #Each event has an original text, and a timestamp (which may be None, if full time event, etc.)
    def __init__(self, event_string):
        self.event_text = str(event_string)
        self.time = event_string.split('.')[0]
        

#Declare possible possible options for shots
shot_types = ['right footed shot', 'left footed shot', 'header', 'an attempt']

shot_positions = ['a difficult angle', 'a difficult angle and long range',
                  'long range', 'outside the box', 'the box',
                 'the six yard box', 'very close range', 'penalty', 'Penalty']

shot_sides = ['the centre', 'the left', 'the right']

miss_positions = ['to the left', 'to the right', 'the top left corner',
                  'the top right corner', 'high and wide to the left',
                  'high and wide to the right', 'just a bit too high', 'too high']

miss_situations = ['following a set piece situation', 'from a direct free kick',
                  'following a corner']

save_positions = ['top left corner', 'top centre of the goal', 'top right corner',
                  'bottom left corner', 'centre of the goal', 'bottom right corner']

woodworks = ['bar','hits the left post','hits the right post']

goal_positions = ['top left corner', 'high centre of the goal', 'top right corner',
                   'bottom left corner', 'centre of the goal', 'bottom right corner']

goal_situations = ['converts the penalty','from a free kick']


class Shot(Event):
    
    def __init__(self, event_string):
        super().__init__(event_string)
        self.shot_type = list(filter(lambda x: x in event_string, shot_types))[0]
        
        if ('more than' in event_string) or ('from a free kick' in event_string):
            self.shot_position = 'long range'
        else:
            self.shot_position = list(
                filter(lambda x: x in event_string, shot_positions))[0].lower()
        
        if 'very close range' in event_string:
            self.shot_side = 'N/A'
        else:
            #This will ensure that we don't confuse 'left side'/'right side'
            #with the miss/save positions, etc.
            if 'difficult angle' in event_string:
                if 'is saved' in event_string:
                    shot_side_text = event_string.split('is saved')[0]
                else:
                    shot_side_text = event_string.split('to the')[0]
            else:
                shot_side_text = event_string.split('box')[0]
                
            if (('Penalty missed!' in event_string) or
            ('converts the penalty' in event_string) or
            ('outside the box' in event_string) or
            ('more than 35 yards' in event_string)):
                self.shot_side = 'N/A'
            elif len([i for i in shot_sides if i in shot_side_text]) > 0:
                self.shot_side = [i for i in shot_sides if i in shot_side_text][0]
            else:
                self.shot_side = 'N/A'
    
    def player(self, players):
        text = self.event_text.split('Assisted')[0]
        return [i for i in players if i in text][0]
    
    def assisted_by(self, players):
        text = self.event_text.split('Assisted')
        if len(text) > 1:
            return [i for i in players if i in text[1]][0]
        else:
            return 'N/A'
    
    def for_team(self, teams):
        return [i for i in teams if i in self.event_text][0]

    def against_team(self, teams):
        return list(filter(lambda x: x not in
                           [[i for i in teams if i in self.event_text][0]],teams))[0]
    
class ShotMissed(Shot):
    def __init__(self, event_string):
        super().__init__(event_string)
        self.miss_position = [i for i in miss_positions if i in event_string][0]
        self.close = [i if i in event_string else 'not close' for i in ['close']][0]
        
        if len([i for i in miss_situations if i in event_string]) > 0:
            self.miss_situation = [i for i in miss_situations if i in event_string][0]
        else:
            self.miss_situation = 'N/A'

class ShotSaved(Shot):
    def __init__(self, event_string):
        super().__init__(event_string)
        self.save_position = [i for i in save_positions if i in event_string][0]

class ShotBlocked(Shot):
    def __init__(self, event_string):
        super().__init__(event_string)
        
class Woodwork(Shot):
    def __init__(self, event_string):
        super().__init__(event_string)
        self.woodwork_type = [i for i in woodworks if i in event_string][0]
                
class Goal(Shot):
    def __init__(self, event_string):
        super().__init__(event_string)
        self.goal_position = [i for i in goal_positions if i in event_string][0]

        if len([i for i in goal_situations if i in event_string]) > 0:
            self.goal_situation = [i for i in goal_situations if i in event_string][0]
        else:
            self.goal_situation = 'non-dead ball'
            
    #We need a different definition to assign teams given
    #the structure of the string for goal events
    def for_team(self, teams):
        text = self.event_text.split('.')[2]
        return [i for i in teams if i in text][0]
    
    def against_team(self, teams):
        text = self.event_text.split('.')[2]
        return list(filter(lambda x: x not in text,teams))[0]        

class OwnGoal(Event):
    
    def player(self, players):
        return [i for i in players if i in self.event_text][0]    
    
        
#Declare possible possible outcomes for assists
assist_outcomes = ['Attempt saved', 'Attempt blocked', 'Attempt missed', 'Goal!',
                   'hits the bar', 'hits the left post', 'hits the right post']

assist_types = ['following a set piece situation',
                'following a corner', 'following a fast break']


class Assist(Event):
    
    def __init__(self, event_string):
        super().__init__(event_string)
        self.outcome = list(filter(lambda x: x in event_string, assist_outcomes))[0]
        
        if len([i for i in assist_type if i in event_string]) > 0:
            self.assist_type = [i for i in assist_types if i in event_string][0]
        else:
            self.assist_type = 'N/A'
    
    def player(self, players):
        text = self.event_text.split('Assisted')[1]        
        return [i for i in players if i in text][0]


cards = ['Second yellow','Yellow','Red']
foul_offences = ['handball','bad foul']
    
class Foul(Event):
    
    def __init__(self, event_string):
        super().__init__(event_string)
        
        if len([i for i in cards if i in event_string]) > 0:
            self.card = [i for i in cards if i in event_string][0]
        else:
            self.card = 'none'
            
        if len([i for i in foul_offences if i in event_string]) > 0:
            self.offence = [i for i in foul_offences if i in event_string][0]
        else:
            self.offence = 'foul'            

    
    def player(self, players):
        return [i for i in players if i in self.event_text][0]

    
class Penalty(Event):
    
    def __init__(self, event_string):
        super().__init__(event_string)
        
        
        
        
#SHOT TABLES
#___________________________________________________________

def strength(team):
    '''
    Returns the strength of the team, as defined by FPL
    '''
    
    return int(df_teams.loc[df_teams['CommentName']==team, 'Strength'].item())



def match_shots_missed(self):
    
    '''
    Takes in a Match object, and reuturns a dataframe of missed shots
    '''
    
    #extract required information from the match object
    match_id = self.match_id
    game_week = self.game_week
    match_players = self.players
    match_teams = self.teams    
    #create event objects out of the strings in the shots_missed attribute
    shots_missed = [ShotMissed(i) for i in self.shots_missed]
    
    #declare all the columns 
    cols = ['MatchID','GameWeek','Player','ForTeam','AgainstTeam','Time','ShotOutcome',
            'AssistedBy','ShotType','ShotPosition','ShotSide','MissPosition',
            'Close','MissSituation']
    
    #create an empty dataframe with the desired columns
    df_temp = pd.DataFrame(columns=cols)
    
    #go through and extract the different statistics for each event
    match = [match_id for i in shots_missed]
    gameweek = [game_week for i in shots_missed]
    players = [i.player(match_players) for i in shots_missed]
    forteams = [i.for_team(match_teams) for i in shots_missed]
    againstteams = [i.against_team(match_teams) for i in shots_missed]
    time = [i.time for i in shots_missed]
    outcome = ['Miss' for i in shots_missed]
    assisted = [i.assisted_by(match_players) for i in shots_missed]
    shottype = [i.shot_type for i in shots_missed]
    position = [i.shot_position for i in shots_missed]
    side = [i.shot_side for i in shots_missed]
    misspos = [i.miss_position for i in shots_missed]
    close = [i.close for i in shots_missed]
    misssit = [i.miss_situation for i in shots_missed]

    new_df = pd.DataFrame({'MatchID':match,
                           'GameWeek':gameweek,
                           'Player':players,
                           'ForTeam':forteams,
                           'AgainstTeam':againstteams,
                           'Time':time,
                           'ShotOutcome':outcome,
                           'AssistedBy':assisted,
                           'ShotType':shottype,
                           'ShotPosition':position,
                           'ShotSide':side,
                           'MissPosition':misspos,
                           'Close':close,
                           'MissSituation':misssit})

    df_temp = pd.concat([df_temp,new_df])
    
    df_temp['RelativeStrength'] = df_temp['ForTeam'].map(
        lambda x: strength(x)) - df_temp['AgainstTeam'].map(
        lambda x: strength(x))
    
    return df_temp

#Set the above function as a method for the Match class
Match.shots_missed_table = match_shots_missed



def match_shots_saved(self):
    
    '''
    Takes in a Match object, and reuturns a dataframe of saved shots
    '''
    
    #extract required information from the match object
    match_id = self.match_id
    game_week = self.game_week
    match_players = self.players
    match_teams = self.teams
    
    #create event objects out of the strings in the shots_saved attribute
    shots_saved = [ShotSaved(i) for i in self.shots_saved]
    
    #declare all the columns 
    cols = ['MatchID','GameWeek','Player','ForTeam','AgainstTeam','Time',
            'ShotOutcome','AssistedBy','ShotType','ShotPosition',
            'ShotSide','SavePosition','Close']
    
    #create an empty dataframe with the desired columns
    df_temp = pd.DataFrame(columns=cols)
    
    #go through and extract the different statistics for each event
    match = [match_id for i in shots_saved]
    gameweek = [game_week for i in shots_saved]    
    players = [i.player(match_players) for i in shots_saved]
    forteams = [i.for_team(match_teams) for i in shots_saved]
    againstteams = [i.against_team(match_teams) for i in shots_saved]
    time = [i.time for i in shots_saved]
    outcome = ['Saved' for i in shots_saved]
    assisted = [i.assisted_by(match_players) for i in shots_saved]
    shottype = [i.shot_type for i in shots_saved]
    position = [i.shot_position for i in shots_saved]
    side = [i.shot_side for i in shots_saved]
    savepos = [i.save_position for i in shots_saved]
    close = ['close' for i in shots_saved]


    new_df = pd.DataFrame({'MatchID':match,
                           'GameWeek':gameweek,
                           'Player':players,
                           'ForTeam':forteams,
                           'AgainstTeam':againstteams,
                           'Time':time,
                           'ShotOutcome':outcome,
                           'AssistedBy':assisted,
                           'ShotType':shottype,
                           'ShotPosition':position,
                           'ShotSide':side,
                           'SavePosition':savepos,
                           'Close':close})

    df_temp = pd.concat([df_temp,new_df])
    
    df_temp['RelativeStrength'] = df_temp['ForTeam'].map(
        lambda x: strength(x)) - df_temp['AgainstTeam'].map(
        lambda x: strength(x))
    
    return df_temp

#Set the above function as a method for the Match class
Match.shots_saved_table = match_shots_saved




def match_shots_blocked(self):
    
    '''
    Takes in a Match object, and reuturns a dataframe of blocked shots
    '''
    
    #extract required information from the match object
    match_id = self.match_id
    game_week = self.game_week
    match_players = self.players
    match_teams = self.teams
    
    #create event objects out of the strings in the shots_saved attribute
    shots_blocked = [ShotBlocked(i) for i in self.shots_blocked]
    
    #declare all the columns 
    cols = ['MatchID','GameWeek','Player','ForTeam','AgainstTeam','Time',
            'ShotOutcome','AssistedBy','ShotType','ShotPosition',
            'ShotSide','Close']
    
    #create an empty dataframe with the desired columns
    df_temp = pd.DataFrame(columns=cols)
    
    #go through and extract the different statistics for each event
    match = [match_id for i in shots_blocked]
    gameweek = [game_week for i in shots_blocked]    
    players = [i.player(match_players) for i in shots_blocked]
    forteams = [i.for_team(match_teams) for i in shots_blocked]
    againstteams = [i.against_team(match_teams) for i in shots_blocked]
    time = [i.time for i in shots_blocked]
    outcome = ['Blocked' for i in shots_blocked]
    assisted = [i.assisted_by(match_players) for i in shots_blocked]
    shottype = [i.shot_type for i in shots_blocked]
    position = [i.shot_position for i in shots_blocked]
    side = [i.shot_side for i in shots_blocked]
    close = ['not close' for i in shots_blocked]

    new_df = pd.DataFrame({'MatchID':match,
                           'GameWeek':gameweek,
                           'Player':players,
                           'ForTeam':forteams,
                           'AgainstTeam':againstteams,
                           'Time':time,
                           'ShotOutcome':outcome,
                           'AssistedBy':assisted,
                           'ShotType':shottype,
                           'ShotPosition':position,
                           'ShotSide':side,
                           'Close':close})

    df_temp = pd.concat([df_temp,new_df])
    
    df_temp['RelativeStrength'] = df_temp['ForTeam'].map(
        lambda x: strength(x)) - df_temp['AgainstTeam'].map(
        lambda x: strength(x))
    
    return df_temp

#Set the above function as a method for the Match class
Match.shots_blocked_table = match_shots_blocked




def match_woodwork(self):
    
    '''
    Takes in a Match object, and reuturns a dataframe
    of shots that hit the post or bar
    '''
    
    #extract required information from the match object
    match_id = self.match_id
    game_week = self.game_week
    match_players = self.players
    match_teams = self.teams
    
    #create event objects out of the strings in the shots_saved attribute
    woodwork = [Woodwork(i) for i in self.woodwork]
    
    #declare all the columns 
    cols = ['MatchID','GameWeek','Player','ForTeam','AgainstTeam','Time',
            'ShotOutcome','WoodworkType','AssistedBy','ShotType',
            'ShotPosition','ShotSide','Close']
    
    #create an empty dataframe with the desired columns
    df_temp = pd.DataFrame(columns=cols)
    
    #go through and extract the different statistics for each event
    match = [match_id for i in woodwork]
    gameweek = [game_week for i in woodwork]
    players = [i.player(match_players) for i in woodwork]
    forteams = [i.for_team(match_teams) for i in woodwork]
    againstteams = [i.against_team(match_teams) for i in woodwork]
    time = [i.time for i in woodwork]
    outcome = ['Woodwork' for i in woodwork]
    shottype = [i.woodwork_type for i in woodwork]
    assisted = [i.assisted_by(match_players) for i in woodwork]
    shottype = [i.shot_type for i in woodwork]
    position = [i.shot_position for i in woodwork]
    side = [i.shot_side for i in woodwork]
    close = ['close' for i in woodwork]

    new_df = pd.DataFrame({'MatchID':match,
                           'GameWeek':gameweek,
                           'Player':players,
                           'ForTeam':forteams,
                           'AgainstTeam':againstteams,
                           'Time':time,
                           'ShotOutcome':outcome,
                           'WoodworkType':shottype,
                           'AssistedBy':assisted,
                           'ShotType':shottype,
                           'ShotPosition':position,
                           'ShotSide':side,
                           'Close':close})

    df_temp = pd.concat([df_temp,new_df])
    
    df_temp['RelativeStrength'] = df_temp['ForTeam'].map(
        lambda x: strength(x)) - df_temp['AgainstTeam'].map(
        lambda x: strength(x))    
    
    return df_temp

#Set the above function as a method for the Match class
Match.woodwork_table = match_woodwork



def match_goals(self):
    
    '''
    Takes in a Match object, and reuturns a dataframe of goals
    '''
    
    #extract required information from the match object
    match_id = self.match_id
    game_week = self.game_week
    match_players = self.players
    match_teams = self.teams
    
    #create event objects out of the strings in the shots_missed attribute
    goals = [Goal(i) for i in self.goals]
    
    #declare all the columns 
    cols = ['MatchID','GameWeek','Player','ForTeam','AgainstTeam','Time','ShotOutcome',
            'AssistedBy','ShotType','ShotPosition','ShotSide','GoalPosition',
            'Close','GoalSituation']
    
    #create an empty dataframe with the desired columns
    df_temp = pd.DataFrame(columns=cols)
    
    #go through and extract the different statistics for each event
    match = [match_id for i in goals]
    gameweek = [game_week for i in goals]
    players = [i.player(match_players) for i in goals]
    forteams = [i.for_team(match_teams) for i in goals]
    againstteams = [i.against_team(match_teams) for i in goals]
    time = [i.time for i in goals]
    outcome = ['Goal' for i in goals]
    assisted = [i.assisted_by(match_players) for i in goals]
    shottype = [i.shot_type for i in goals]
    position = [i.shot_position for i in goals]
    side = [i.shot_side for i in goals]
    close = ['close' for i in goals]
    goalpos = [i.goal_position for i in goals]
    goalsit = [i.goal_situation for i in goals]

    new_df = pd.DataFrame({'MatchID':match,
                           'GameWeek':gameweek,
                           'Player':players,
                           'ForTeam':forteams,
                           'AgainstTeam':againstteams,
                           'Time':time,
                           'ShotOutcome':outcome,
                           'AssistedBy':assisted,
                           'ShotType':shottype,
                           'ShotPosition':position,
                           'ShotSide':side,
                           'GoalPosition':goalpos,
                           'Close':close,
                           'GoalSituation':goalsit})

    df_temp = pd.concat([df_temp,new_df])
    
    df_temp['RelativeStrength'] = df_temp['ForTeam'].map(
        lambda x: strength(x)) - df_temp['AgainstTeam'].map(
        lambda x: strength(x))
    
    return df_temp

#Set the above function as a method for the Match class
Match.goals_table = match_goals



def match_shots(self):
    
    '''
    Takes a match object and produces a collated list of all shots in a dataframe
    '''
    
    #Create dataframes of the different shot types
    goals = self.goals_table()
    missed = self.shots_missed_table()
    blocked = self.shots_blocked_table()
    saved = self.shots_saved_table()
    woodwork = self.woodwork_table()
    
    #Create a list of these to iterate through
    shot_dfs = [goals, woodwork, blocked, saved, missed]
    
    #Identify the columns shared by these dfs
    columns = ['MatchID','GameWeek','Player',
               'ForTeam','AgainstTeam','RelativeStrength',
               'Time','ShotOutcome','AssistedBy','ShotType',
               'ShotPosition','ShotSide','Close']
    
    #Inititate a new dataframe with the appropriate columns
    df_temp = pd.DataFrame(columns = columns)
    
    #Iterate through the dfs and append the rows as required
    for i in shot_dfs:
        new_rows = i[columns]
        df_temp = pd.concat([df_temp,new_rows])
        
    df_temp.reset_index(inplace=True,drop=True)
    
    return df_temp

#Set the above function as a method for the Match class
Match.shots_table = match_shots



def combine_shot_tables(matches):
    
    '''
    Takes a list of match objects, and outputs a concatonated
    dataframe of all the shots taken in those matches.
    '''

    columns = ['MatchID','GameWeek','Player',
               'ForTeam','AgainstTeam','RelativeStrength',
               'Time','ShotOutcome','AssistedBy','ShotType',
               'ShotPosition','ShotSide','Close']
    
    #Inititate a new dataframe with the appropriate columns
    df_temp = pd.DataFrame(columns = columns)

    #Iterate through match objects...
    for match in matches:
        new_rows = match.shots_table()
        #And append thier shot tables to the dataframe
        df_temp = pd.concat([df_temp,new_rows])
    
    df_temp.reset_index(inplace=True, drop=True)
        
    #Make everything numeric
    df_temp = df_temp.apply(pd.to_numeric, errors='ignore')
    
    return df_temp


def shot_filter(df, player=None, event='shot', gameweeks=None,
                shot_outcomes=None, shot_positions=None,
                side=None, shot_type=None, close=None, team=None):
    
    '''
    Filters a shot dataframe according to inputs.
    
    Parameters:
    - player (str):
    - event (str):
    - gameweeks (list):
    - shot_outcomes (list):
    - shot_positions (list):
    - shot_side (list):
    - close (str):
    - team (str):
    
    '''
    
    #Extract all possible outcomes for each column    
    if gameweeks == None:
        gameweeks = list(range(max(df_shots['GameWeek'])+1))
        
    if shot_outcomes == None:
        shot_outcomes = df['ShotOutcome'].unique()
                    
    if shot_positions == None:
        shot_positions = df['ShotPosition'].unique()
        
    if shot_type == None:
        shot_type = df['ShotType'].unique()
    elif type(side) != list:
        shot_type = [shot_type]
        
    if side == None:
        side = df['ShotSide'].unique()
    elif type(side) != list:
        side = [side]
        
    if team == None:
        team = df['ForTeam'].unique()
    else:
        team = [team]
                        
    if close == None:
        close = ['close','not close']
    else:
        close = [close]
    
    #Now perform a big loc to filter as required
    df = df.loc[(df['GameWeek'].isin(gameweeks))
               & (df['ShotOutcome'].isin(shot_outcomes))
               & (df['ShotPosition'].isin(shot_positions))
               & (df['ShotType'].isin(shot_type))
               & (df['Close'].isin(close))
               & (df['ForTeam'].isin(team))
               & (df['ShotSide'].isin(side))]
    
    
    if player == None:
        player = df['Player'].unique()
    else:
        player = [player]
    
    #Filter on either shots or assists, depending on input
    if event == 'shot':
        return df.loc[df['Player'].isin(player)]
    elif event == 'assist':
        return df.loc[df['AssistedBy'].isin(player)]


def goals_in_week(df, player, event='shot', gameweek=None):
    
    '''
    Returns the number of goals that a given player
    scored / assisted in the gameweek
    '''
    
    df_temp = shot_filter(df, player, gameweeks = [gameweek],
                          event=event, shot_outcomes=['Goal'])
    
    return len(df_temp)



def shots_in_week(df, player, event='shot', side=None, gameweek=None):
    
    '''
    Returns the number of total shots that a given player
    hit / assisted in the gameweek
    '''
    if side != None:
        side = [side]
    
    df_temp = shot_filter(df, player, gameweeks = [gameweek],
                          event=event, side=side)    
    
    return len(df_temp)



def headers_in_week(df, player, event='shot', gameweek=None):
    
    '''
    Returns the number of total headers that a given player
    hit / assisted in the gameweek
    '''
    
    df_temp = shot_filter(df, player, gameweeks = [gameweek],
                          event=event, shot_type = 'header')    
    
    return len(df_temp)



def shots_close_in_week(df, player, event='shot', gameweek=None):
    
    '''
    Returns the number of close shots that a given player
    hit / assisted in the gameweek
    '''
    
    df_temp = shot_filter(df, player, gameweeks = [gameweek],
                          close='close', event=event)
    
    return len(df_temp)



def shots_on_target_in_week(df, player, event='shot', gameweek=None):
    
    '''
    Returns the number of total shots on target that a given player
    hit / assisted in the gameweek
    '''
    
    df_temp = shot_filter(df, player, gameweeks = [gameweek],
                          shot_outcomes=['Saved','Goal'],
                          event=event)
    
    return len(df_temp)



def shots_in_box_in_week(df, player, event='shot', gameweek=None):
    
    '''
    Returns the number of total shots in the box that a given player
    hit / assisted in the gameweek
    '''
    
    df_temp = shot_filter(df, player, gameweeks = [gameweek],
                          shot_positions = ['the box', 'the six yard box'],
                          event=event)
    
    return len(df_temp)



def player_gameweek_row(player, df, gameweek=None, verbose=True):
    
    '''
    Creates an aggregated view of a player's
    attacking performance in that gameweek
    '''
    if verbose==True:
        print(f'{player}, gameweek {gameweek}')
    
    for_team = df_players.loc[df_players['CommentName']==player]['Team'].item()
    
    against_team = shot_filter(team=for_team,
                               gameweeks=[gameweek],
                               df=df)['AgainstTeam'].mode().item()
    
    strength = shot_filter(team=for_team,
                           gameweeks=[gameweek],
                           df=df)['RelativeStrength'].mode().item()
    
    goals = [goals_in_week(df, player, gameweek=gameweek)]
    sot = [shots_on_target_in_week(df, player, gameweek=gameweek)]
    sib = [shots_in_box_in_week(df, player, gameweek=gameweek)]
    close = [shots_close_in_week(df, player, gameweek=gameweek)]
    shots = [shots_in_week(df, player, gameweek=gameweek)]
    headers = [headers_in_week(df, player, gameweek=gameweek)]
    shots_centre = [shots_in_week(df, player, gameweek=gameweek, side='the centre')]
    shots_left = [shots_in_week(df, player, gameweek=gameweek, side='the left')]
    shots_right = [shots_in_week(df, player, gameweek=gameweek, side='the right')]
    
    goal_ass = [goals_in_week(df, player, gameweek=gameweek,
                              event='assist')]
    sot_ass = [shots_on_target_in_week(df, player, gameweek=gameweek,
                                       event='assist')]
    sib_ass = [shots_in_box_in_week(df, player, gameweek=gameweek,
                                    event='assist')]
    close_ass = [shots_close_in_week(df, player, gameweek=gameweek,
                                 event='assist')]
    total_ass = [shots_in_week(df, player, gameweek=gameweek,
                             event='assist')]
    headers_ass = [headers_in_week(df, player, gameweek=gameweek,
                                   event='assist')]
    ass_centre = [shots_in_week(df, player, gameweek=gameweek,
                                event='assist', side='the centre')]
    ass_left = [shots_in_week(df, player, gameweek=gameweek,
                                event='assist', side='the left')]
    ass_right = [shots_in_week(df, player, gameweek=gameweek,
                                event='assist', side='the right')]
    
    
    df_temp = pd.DataFrame({'GameWeek':[gameweek],
                            'Player':[player],
                            'ForTeam': for_team,
                            'AgainstTeam': against_team,
                            'RelativeStrength': strength,
                            'Goals': goals,
                            'ShotsOnTarget': sot,
                            'ShotsInBox': sib,
                            'CloseShots': close,
                            'TotalShots': shots,
                            'Headers': headers,
                            'ShotsCentre': shots_centre,
                            'ShotsLeft': shots_left,
                            'ShotsRight': shots_right,
                            'GoalAssists': goal_ass,
                            'ShotOnTargetCreated': sot_ass,
                            'ShotInBoxCreated': sib_ass,
                            'CloseShotCreated': close_ass,
                            'TotalShotCreated': total_ass,
                            'HeadersCreated': headers_ass,
                            'CreatedCentre': ass_centre,
                            'CreatedLeft': ass_left,
                            'CreatedRight': ass_right})
    
    return df_temp



def df_player_games_extender(df, shot_df, verbose=True):
    
    '''
    Takes a player_games dataframe, and calculates then appends
    the required columns for shots and assists summary
    '''
    
    #Declare an empty dataframe, which we'll concatenate
    #to the player_games dataframe
    
    cols = ['Player','MatchID','GameWeek','Minutes','ForTeam','AgainstTeam',
            'RelativeStrength','Goals','ShotsOnTarget','ShotsInBox','CloseShots',
            'TotalShots','Headers','ShotsCentre','ShotsLeft','ShotsRight',
            'GoalAssists','ShotOnTargetCreated','ShotInBoxCreated',
            'CloseShotCreated','TotalShotCreated','HeadersCreated',
            'CreatedCentre','CreatedLeft','CreatedRight']
    
    df_temp = pd.DataFrame(columns = cols)
    
    #Iterate through rows of the player games dataframe
    for i in range(len(df)):
        #Include a try/except, in case teams missed gameweeks
        #e.g. Liverpool in gameweek 18
        try:
            #Create a row stub from the input dataframe
            row_stub = df.iloc[[i]].reset_index(drop=True)
            #Create the new stats that we'll attach to this stub
            player = df.iloc[i]['Player']
            gameweek = df.iloc[i]['GameWeek']
            match_id = pd.DataFrame({'MatchID':[shot_df['MatchID'][0]]})

            new_row = player_gameweek_row(player, df=shot_df, gameweek=gameweek, 
                                         verbose=verbose).iloc[:,2:]

            #Join the new data to the stub
            new_row = pd.concat([row_stub, match_id, new_row], axis=1)
            
            #And append to the grand output dataframe
            df_temp = pd.concat([df_temp, new_row], sort=False)
            
        except:
            pass
    
    df_temp.reset_index(drop=True,inplace=True)
    
    #Make everything numeric
    df_temp = df_temp.apply(pd.to_numeric, errors='ignore')
    df_temp = df_temp[cols]
    
    return df_temp



#TEAM LEVEL DATA
#_____________________________________________________________________________

def team_table_init(self):
    
    '''
    Takes a match object and outputs a dataframe of summary team-level
    stats from the match, with a line for each of the teams that played
    the match.
    '''
    
    #get required attributes from match object
    teams = self.teams
    stats = self.stats
    
    #extract basic information
    match_id = [self.match_id, self.match_id]
    for_team = [teams[0], teams[1]]
    against_team = [teams[1], teams[0]]
    game_week = [self.game_week, self.game_week]
    home = ['Home','Away']
    
    #calculate relative strength
    relative_strength = [strength(teams[0])-strength(teams[1]),
                         strength(teams[1])-strength(teams[0])]
    
    #extract information from stats tables
    possession = [stats[i]['Possession %'] for i in stats]
    goals = [stats[i]['Goals'] for i in stats]
    sot = [stats[i]['Shots on target'] for i in stats]
    shots = [stats[i]['Shots'] for i in stats]
    goals_conceded = [goals[1],goals[0]]
    shots_conceded = [shots[1],shots[0]]
    touches = [stats[i]['Touches'] for i in stats]
    passes = [stats[i]['Passes'] for i in stats]
    tackles = [stats[i]['Tackles'] for i in stats]
    clearances = [stats[i]['Clearances'] for i in stats]
    corners = [stats[i]['Corners'] for i in stats]
    fouls = [stats[i]['Fouls conceded'] for i in stats]
    
    #Games with no cards have no yellow card heading in the table
    try:
        yellows = [stats[i]['Yellow cards'] for i in stats]
    except:
        yellows = [0,0]
        
    #Games with no offsides have no yellow card heading in the table
    try:
        offsides = [stats[i]['Offsides'] for i in stats]
    except:
        offsides = [0,0]

    
    df_temp = pd.DataFrame({'MatchID': match_id,
                            'ForTeam': for_team,
                            'AgainstTeam': against_team,
                            'RelativeStrength': relative_strength,
                            'GameWeek': game_week,
                            'Home': home,
                            'Possession': possession,
                            'Goals': goals,
                            'ShotsOnTarget': sot, 
                            'TotalShots': shots,
                            'GoalsConceded':goals_conceded,
                            'ShotsConceded':shots_conceded,
                            'Touches': touches,
                            'Passes': passes,
                            'Tackles': tackles,
                            'Clearances': clearances,
                            'Corners': corners,
                            'Offsides': offsides,
                            'YellowCards': yellows,
                            'FoulsConceded': fouls})
    
    #Make everything numeric
    df_temp = df_temp.apply(pd.to_numeric, errors='ignore')    
    
    return df_temp


#We can now embed this function into the Matches class,
#so that we can call it more easily in future

Match.stats_table = team_table_init




def team_table_extended(match, df_ref):
    '''
    Takes a match object, and returns a full table of
    statistics for the home and away teams.
    
    Also takes 'df_ref', a dataframe of shots at a
    player/match level, which gets aggregated up.
    
    Includes a full breakdown of shot types.
    '''
    
    #Create an initial dataframe with basic stats
    df_init = match.stats_table()
    
    #Isolate the gameweek and the two teams
    home = match.home_team
    away = match.away_team
    gw = match.game_week
        
    #State the required columns
    required_columns = ['ShotsInBox','CloseShots','Headers',
                        'ShotsCentre','ShotsLeft','ShotsRight']
    
    #Create the aggregated view of the reference dataframe (for 'for' statistics)
    df_ref_agg_for = df_ref.groupby(['ForTeam','GameWeek']).sum()
    
    #Isolate the required teams for the required gameweek
    df_for = df_ref_agg_for.loc[[(home,gw),(away,gw)], required_columns]
    
    #Reset index to flatten the multi-index that results
    df_for.reset_index(drop=True, inplace=True)
    
    #Concatenate with the match stats dataframe
    df_init = pd.concat([df_init, df_for], axis=1)
    
    #Flip the extra shots statistics to get into 'shots against' form
    df_for.index = [1,0]
    #And rename the columns    
    new_columns = [f'{i}Conceded' for i in required_columns]
    df_for.columns = new_columns
    
    #Concatenate with the match stats dataframe
    df_init = pd.concat([df_init, df_for], axis=1)
    
    return df_init



def team_table_aggregator(matches, df_ref):
    '''
    Take a list of match objects, get full statistics, 
    and combine all stats into single table
    '''
    
    #Declare columns of the eventual table, and instantiate dataframe
    columns = ['MatchID', 'ForTeam', 'AgainstTeam', 'RelativeStrength', 'GameWeek',
       'Home', 'Possession', 'Goals', 'ShotsOnTarget', 'TotalShots',
       'GoalsConceded', 'ShotsConceded', 'Touches', 'Passes', 'Tackles',
       'Clearances', 'Corners', 'Offsides', 'YellowCards', 'FoulsConceded',
       'ShotsInBox', 'CloseShots', 'Headers', 'ShotsCentre', 'ShotsLeft', 'ShotsRight',
       'ShotsInBoxConceded', 'CloseShotsConceded', 'HeadersConceded',
       'ShotsCentreConceded', 'ShotsLeftConceded', 'ShotsRightConceded']
    
    df_temp = pd.DataFrame(columns=columns)
    
    #Iterate through matches...
    for i in matches:
        try:
            #Create statistics for that match
            new_rows = team_table_extended(i, df_ref=df_ref)
            #and append to dataframe
            df_temp = pd.concat([df_temp, new_rows])
        except:
            print('Not Recorded', i.match_id)
        
    df_temp.reset_index(drop=True, inplace=True)
    
    #Make everything numeric
    df_temp = df_temp.apply(pd.to_numeric, errors='ignore')
        
    return df_temp




#CORE UPDATER
#________________________________________________________________


#For the player detail dataframe, we will need to
#build out a function that deals with irregular game weeks

def PlayerBasicsGenerator(matches, df_players):
    '''
    Takes a list of match objects, and the standard dataframe of
    players (from SQL database) then creates a dataframe of
    all the players assocated with the teams that played in those matches
    and how long they played in each match (includes non-matchday-squad players)
    '''
    
    df_temp = pd.DataFrame(columns=['Player','GameWeek','Minutes'])
    
    for i in matches:
        gameweek = i.game_week
        teams = i.teams
        minutes = i.player_minutes()
        
        #Isolate all players in teams
        required_players = df_players.loc[df_players['Team'].isin(teams)]
        required_players = required_players[['CommentName']]
        required_players.columns = ['Player']
        
        #Join with the minutes dataframe
        merged_df = pd.merge(required_players, minutes, how='outer')
        
        #Fill in the missing gameweeks/minutes with 0
        merged_df['GameWeek'] = gameweek
        merged_df.loc[merged_df['Minutes'].isna(), 'Minutes'] = 0
        
        #Change minutes back to integer
        merged_df['Minutes'] = merged_df['Minutes'].astype('int64')
        
        #Add this to the temporary dataframe
        df_temp = pd.concat([df_temp, merged_df])
        
    return df_temp



def suggested_match_ids():
    stored_matches = sql('SELECT * FROM team_matches_detail', c)
    stored_ids = stored_matches['MatchID'].unique()
    
    df_temp = df_matches[['MatchID','Date']]
    df_temp['Date'] = df_temp['Date'].map(lambda x: pd.to_datetime(x.replace('TBC','')))
    
    date_today = datetime.combine(date.today(), datetime.min.time())
    
    played_ids = df_temp.loc[df_temp['Date']<=date_today, 'MatchID']
    played_ids = played_ids.unique()
    
    return [i for i in played_ids if i not in stored_ids]



def CoreDataUpdater(matches, cursor, connection, verbose=True):
    '''
    Takes a list of match codes, then updates the following SQL tables:
        - ShotsDetail
        - PlayerMatchesDetail
        - TeamMatchesDetail
    The function does this on a match by match basis (there is a risk that the
    scraping for a particular match fails, so if this was not the case,
    all work that has not been uploaded to SQL database would otherwise be lost).
    '''
    
    #Check that we have a list of matches
    if type(matches) != list:
        matches = [matches]
    
    #Iterate through the matches one at a time
    for i in matches:
        #Have everything in a try/except in case match has not been played yet
        try:
            #Scrape the webpage for that match and create a match object
            match_scrape = get_matches([i], verbose=verbose)[0]
            match_object = Match(match_scrape)
            if verbose==True:
                print(f'Match {i} object successfully instantiated')

            #Create the shot detail dataframe for that match
            temp_shot_detail_df = combine_shot_tables([match_object])
            if verbose==True:
                print(f'Match {i} shot detail dataframe successfully created')

            #Upload to sql...
            populate_sql_from_dataframe(temp_shot_detail_df,
                                        'shots_detail', cursor)

            #Create the player matches detail dataframe
            #Firstly, we need to create a simple player games table for the match
            temp_player_detail_df = PlayerBasicsGenerator([match_object], df_players)

            #Then we use the extender to populate
            temp_player_detail_df = df_player_games_extender(temp_player_detail_df,
                                                             shot_df = temp_shot_detail_df,
                                                             verbose=False)
            if verbose==True:
                print(f'Match {i} player detail dataframe successfully created')

            #Upload to sql
            populate_sql_from_dataframe(temp_player_detail_df, 'player_matches_detail', cursor)

            #Try to create the team dataframe - this can fail if
            #doesn't 'click' on the stats tab properly
            try:
                #Create team dataframe
                temp_team_detail_df = team_table_extended(match_object,
                                                          df_ref=temp_player_detail_df)
                if verbose==True:
                    print(f'Match {i} team detail dataframe successfully created')
                #Upload to sql
                populate_sql_from_dataframe(temp_team_detail_df,
                                            'team_matches_detail', cursor)
            except:
                print(f'\nFAILURE: Match {i} team detail dataframe NOT created\n')

            #Commit sql changes
            connection.commit()
            if verbose==True:
                print(f'Match {i} SQL entries committed')
        except:
            print(f'\nFAILURE: Match {i} failed to scrape - may not have been played yet\n')

            
            
def MatchSweeper(cursor, connection, verbose=True):
    
    '''
    Looks up matches that should be in the database, but aren't.
    Attempts to perform the core updater on these matches.
    '''
    
    temp_df = sql('SELECT * FROM team_matches_detail', c)
    matchids = list(temp_df['MatchID'].unique())

    missing_matches = []

    for i in range(min(matchids),max(matchids)+1):
        if i not in matchids:
            missing_matches.append(i)
    
    print(f'Attempting to scrape {missing_matches}')
            
    CoreDataUpdater(missing_matches, cursor, connection, verbose=verbose)