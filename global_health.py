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

player_name = input("Enter scientist name: ")
print("\nWelcome", player_name + "!")
print("Mission: Stop the virus outbreak and return safely to your starting airport.")

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

# ==========================================================
# STEP 5 – MAIN GAME LOOP
# ==========================================================

while not game_over:

    airport = get_airport_info(current_airport)

    print("\n----------------------------------")
    print("You are at:", airport["name"])
    print("Country:", airport["iso_country"])

    print("You have", money, "€ left.")

    print("Fuel range left:", int(fuel_range_km), "km")
    # step 6 check event
    event = check_event(game_id, current_airport)

    # step 7 Help missions
    if event and event["event_type"] == "Help":

        print("\nHelp Mission:", event["event_name"])

        questions = get_questions(event["event_id"])

        correct_answers = 0

        for question in questions:

            print("\nQuestion:", question["question_text"])

            answers = get_answers(question["quiz_id"])

            for a in answers:
                print(a["answer_id"], "-", a["answer_text"])

            attempts = 2
            answered_correctly = False

            while attempts > 0 and not answered_correctly:

                user_answer = int(input("Choose answer number: "))

                if check_answer(user_answer):

                    print("Correct!")
                    correct_answers += 1
                    answered_correctly = True

                else:

                    attempts -= 1

                    if attempts > 0:
                        print("Wrong answer. Try again.")
                    else:
                        print("No attempts left.")

        if correct_answers >= 2:

            print("Mission successful!")

            money += event["reward_money"]
            successful_missions += 1

            print("Reward:", event["reward_money"], "€")
            print("Your money now:", money, "€")

        else:

            print("\nMission failed.")
    #step 8 risk events
    elif event and event["event_type"] == "Risk":

        print("\nVirus spread detected!")

        choice = input("1 Leave quickly (-100€) / 2 Delay (-200€): ")

        if choice == "1":
            money -= 100
        else:
            money -= 200

        print("Money remaining:", money)
    #step 9 bonus events
    elif event and event["event_type"] == "Bonus":

        print("\nFriendly scientist shares tips!")

        reward = random.choice(["money", "fuel"])

        if reward == "money":

            money += 50
            print("You received +50€")

        else:

            fuel_range_km += 10
            print("You received +10 fuel")
    #step 10 main outbreak event

   # ==========================================================
    # MAIN OUTBREAK EVENT
    # ==========================================================

    elif event and event["event_type"] == "Main":

        # First check if player completed enough help missions

        if successful_missions < 2:

            print("\nYou discovered the main outbreak location!")
            print("You must complete at least TWO help missions first.")




        else:

            # Player is ready for the final mission

            print("\nYou have arrived at the main outbreak site.")

            print("Complete one final task to contain it.")

            print("\nChoose your action:")

            print("1 Deploy emergency containment supplies")

            print("2 Coordinate with local scientists")

            print("3 Deliver critical medical kit")

            choice = input("Enter your choice (1, 2 or 3): ")

            if choice == "1" or choice == "2" or choice == "3":

                print("\nCongratulations! You have stopped the main outbreak.")

                outbreak_stopped = True

                # Save completion in database

                cursor = conn.cursor()

                sql = """

                      UPDATE game

                      SET main_outbreak_completed = 1

                      WHERE game_id = %s \

                      """

                cursor.execute(sql, (game_id,))

                print("Return to the starting airport to finish the mission.")


            else:

                print("Invalid choice. The outbreak continues.")
    #step 11 buy fuel in range km

    if money > 0:

        print("\nFuel station available")
        print("1 € = 2 km fuel")

        buy = input("Enter money to spend on fuel (or press Enter to skip): ")

        if buy != "":

            buy = int(buy)

            if buy > money:

                print("Not enough money.")

            else:

                fuel_range_km += buy * 2
                money -= buy

                print("New fuel range:", int(fuel_range_km), "km")
                print("Money left:", money)

    # step 12 travel system in range

# ----------------------------------------------------------
    # TRAVEL SYSTEM
    # ----------------------------------------------------------

    available_airports = airports_in_range(current_airport, airports, fuel_range_km)

    # If airports are reachable
    if len(available_airports) > 0:

        print("\nAirports in range:")

        for airport in available_airports:
            dist = calculate_distance(current_airport, airport["ident"])
            print(airport["ident"], "-", airport["name"], "-", int(dist), "km")

        # Ask player where to go
        destination = input("\nEnter destination ICAO: ").upper()

        travel_distance = calculate_distance(current_airport, destination)

        if travel_distance <= fuel_range_km:

            fuel_range_km -= travel_distance
            update_game(destination, fuel_range_km, money, game_id)
            current_airport = destination

        else:
            print("That airport is too far.")


    # If no airport is reachable
    else:

        print("\nNo airports are within your current fuel range.")

        if money > 0:

            print("\nFuel station available")
            print("1 € = 2 km fuel")

            fuel_buy = input("Enter money to spend on fuel (press Enter to skip): ")

            if fuel_buy != "":

                fuel_buy = int(fuel_buy)

                if fuel_buy <= money:

                    fuel_range_km += fuel_buy * 2
                    money -= fuel_buy

                    print("New fuel range:", int(fuel_range_km), "km")
                    print("Money left:", money, "€")

                else:
                    print("You do not have enough money.")

        else:

            print("\nYou have no money and no fuel.")
            print("MISSION FAILED")
            game_over = True

    # step 13 lose condition
    if money <= 0 and fuel_range_km <= 0:

        print("\nMISSION FAILED")
        game_over = True

    # step 14 win condition
    if outbreak_stopped and current_airport == start_airport:

        print("\nMISSION COMPLETE!")
        print("You successfully controlled the outbreak and returned safely.")

        game_over = True
    # step 15 end the game

    print("Money left:", money)
    print("Fuel left:", int(fuel_range_km))