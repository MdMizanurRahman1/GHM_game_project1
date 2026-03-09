#Libraries imported for this project
import mysql.connector
import random
from geopy import distance

#connect the pycharm to health_game database

connection_db = mysql.connector.connect(
         host='127.0.0.1',
         port= 3306,
         database='health_game',
         user='mizan',
         password='mizan2217',
         autocommit=True
         )


#Step 1. Get random 30 airports, one per each EU countries
def load_airports():

    sql = """
    SELECT iso_country, ident, name, latitude_deg, longitude_deg
    FROM airport
    WHERE continent='EU'
    AND type='large_airport'
    GROUP BY iso_country
    ORDER BY RAND()
    LIMIT 30
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql)

    return cursor.fetchall()


#Step 2. create a new game session in mariadb database
# ==========================================================

def create_newGame(scientist_name, starting_airport, money, fuel_ranges):

    sql = """
    INSERT INTO game
    (player_name, starting_airport_id, current_airport_id,
     money, fuel, successful_missions_count,
     main_outbreak_completed, status)

    VALUES (%s,%s,%s,%s,%s,0,0,'ongoing')
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql, (scientist_name, starting_airport, starting_airport, money, fuel_ranges))

    return cursor.lastrowid


# ==========================================================
# Step 3. assigning the events based on probability values in 30 airports
# ==========================================================

def assigning_events(game_id, airports, starting_airport):

    cursor = connection_db.cursor(dictionary=True)

    sql = "SELECT event_id, probability FROM event"
    cursor.execute(sql)
    events = cursor.fetchall()

    event_lists = []

    for event in events:
        for i in range(event["probability"]):
            event_lists.append(event["event_id"])

    accessible_airports = [a for a in airports if a["ident"] != starting_airport]

    random.shuffle(accessible_airports)
    random.shuffle(event_lists)

    for i, event_id in enumerate(event_lists):

        if i >= len(accessible_airports):
            break

        airport_id = accessible_airports[i]["ident"]

        sql = """
        INSERT INTO game_event
        (game_id, airport_id, event_id, is_completed, is_failed)
        VALUES (%s,%s,%s,0,0)
        """

        cursor.execute(sql, (game_id, airport_id, event_id))


# Step 4. fetch airport information using ICAO codes
def get_airport_information(icao_code):

    sql = """
    SELECT iso_country, ident, name, latitude_deg, longitude_deg
    FROM airport
    WHERE ident = %s
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql, (icao_code,))

    return cursor.fetchone()


#Step 5. calculate the travel distance between two airports in km
# ==========================================================

def calculate_distance(current, target):

    started_airport = get_airport_information(current)
    destinated_airport = get_airport_information(target)

    return distance.distance(
        (started_airport["latitude_deg"], started_airport["longitude_deg"]),
        (destinated_airport["latitude_deg"], destinated_airport["longitude_deg"])
    ).km


#step 6. find range for airports which can be reachable with current fuel

def airports_in_ranges(icao_code, airports, fuel_range_km):

    airports_reachable = []

    for airport in airports:

        dist = calculate_distance(icao_code, airport["ident"])

        if dist <= fuel_range_km and dist !=0:
            airports_reachable.append(airport)

    return airports_reachable


#step 7 check events if these are available when player lands in airport 

def check_events(game_id, airport):

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
WHERE game_id=%s 
AND airport_id=%s 
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql, (game_id, airport))

    result_output = cursor.fetchone()

    if result_output is None:
        return False

    return result_output


#step 8. quiz questions, options and answers,
# sub-step 1. get all the quiz questions
# ==========================================================

def get_all_questions(event_id):

    sql = """
    SELECT quiz_id,question_text
    FROM quiz
    WHERE event_id=%s
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql,(event_id,))

    return cursor.fetchall()

# sub-step 2. get all the quiz answer options
def get_all_answers(quiz_id):

    sql = """
    SELECT answer_id,answer_text
    FROM answer
    WHERE quiz_id=%s
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql,(quiz_id,))

    return cursor.fetchall()

# sub-step 3. get the correct quiz answer
def check_correct_answer(answer_id):

    sql = """
    SELECT is_correct
    FROM answer
    WHERE answer_id = %s
    """

    cursor = connection_db.cursor(dictionary=True)
    cursor.execute(sql, (answer_id,))

    result_output = cursor.fetchone()

    return result_output["is_correct"]


# Step 9 update game money, location, and fuel and save to the database
# ==========================================================

def update_game_session(current_airport_location, fuel_ranges, money, game_id):

    sql = """
    UPDATE game
    SET current_airport_id = %s,
        fuel = %s,
        money = %s
    WHERE game_id = %s
    """

    cursor = connection_db.cursor()
    cursor.execute(sql,(current_airport_location, fuel_ranges, money, game_id))



# ==========================================================
#Step 1. Start the main game session

print("\nWELCOME TO GLOBAL HEALTH MISSION")

scientist_name = input("Enter the scientist name: ")
print("\nWelcome", scientist_name + "!")
print("Mission: Stop the main virus outbreak and return safely to the starting airport.")

money = 1000
fuel_range_km = 2000

game_over = False
outbreak_stopped = False
successful_missions = 0

risk_events_seen = 0
bonus_events_seen = 0


# STEP 2 – load all airports

airports = load_airports()

starting_airport = airports[0]["ident"]
current_airport_location = starting_airport


# STEP 3 – CREATE GAME IN DATABASE

game_id = create_newGame(scientist_name, starting_airport, money, fuel_range_km)


# STEP 4 – ASSIGN EVENTS

assigning_events(game_id, airports, starting_airport)


# STEP 5 – MAIN GAME LOOP

while not game_over:

    airport = get_airport_information(current_airport_location)

    print("\n----------------------------------")
    print("You are at:", airport["name"])
    print("Country:", airport["iso_country"])

    print("You have", money, "€ left.")
    print("Fuel range left:", int(fuel_range_km), "km")

    print("\nMission Progress")
    print("Help missions completed:", successful_missions, "/ 2")
    print("Risk events encountered:", risk_events_seen, "/ 1")
    print("Bonus events received:", bonus_events_seen, "/ 1")

    event = check_events(game_id, current_airport_location)


    if event and event["event_type"] == "Help":

        print("\nHelp Mission:", event["event_name"])

        questions = get_all_questions(event["event_id"])

        correct_answers = 0

        for question in questions:

            print("\nQuestion:", question["question_text"])

            answers = get_all_answers(question["quiz_id"])

            for a in answers:
                print(a["answer_id"], "-", a["answer_text"])

            attempts = 2
            answered_correctly = False

            while attempts > 0 and not answered_correctly:

                user_answer = int(input("Choose answer number: "))

                if check_correct_answer(user_answer):

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

            print("Mission failed. You needed at least 2 correct answers.")



    elif event and event["event_type"] == "Risk":

        print("\nVirus spread detected!")

        choice = input("1 Leave quickly (-100€) / 2 Delay (-200€): ")

        if choice == "1":
            money -= 100
        else:
            money -= 200

        print("Money remaining:", money)

        risk_events_seen += 1



    elif event and event["event_type"] == "Bonus":

        print("\nFriendly scientist shares tips!")

        reward = random.choice(["money", "fuel"])

        if reward == "money":

            money += 50
            print("You received +50€")

        else:

            fuel_range_km += 10
            print("You received +10 fuel")

        bonus_events_seen += 1


    elif event and event["event_type"] == "Main":

        if successful_missions < 2 or risk_events_seen < 1 or bonus_events_seen < 1:

            print("\nYou discovered the main outbreak location!")
            print("Before stopping the outbreak you must:")
            print("- Complete at least TWO help missions")
            print("- Encounter at least ONE virus spread event")
            print("- Receive at least ONE scientist bonus")

        else:

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

                print("Return to the starting airport to finish the mission.")

                # move player to starting airport
                current_airport_location = starting_airport

                # show final location and win codition

                final_airport = get_airport_information(current_airport_location)

                print("\nMISSION COMPLETE!")
                print("You are at:", final_airport["name"])
                print("You successfully controlled the outbreak and returned safely.")

                print("Money left:", money)
                print("Fuel left:", int(fuel_range_km))

                game_over = True
                break

            else:

                print("Invalid choice. The outbreak continues.")

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

    accessible_airports = airports_in_ranges(current_airport_location, airports, fuel_range_km)

    if len(accessible_airports) > 0:

        print("\nAirports in range:")

        for airport in accessible_airports:
            dist = calculate_distance(current_airport_location, airport["ident"])
            print(airport["ident"], "-", airport["name"], "-", int(dist), "km")

        destination = input("\nEnter destination ICAO: ").upper()

        travel_distance = calculate_distance(current_airport_location, destination)

        if travel_distance <= fuel_range_km:

            fuel_range_km -= travel_distance
            update_game_session(destination, fuel_range_km, money, game_id)
            current_airport_location = destination

        else:
            print("That airport is too far.")

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

            print("MISSION FAILED")
            game_over = True

    if money <= 0 and fuel_range_km <= 0:

        print("\nMISSION FAILED")
        game_over = True

