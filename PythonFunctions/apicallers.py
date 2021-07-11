#Standard data manipulations
import pandas as pd
import numpy as np

#Webscraping libraries
import requests

#For text manipulation
import unicodedata


#TABLE GENERATION WITH API CALLS
#________________________________________________________________________________________



#We have a list of teams and positions taken from site commentary...
teams = ['Arsenal', 'Aston Villa', 'Brighton and Hove Albion',
         'Burnley', 'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leicester City',
         'Leeds United', 'Liverpool', 'Manchester City', 'Manchester United', 'Newcastle United',
         'Sheffield United', 'Southampton', 'Tottenham Hotspur', 'West Bromwich Albion',
         'West Ham United', 'Wolverhampton Wanderers']

#Create a dictionary where the keys are the names in the df_player dictionary,
    #and the corresponding values are the names mentioned in match commentary
player_name_key = {
    'Fabio Henrique Fabinho':'Fabinho',
    'Maximillian Aarons':'Max Aarons',
    'Alex Chamberlain':'Alex Oxlade-Chamberlain',
    'Johann Berg Gudmundsson':'Johann Gudmundsson',
    'Cedric':'Cedric Soares',
    'Andre Filipe Andre Gomes':'Andre Gomes',
    'Benjamin Chilwell':'Ben Chilwell',
    'Ricardo Domingos Pereira':'Ricardo Pereira',
    'Rui Pedro Patricio':'Rui Patricio',
    'Ruben Diogo Neves':'Ruben Neves',
    'Jonathan Jonny':'Jonny',
    'Joao Filipe Iria Moutinho':'Joao Moutinho',
    'Ruben Goncalo Vinagre':'Ruben Vinagre',
    'Mahmoud Ahmed Trezeguet':'Trezeguet',
    'Ezri Konsa':'Ezri Konsa Ngoyo',
    'Jose Ignacio Jota':'Jota',
    'Francisco Kiko Femenia':'Kiko Femenia',
    'Mathew Ryan':'Mat Ryan',
    'Solomon March':'Solly March',
    'Heurelho da Silva Gomes':'Heurelho Gomes',
    'Gabriel Fernando Jesus':'Gabriel Jesus',
    'Roberto':'Roberto Jimenez',
    'Javier Chicharito':'Chicharito',
    'Joao Pedro Cavaco Cancelo':'Joao Cancelo',
    'Bernardo Mota Bernardo Silva':'Bernardo Silva',
    'Kepa':'Kepa Arrizabalaga',
    'Jorge Luiz Jorginho':'Jorginho',
    'Robert Kenedy Kenedy':'Kenedy',
    'Joelinton Cassio Joelinton':'Joelinton',
    'Joseph Willock':'Joe Willock',
    'Daniel Ceballos':'Dani Ceballos',
    'Gabriel Teodoro Martinelli':'Gabriel Martinelli',
    'Fernando Fernandinho':'Fernandinho',
    'Sung-yueng Ki Sung-yueng':'Ki Sung-yueng',
    'Frederic Guilbert':'Frederic Guilbert',
    'Jose Angel Angelino':'Angelino',
    'Heung-Min Son':'Son Heung-Min',
    'Bamidele Alli':'Dele Alli',
    'Frederico Fred':'Fred',
    'Eric Garcia':'Eric Garcia',
    'Arnaut Danjuma':'Arnaut Danjuma Groeneveld',
    'Addji Keaninkin Marc-Israel Guehi':'Marc Guehi',
    'Jose Diogo Dalot':'Diogo Dalot',
    'Bernard Ashley-Seal':'Benny Ashley-Seal',
    'Max Kilman':'Maximilian Kilman',
    'Ayotomiwa Dele-Bashiru':'Tom Dele-Bashiru',
    'Rhu-endly Cuco Martina':'Cuco Martina',
    'Abd-Al-Ali Morakinyo Olaposi Koiki':'Ali Koiki',
    'Goncalo Bento Cardoso':'Goncalo Cardoso',
    'Edward Nketiah':'Eddie Nketiah',
    'Jose Reina':'Pepe Reina',
    'Bruno Andre Jordao':'Bruno Jordao',
    'Bruno Miguel Fernandes':'Bruno Fernandes'
    }


def team_basic_df_generator():
    '''
    Generates a basic table of teams from the FPL API
    '''
    
    #Make the API call
    url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    results = requests.get(url).json()

    #We create a blank dataframe to store team information
    df_teams = pd.DataFrame(columns = ['TeamID','Team','ShortName','Strength'])

    #We loop through all the team data taking the required information
    for i in results['teams']:
        ID = i['id']
        team = i['name']
        short_name = i['short_name']
        strength = i['strength']

        df_temp = pd.DataFrame({'TeamID':[ID],
                                'Team':[team],
                                'ShortName':[short_name],
                                'Strength':[strength]})

        df_teams = pd.concat([df_teams, df_temp])

    #We set the TeamID as the index for the dataframe
    df_teams.set_index('TeamID',drop=True,inplace=True)

    #We also add the commentary names to the teams dataframe
    df_teams['CommentName'] = teams

    return df_teams
    

#We should create a function that will remove accents from player names
#e.g. "à" should become "a", and so forth. This will help with commentary
#recognition later...
def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


#We need to amend some full names in cases where player goes by single name
#e.g. 'Sokratis'
def single_name_update(name):
    #Check if any player's name is just the same name twice
    split = name.split()
    
    #For players who have the same name twice e.g. 'Sokratis'
    if split[0] == split[1]:
        return ' '.join(split[1:])
    
    #For players who have two names twice e.g. 'David Luis'
    if (len(split)==4) & (split[:2] == split[2:]):
        return ' '.join(split[2:])
    
    return name


def player_basic_df_generator():

    '''
    Creates a table of basic table of players from the FPL API
    '''
    #Make the API call
    url = 'https://fantasy.premierleague.com/api/bootstrap-static/'
    results = requests.get(url).json()

    #Bring in the 'elements' dictionary from the json file
    #This is part containing player informaion
    players_json = results['elements']

    #We create an empty dataframe with the columns we want
    df_players = pd.DataFrame(columns = ['PlayerCode','PlayerID','FirstName',
                                         'WebName','Team','Position'])

    #We iterate through each of the players in the json file...
    #...taking the information we want from it
    for i in range(len(players_json)):
        code = players_json[i]['code']
        ID = players_json[i]['id']
        first = remove_accents(players_json[i]['first_name'])
        web = remove_accents(players_json[i]['web_name'])
        team = players_json[i]['team']
        position = players_json[i]['element_type']

        df_temp = pd.DataFrame({'PlayerCode':[code],
                                'PlayerID':[ID],
                                'FirstName':[first],
                                'WebName':[web],
                                'Team':[team],
                                'Position':[position]})

        df_players = pd.concat([df_players, df_temp])

    #We set the playerID as the index for the dataframe
    df_players.set_index('PlayerID',drop=True,inplace=True)

    positions = ['GKP','DEF','MID','FWD']

    #We then update the columns with these strings as required
    df_players['Team'] = df_players['Team'].map(lambda x: teams[x-1])
    df_players['Position'] = df_players['Position'].map(lambda x: positions[x-1])
    df_players['CommentName'] = df_players['FirstName'].map(str) + ' ' + df_players['WebName'].map(str)
    
    #Correct the comment names where players go by a single name
    df_players['CommentName'] = df_players['CommentName'].map(lambda x: single_name_update(x))

    #Iterate through the keys, and update the df_player dataframe as required
    for i in list(player_name_key.keys()):
        new_name = player_name_key[i]
        df_players.loc[df_players['CommentName']==i,'CommentName'] = new_name
        
    return df_players


def PlayerAPI(player):
    '''
    Takes the player's code, and returns the
    API JSON file associated with them.
    '''
    
    url = f'https://fantasy.premierleague.com/api/element-summary/{player}/'
    return requests.get(url).json()


def PlayerHistory(player):
    '''
    Takes the player's code, and returns the
    API JSON file associated with their game
    history from the current season.
    '''
    json_file = PlayerAPI(player)
    return json_file['history']


def PlayerAPIStats(player):
    '''
    Takes a playerID and outputs a dataframe of
    the player's statistics derived from the FPL API
    - value
    - total_points
    - minutes
    - bps
    - clean_sheets
    - selected
    - transfers in (net)
    '''
    #Get the JSON file for the player
    history = PlayerHistory(player)
    
    #Extract the data from this JSON file
    playerID = [int(player) for i in history]
    gameweeks = [i['round']-9 if i['round'] > 38 else i['round'] for i in history]
    dates = [i['kickoff_time'][:10] for i in history]
    points = [i['total_points'] for i in history]
    value = [i['value']/10 for i in history]
    minutes = [i['minutes'] for i in history]
    bps = [i['bps'] for i in history]
    cs = [i['clean_sheets'] for i in history]
    saves = [i['saves'] for i in history]
    selected = [i['selected'] for i in history]
    transfers = [i['transfers_balance'] for i in history]
    
    df_temp = pd.DataFrame({'PlayerID':playerID,
                            'GameWeek':gameweeks,
                            'Date':dates,
                            'Points':points,
                            'Price':value,
                            'MinutesPlayed':minutes,
                            'CleanSheet':cs,
                            'Saves':saves,
                            'BPS':bps,
                            'SelectedBy':selected,
                            'NetTransfersIn':transfers})
    
    return df_temp


def PlayersAPIStats(players, gameweeks=None):
    '''
    Takes a list of playerIDs a list of gameweeks
    and outputs a dataframe of the player's statistics
    derived from the FPL API for those weeks
    - points
    - price
    - bps
    - selected
    - transfers in (net)    
    '''
    #If no gameweeks specified, then use all
    #gameweeks in the retured JSON file
    if gameweeks == None:
        gameweeks = list(range(1,PlayerAPIStats(players[0])['GameWeek'].max()+1))
    
    #Create a blank dataframe
    cols = ['PlayerID', 'GameWeek', 'Date', 'Points', 'Price',
            'BPS', 'SelectedBy', 'NetTransfersIn']
    df_temp = pd.DataFrame(columns=cols)
    
    #Iterate through the players and add their stats to the dataframe
    for i in players:
        new_rows = PlayerAPIStats(i)
        df_temp = pd.concat([df_temp, new_rows])
        
    #Remove rows we don't want
    df_temp = df_temp.loc[df_temp['GameWeek'].isin(gameweeks)]
            
    #Make everything numeric
    df_temp = df_temp.apply(pd.to_numeric, errors='ignore')
    
    #Reset the index
    df_temp.reset_index(inplace=True, drop=True)
    
    return df_temp