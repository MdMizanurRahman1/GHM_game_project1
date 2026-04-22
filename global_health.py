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
    AND is_completed = 0
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

#Mark event done
def mark_event_done(game_id, airport):
    cursor = connection_db.cursor()

    sql = """
    UPDATE game_event
    SET is_completed = 1
    WHERE game_id = %s AND airport_id = %s
    """

    cursor.execute(sql, (game_id, airport))


# Step 10. Start the main game session
# ==========================================================

# Sub-step 1. Start the main game session and Initializes the variables

read_plan = input("Hi!, Do you want to read the mission plan? (y/n): ").lower()

if read_plan == "y":
    with open("README.txt") as file:
        print(file.read())
scientist_name = input("Enter the scientist name: ")

print("\nWelcome", scientist_name + "!")
print("Mission: Your main goal is to stop the main virus outbreak and return safely.")

money = 1000
fuel_range_km = 2000

health = 100
current_day = 1
days_limit = 20


game_over = False
outbreak_stopped = False
missions_completed_successfully = 0

risk_events_found = 0
bonus_events_found = 0


REQUIRED_HELP = 3
REQUIRED_RISK = 1
REQUIRED_BONUS = 2

# Sub-step 2 – load all 30 airports

airports = load_airports()

starting_airport = airports[0]["ident"]
current_airport_location = starting_airport


# Sub-step 3 – create the new game session in the database

game_id = create_newGame(scientist_name, starting_airport, money, fuel_range_km)


# Sub-step 4 – assign the events

assigning_events(game_id, airports, starting_airport)


last_event_type = None
# Sub-step 5 – starting the main game loop

while not game_over:

    # ---------------- WIN CONDITION ----------------
    if outbreak_stopped and current_airport_location == starting_airport:
        final_airport = get_airport_information(current_airport_location)

        print("\nMISSION COMPLETE successfully!")
        print("You are at:", final_airport["name"])
        print("You have successfully controlled the main outbreak and returned safely.")

        print("Remaining money:", money)
        print("Remaining fuel:", int(fuel_range_km))

        game_over = True
        break

    # ---------------- LOSE CONDITION (NEW - TOP) ----------------
    if health <= 0:
        print("\nMISSION FAILED: You got infected.")
        game_over = True
        break

    if current_day > days_limit:
        print("\nMISSION FAILED: Time ran out.")
        game_over = True
        break

    # ---------------- STATUS ----------------
    airport = get_airport_information(current_airport_location)

    print("\n----------------------------------")
    print("You are at:", airport["name"])
    print("Country:", airport["iso_country"])

    print("Your current balance:", money, "€.")
    print("Your current fuel:", int(fuel_range_km), "km")
    print("Health:", health)
    print("Day:", current_day, "/", days_limit)

    print("\nMission Ongoing")

    shown_help = min(missions_completed_successfully, REQUIRED_HELP)
    shown_risk = min(risk_events_found, REQUIRED_RISK)
    shown_bonus = min(bonus_events_found, REQUIRED_BONUS)

    print("Help missions earned:", shown_help, "/", REQUIRED_HELP)
    print("Risk events identified:", shown_risk, "/", REQUIRED_RISK)
    print("Bonus events obtained:", shown_bonus, "/", REQUIRED_BONUS)

    # ---------------- EVENTS ----------------
    event = check_events(game_id, current_airport_location)

    if event and event["event_type"] == last_event_type:
        event = False

    # ---------------- HELP EVENT ----------------
    if event and event["event_type"] == "Help":

        print("\nHelp Mission:", event["event_name"])
        questions = get_all_questions(event["event_id"])

        correct_answers_count = 0

        for question in questions:
            print("\nQuestion:", question["question_text"])
            answers = get_all_answers(question["quiz_id"])

            for ans in answers:
                print(ans["answer_id"], "-", ans["answer_text"])

            right_answers = [a["answer_id"] for a in answers]

            attempt_numbers = 2
            answered_correctly = False

            while attempt_numbers > 0 and not answered_correctly:

                user_input_value = input("Choose the correct answer number please: ")

                if user_input_value == "":
                    print("Please enter a number.")
                    continue

                user_answer = int(user_input_value)

                if user_answer not in right_answers:
                    print("Invalid option.")
                    continue

                if check_correct_answer(user_answer):
                    print("Correct!")
                    correct_answers_count += 1
                    answered_correctly = True
                else:
                    attempt_numbers -= 1
                    if attempt_numbers > 0:
                        print("Incorrect. Try again.")
                    else:
                        print("No attempts remaining.")

        if correct_answers_count >= 2:
            print("Mission successful!")
            money += event["reward_money"]
            missions_completed_successfully += 1

            print("Reward:", event["reward_money"], "€")
            print("Balance:", money)

            # HEALTH RECOVERY
            health += 5
            print("Health improved! +5")

        else:
            print("Mission failed.")

        mark_event_done(game_id, current_airport_location)
        last_event_type = "Help"

    # ---------------- RISK EVENT ----------------
    elif event and event["event_type"] == "Risk":

        print("\nVirus activity identified!")

        choice = input("1 Leave quickly (-100€) / 2 Delay (-200€): ")

        penalty_money = 100 if choice == "1" else 200

        money = max(0, money - penalty_money)
        print("Remaining money:", money)

        # HEALTH DAMAGE
        health -= 15
        print("You were exposed to the virus! Health:", health)

        if health < 0:
            health = 0

        risk_events_found += 1

        mark_event_done(game_id, current_airport_location)
        last_event_type = "Risk"

    # ---------------- BONUS EVENT ----------------
    elif event and event["event_type"] == "Bonus":

        print("\nA scientist offers tips!")

        reward_type = random.choice(["money", "fuel"])

        if reward_type == "money":
            money += 50
            print("You got +50€")
        else:
            fuel_range_km += 10
            print("You got +10 fuel")

        bonus_events_found += 1

        mark_event_done(game_id, current_airport_location)
        last_event_type = "Bonus"

    # ---------------- MAIN EVENT ----------------
    elif event and event["event_type"] == "Main":

        if missions_completed_successfully < REQUIRED_HELP or risk_events_found < REQUIRED_RISK or bonus_events_found < REQUIRED_BONUS:
            print("\nComplete required missions first.")
        else:
            print("\nFinal mission!")

            choice = input("Choose (1,2,3): ")

            if choice in ["1", "2", "3"]:
                print("Outbreak stopped!")
                outbreak_stopped = True
                mark_event_done(game_id, current_airport_location)
                current_airport_location = starting_airport
                continue

    # ---------------- TRAVEL ----------------
    accessible_airports = airports_in_ranges(current_airport_location, airports, fuel_range_km)

    if accessible_airports:

        print("\nAirports in range:")

        airports_with_distance = []

        for a in accessible_airports:
            d = calculate_distance(current_airport_location, a["ident"])
            airports_with_distance.append([a, d])


        # simple sorting
        def get_distance(item):
            return item[1]


        airports_with_distance.sort(key=get_distance)

        for i in range(len(airports_with_distance)):
            item = airports_with_distance[i]

            print(i + 1, "-", item[0]["ident"], "-", item[0]["name"], "-", int(item[1]), "km")
        choice = input("\nChoose airport number: ")

        while not choice.isdigit() or not (1 <= int(choice) <= len(airports_with_distance)):
            choice = input("Choose again: ")

        selected_airport = airports_with_distance[int(choice)-1][0]["ident"]
        travel_distance = calculate_distance(current_airport_location, selected_airport)

        if travel_distance <= fuel_range_km:

            fuel_range_km -= travel_distance
            update_game_session(selected_airport, fuel_range_km, money, game_id)
            current_airport_location = selected_airport

            # TIME + HEALTH COST
            current_day += 1
            health -= 5

            print("Travel cost: -1 day, -5 health")

        else:
            print("Too far.")



    else:

        print("\nNo airports available.")

        # if player cannot move AND cannot buy fuel → lose

        if fuel_range_km <= 0 or len(accessible_airports) == 0:

            if money <= 0:
                print("\nMISSION FAILED: You are stuck with no fuel and no money.")

                game_over = True

    # ---------------- FUEL ----------------
    if money > 0 and not game_over:

        fuel_buy = input("Buy fuel (Enter to skip): ")

        if fuel_buy:
            fuel_buy = int(fuel_buy)

            if fuel_buy <= money:
                fuel_range_km += fuel_buy * 2
                money -= fuel_buy
                print("Fuel:", int(fuel_range_km), "| Money:", money)
            else:
                print("Not enough money.")

    # ---------------- LOSE ----------------
    if money <= 0 and fuel_range_km <= 0:
        print("\nMISSION FAILED")
        game_over = True