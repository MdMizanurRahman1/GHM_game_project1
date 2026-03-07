import mysql.connector
import random
from geopy import distance

conn = mysql.connector.connect(
         host='127.0.0.1',
         port= 3306,
         database='health_game',
         user='mizan',
         password='mizan2217',
         autocommit=True
         )



#1 To get 30 airports
def get_airports():

    sql = """
    SELECT iso_country, ident, name, latitude_deg, longitude_deg
    FROM airport
    WHERE continent='EU'
    AND type='large_airport'
    GROUP BY iso_country
    ORDER BY RAND()
    LIMIT 30
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql)

    return cursor.fetchall()


 #STEP 2 – CREATE A NEW GAME SESSION
# ==========================================================

def create_game(player_name, start_airport, money, fuel):


    sql = """
    INSERT INTO game
    (player_name, starting_airport_id, current_airport_id,
     money, fuel, successful_missions_count,
     main_outbreak_completed, status)

    VALUES (%s,%s,%s,%s,%s,0,0,'ongoing')
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (player_name, start_airport, start_airport, money, fuel))

    return cursor.lastrowid



# ==========================================================
# Step 3 ASSIGN EVENTS TO AIRPORTS
# ==========================================================

def assign_events(game_id, airports, start_airport):

    cursor = conn.cursor(dictionary=True)

    # STEP 1: Read event probabilities
    sql = "SELECT event_id, probability FROM event"
    cursor.execute(sql)
    events = cursor.fetchall()

    # STEP 2: Create event list
    event_list = []

    for event in events:
        for i in range(event["probability"]):
            event_list.append(event["event_id"])

    # STEP 3: Remove starting airport
    available_airports = [a for a in airports if a["ident"] != start_airport]

    # STEP 4: Shuffle airports and events
    random.shuffle(available_airports)
    random.shuffle(event_list)

    # STEP 5: Assign events
    for i, event_id in enumerate(event_list):

        if i >= len(available_airports):
            break

        airport_id = available_airports[i]["ident"]

        sql = """
        INSERT INTO game_event
        (game_id, airport_id, event_id, is_completed, is_failed)
        VALUES (%s,%s,%s,0,0)
        """

        cursor.execute(sql, (game_id, airport_id, event_id))

# Step 4 get airport information

def get_airport_info(icao):

    sql = """
    SELECT iso_country, ident, name, latitude_deg, longitude_deg
    FROM airport
    WHERE ident = %s
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (icao,))

    return cursor.fetchone()

#Step 5  CALCULATE DISTANCE between two airports
# ==========================================================

def calculate_distance(current, target):

    start = get_airport_info(current)
    end = get_airport_info(target)

    return distance.distance(
        (start["latitude_deg"], start["longitude_deg"]),
        (end["latitude_deg"], end["longitude_deg"])
    ).km

# ==================================================

#step 6 find range for airports

def airports_in_range(icao, airports, fuel_range_km):

    in_range_airports = []

    for airport in airports:

        dist = calculate_distance(icao, airport["ident"])

        if dist <= fuel_range_km and  not dist ==0:
            in_range_airports.append(airport)

    return in_range_airports

#step 7 check events if exists

def check_event(game_id, airport):

    sql = """
    SELECT event.event_id,
           event.event_type,
           event.event_name,
           reward_money,
           reward_fuel,
           penalty_option_one,
           penalty_option_two
    FROM game_event
    JOIN event ON event.event_id = game_event.event_id
    WHERE game_id=%s AND airport_id=%s
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (game_id, airport))

    result = cursor.fetchone()

    if result is None:
        return False

    return result


#step 8 QUIZ FUNCTIONS
# ==========================================================
#1 get the questions

def get_questions(event_id):

    sql = """
    SELECT quiz_id,question_text
    FROM quiz
    WHERE event_id=%s
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql,(event_id,))

    return cursor.fetchall()

#2 get the answers

def get_answers(quiz_id):

    sql = """
    SELECT answer_id,answer_text
    FROM answer
    WHERE quiz_id=%s
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql,(quiz_id,))

    return cursor.fetchall()

#3 get the correct answer

def check_answer(answer_id):

    sql = """
    SELECT is_correct
    FROM answer
    WHERE answer_id = %s
    """

    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, (answer_id,))

    result = cursor.fetchone()

    return result["is_correct"]


# Step 9 update game status or current location
# ==========================================================

def update_game(current_airport, fuel, money, game_id):

    sql = """
    UPDATE game
    SET current_airport_id = %s,
        fuel = %s,
        money = %s
    WHERE game_id = %s
    """

    cursor = conn.cursor()
    cursor.execute(sql,(current_airport, fuel, money, game_id))

# ==========================================================
#Step 1 start the game

print("\nGLOBAL HEALTH MISSION")
print("You are a scientist trying to stop a virus outbreak.")

player_name = input("Enter scientist name: ")

# starting resources
money = 1000
fuel_range_km = 2000

# game state
game_over = False
outbreak_stopped = False
successful_missions = 0

# ==========================================================
# STEP 2 – load all airports
# ==========================================================

airports = get_airports()

# start_airport ident
start_airport = airports[0]["ident"]
#current airport
current_airport = start_airport

# ==========================================================
# STEP 3 – CREATE GAME IN DATABASE
# ==========================================================

game_id = create_game(player_name, start_airport, money, fuel_range_km)

# ==========================================================
# STEP 4 – ASSIGN EVENTS
# ==========================================================

assign_events(game_id, airports, start_airport)

