GLOBAL HEALTH MISSION

About the Project
This project is a simple text-based game made with Python and MySQL.
In the game, the player becomes a scientist who travels between different airports in Europe. The mission is to help stop a virus outbreak by completing tasks and finally finding the main outbreak location.

The idea of the game is to combine programming with a small adventure-style challenge. While traveling between airports, the player must manage money and fuel and also complete different events that appear at airports.

Game Goal
The main goal of the game is to stop the virus outbreak.

To reach the final outbreak location, the player needs to:

* complete at least three help missions
* encounter at least two virus risk event
* receive at least two bonus event

After these conditions are completed, the player can stop the main outbreak. Once the outbreak is controlled, the player returns to the starting airport and the mission is completed.

Game Features
The game includes several different mechanics:

* Travel system between European airports
* Fuel system (1 euro gives 2 km of fuel)
* Help missions with quiz questions
* Risk events that may reduce the player’s money
* Bonus events that give extra fuel or money
* Random airport locations so the game is different each time

How to Run the Game

1. Import the database
   First import the file **health_game.sql** into MySQL or MariaDB.

2. Install required Python libraries
   The program uses the following libraries:

* mysql.connector
* geopy

3. Run the Python file
   Open **global_health.py** in PyCharm or another Python environment and run the program.

4. Start playing
   Enter your name when the game starts and follow the instructions shown in the terminal.

Game Rules

* Travelling between airports uses fuel based on the real distance between locations.
* Players can buy more fuel using money.
* If the player runs out of both money and fuel, the mission fails.
* Completing missions gives rewards such as money or fuel.

-----------------END----------------
