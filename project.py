import sqlite3
import re
import time
import sys
import hashlib
import random

from os import name, system
from pyfiglet import Figlet

name_regex = r"^[a-zA-Z0-9]{4,32}$"
passcode_regex = r"^[0-9]{6}$"


class UserSavegame:
    def __init__(self) -> None:
        self.ranks = {
            0: "Newbie",
            1000: "Trained",
            2500: "Experienced Hunter",
            5000: "Distinguished Hunter",
            10000: "The Maze Hunter",
        }

        self.con = sqlite3.connect("user_savegame.db")
        self.cur = self.con.cursor()

        try:
            self.cur.execute(
                "CREATE TABLE saved_games(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, passcode TEXT NOT NULL, diamond_count INTEGER NOT NULL, score INTEGER NOT NULL, rank TEXT NOT NULL)"
            )
        except sqlite3.OperationalError:
            # Table already exists
            ...

    def create_new_game(self, name, passcode):
        self.name = name
        self.passcode = passcode

        self.cur.execute(
            """
            INSERT INTO saved_games(name, passcode, diamond_count, score, rank) VALUES
                (?, ?, ?, ?, ?)
        """,
            (name, passcode, 0, 0, "Newbie"),
        )

        self.con.commit()

        fetch = self.cur.execute(
            """SELECT * from saved_games WHERE name = ? AND passcode = ?""",
            (name, passcode),
        ).fetchone()

        self.user_id = fetch[0]
        self.name = fetch[1]
        self.rank = fetch[5]

    def check_name_availability(self, name):
        check = self.cur.execute(
            """SELECT * from saved_games WHERE name = ?""", (name,)
        ).fetchone()

        if check is None:
            return 0

    def load_game(self, name, passcode):
        check = self.cur.execute(
            """SELECT * from saved_games WHERE name = ? AND passcode = ?""",
            (name, passcode),
        )
        fetch = check.fetchone()

        if fetch is None:
            return -1

        self.user_id = fetch[0]
        self.name = fetch[1]
        self.diamond = fetch[3]
        self.score = fetch[4]
        self.rank = fetch[5]

        return 1

    def calculate_rank(self, score):
        for minimum, rank_name in self.ranks.items():
            if score < minimum:
                break

            rank = rank_name

        return rank

    def save_game(self, session_result: dict):
        info = self.cur.execute(
            """SELECT * FROM saved_games WHERE id = ?""", (session_result["id"],)
        ).fetchone()

        new_diamond = info[3] + session_result["diamond"]
        new_score = info[4] + session_result["score"]
        new_rank = self.calculate_rank(new_score)

        self.cur.execute(
            """UPDATE saved_games SET diamond_count = ? WHERE id = ?""",
            (new_diamond, session_result["id"]),
        )
        self.con.commit()

        self.cur.execute(
            """UPDATE saved_games SET score = ? WHERE id = ?""",
            (new_score, session_result["id"]),
        )
        self.con.commit()

        self.cur.execute(
            """UPDATE saved_games SET rank = ? WHERE id = ?""",
            (new_rank, session_result["id"]),
        )
        self.con.commit()

        if new_rank != info[5]:
            print(f"\nYou also have been promoted to {new_rank}!")

    def delete_savegame(self, user_id):
        self.cur.execute("""DELETE FROM saved_games WHERE id = ?""", (user_id,))
        self.con.commit()

    def display_leaderboard(self):
        clear_screen()

        rank = 1

        fetch = self.cur.execute(
            """SELECT name, diamond_count, score, rank FROM saved_games ORDER BY score DESC"""
        ).fetchall()

        if len(fetch) == 0:
            print("\nThere is no one brave enough to enter the maze... yet.")
            return

        print("\nHUNTER LEADERBOARD")

        for row in self.cur.execute(
            """SELECT name, diamond_count, score, rank FROM saved_games ORDER BY score DESC LIMIT 10"""
        ):
            print(f"{rank}. {row[0]} - {row[3]} - {row[1]}x 💎 ({row[2]})")
            rank += 1


class Maze:
    def __init__(self, user: UserSavegame) -> None:
        self.user = user
        self.user_id = user.user_id
        self.user_name = user.name
        self.user_rank = user.rank
        self.user_diamond = user.diamond
        self.user_score = user.score

    def initialize_game(self):
        clear_screen()

        print(f"\nWelcome, {self.user_name}.")
        print(f"Current ranking: {self.user_rank}\n")
        time.sleep(0.5)

        print(f"Before you begin, would you like to see the tutorials? (Y/N)")
        time.sleep(0.5)

        while True:
            choice = input("> ").upper()

            if choice == "Y":
                self.display_tutorial()
                break
            elif choice == "N":
                break

            print("\nWrong choice, Hunter.")

        self.start_game()

    def setup_maze(self, level):
        self.maze = []
        self.user_position = [0, 0]
        self.level = level
        self.diamond_in_maze = 1
        self.total_diamond_in_session = 1
        self.score_multiplier = 1

        if self.level == 1:
            self.maze_width = 5
            self.maze_height = 5
        elif self.level == 2:
            self.maze_width = 10
            self.maze_height = 10
        elif self.level == 3:
            self.maze_width = 15
            self.maze_height = 15

        for row in range(self.maze_height):
            self.maze.append([])
            for column in range(self.maze_width):
                self.maze[row].append(".")

        for _ in range((self.maze_height * self.maze_width) // 2):
            while True:
                x = random.randint(0, self.maze_width - 1)
                y = random.randint(0, self.maze_height - 1)

                # Don't block the starting position
                if (
                    [y, x] == [0, 1]
                    or [y, x] == [1, 0]
                    or [y, x] == [0, 0]
                    or [y, x] == [1, 1]
                ):
                    continue

                # Minimize chance of dead end
                try:
                    if self.maze[y][x - 1] == "#":
                        continue
                    if self.maze[y - 1][x] == "#":
                        continue
                    if self.maze[y - 1][x - 1] == "#":
                        continue
                except IndexError:
                    continue

                self.maze[y][x] = "#"

                break

        self.maze[0][0] = "\x1b[38;5;14m@\x1b[0m"

        self.maze[random.randint(0, self.maze_height - 1)][
            random.randint(self.maze_width // 2, self.maze_width - 1)
        ] = "💎"

        if self.level == 2:
            self.score_multiplier = 1.5
        elif self.level == 3:
            self.diamond_in_maze = 2
            self.total_diamond_in_session = 2
            self.score_multiplier = 1.5
            while True:
                y = random.randint(0, self.maze_height - 1)
                x = random.randint(self.maze_width // 2, self.maze_width - 1)

                if self.maze[y][x] != "💎":
                    self.maze[y][x] = "💎"
                    break

    def update_maze(self, move):
        if move not in ("up", "down", "right", "left", ":("):
            return -1

        user_y, user_x = self.user_position
        prev_user_y, prev_user_x = self.user_position

        if move == "up":
            if user_y - 1 < 0:
                return -1
            user_y -= 1

        elif move == "down":
            if user_y + 1 > self.maze_height - 1:
                return -1
            user_y += 1

        elif move == "right":
            if user_x + 1 > self.maze_width - 1:
                return -1
            user_x += 1

        elif move == "left":
            if user_x - 1 < 0:
                return -1
            user_x -= 1

        elif move == ":(":
            self.setup_maze(self.level)
            return

        if self.maze[user_y][user_x] == "💎":
            self.diamond_in_maze -= 1
        elif self.maze[user_y][user_x] == "#":
            return -1

        self.user_position = user_y, user_x
        self.maze[prev_user_y][prev_user_x] = "."
        self.maze[user_y][user_x] = "\x1b[38;5;14m@\x1b[0m"

    def show_maze(self):
        for row in range(self.maze_height):
            for column in range(self.maze_width):
                if column == 0:
                    print()
                print(self.maze[row][column] + "\t", end="")

    def display_tutorial(self):
        clear_screen()

        self.setup_maze(1)

        print("\nThe maze has 3 levels, the higher the level the harder it is.")
        print("Does harder maze comes with better rewards? who knows...")

        self.show_maze()

        print("\n\nAbove is an example of a Level 1 Maze")
        print(
            """\nYour position is "@" and your objective is to get to the treasure position."""
        )
        print(
            """You can't go into a path that is blocked by a "#", nor out of bound path. """
        )
        print(
            """\nTo move your position, simply bestow (type in):\n- "up" to move up\n- "down" to move down\n- "right" to move to the right\n- "left" to move to the left"""
        )
        print(
            """\nIf you're lost in the maze and had nowhere to go, simply send a ":(" signal and the maze will restart."""
        )

        input("\nPress enter to continue...")

        clear_screen()
        time.sleep(0.5)
        print("\nHappy hunting, good luck...")

        for i in range(5, 0, -1):
            sys.stdout.write(f"\rStarting in {i}...")
            time.sleep(1)

    def calculate_victory_score(self):
        self.score = (100 * self.total_diamond_in_session) * self.score_multiplier

    def display_victory_result(self):
        clear_screen()

        self.calculate_victory_score()

        for row in range(self.maze_height):
            for column in range(self.maze_width):
                if column == 0:
                    print()
                print("💎\t", end="")

        print(
            f"\n\nCongratulations, {self.user_name}! Maze Level {self.level} has been conquered!"
        )
        print(
            f"You have obtained {self.total_diamond_in_session}x 💎 (Score: {self.score}) in this trip!"
        )

    def start_game(self):
        clear_screen()
        print()

        while True:
            level = int(input("Maze level (1-3): "))

            if level in (1, 2, 3):
                break

        clear_screen()
        print(f"\nMAZE - LEVEL {level}")

        self.setup_maze(level)
        self.show_maze()

        while True:
            if self.diamond_in_maze == 0:
                print()
                clear_screen()
                self.display_victory_result()
                break

            move = input("\n\nMove: ").lower()

            if self.update_maze(move) == -1:
                clear_screen()
                print(f"\nMAZE - LEVEL {level}")
                self.show_maze()
                print("\n\nInvalid move!")
                continue

            clear_screen()
            print(f"\nMAZE - LEVEL {level}")
            self.show_maze()

        result = {
            "id": self.user_id,
            "maze_level": self.level,
            "diamond": self.total_diamond_in_session,
            "score": self.score,
        }

        self.user.save_game(result)

        print("\nWould you like to re-enter the maze? (Y/N)")
        time.sleep(0.5)
        replay = input("> ").lower()

        if replay == "y":
            self.start_game()
        elif replay == "n":
            return
        else:
            time.sleep(0.5)
            print(
                "\nYou can't even spell it right, relax yourself at the bar and come back soon!"
            )
            time.sleep(1)

    def retire(self):
        clear_screen()

        print(f"Hello, {self.user_name}.")
        print(f"\nAre you sure you want to retire?")
        print(
            f"\nSo far you have achieved:\n - Rank of {self.user_rank}\n - {self.user_diamond}x 💎 with total score of {self.user_score}"
        )

        print(f"\nBestow your answer (Y/N)")
        time.sleep(0.5)

        while True:
            choice = input("> ").lower()

            if choice == "y":
                clear_screen()
                time.sleep(1)
                print("\nVery well. Blessing upon your upcoming journeys.")
                time.sleep(3)
                self.user.delete_savegame(self.user_id)
                return
            elif choice == "n":
                clear_screen()
                time.sleep(1)
                print(
                    "\nGlad to hear that, Hunter. Come to the Bar and relax yourself."
                )
                time.sleep(2)
                print("\nSee you soon...")
                time.sleep(2)
                return


USER = UserSavegame()


def main():
    clear_screen()

    # Print the game title
    f = Figlet(font="starwars")
    print(f.renderText("The Maze Hunter"))

    # Prompt user for further interactions
    print(
        "Welcome, Hunter...\n1. Start new game\n2. Load game\n3. Delete saved game\n4. See Leaderboard"
    )

    choice = int(input("\n> "))

    if choice == 1:
        session = prompt_new_user()
        session.initialize_game()
    elif choice == 2:
        session = prompt_old_user()
        session.initialize_game()
    elif choice == 3:
        session = prompt_old_user()
        session.retire()
    elif choice == 4:
        USER.display_leaderboard()
        return

    print(f"\nHave a good day, Hunter.")


def clear_screen():
    if name == "nt":
        system("cls")
    else:
        system("clear")


def is_valid_name(name):
    rgx = re.search(name_regex, name)

    if not rgx:
        return False

    return True


def is_valid_passcode(passcode):
    rgx = re.search(passcode_regex, passcode)

    if not rgx:
        return False

    return True


def hash_passcode(name, passcode):
    return hashlib.sha256(name.encode() + passcode.encode()).hexdigest()


def prompt_new_user():
    clear_screen()
    time.sleep(2)
    print("\n\nI see that you're a new Hunter, What's your name?")
    time.sleep(2)
    print("I'm sure your name is atleast consist of 4 words and no longer than 32.")
    time.sleep(1)

    # Name prompts
    name = prompt_name(is_new=True)

    clear_screen()
    time.sleep(0.5)
    print(
        "\n\nThorought the maze - there lies dazzling treasures worth of the entire world's wealth..."
    )
    time.sleep(3)
    print(
        "To keep your findings safe, bestow a secret passcode that consists of 6 numbers"
    )
    time.sleep(0.5)

    # passcode prompts
    passcode = prompt_passcode()

    USER.create_new_game(name, hash_passcode(name, passcode))
    USER.load_game(name, hash_passcode(name, passcode))

    return Maze(USER)


def prompt_old_user():
    clear_screen()
    print("\n\nWelcome back, Hunter.")
    time.sleep(0.5)

    print("\nState your name, please.")

    name = prompt_name(is_new=False)

    print("\nYour secret passcode, please.")

    passcode = prompt_passcode()

    user = USER.load_game(name, hash_passcode(name, passcode))

    if user == -1:
        clear_screen()
        print("\nThe provided name and passcode doesn't match our Hunter list...")
        print("You can't enter. Good bye and Good luck.")
        sys.exit(-1)

    return Maze(USER)


def prompt_name(is_new=False):
    while True:
        name = input("> ")

        if is_valid_name(name):
            if is_new:
                if USER.check_name_availability(name) == 0:
                    return name
                else:
                    print("\nI'm afraid another Hunter has taken that name...")
            else:
                return name
        else:
            print("\nA proper name, please - alphanumeric only\n")
            continue


def prompt_passcode():
    while True:
        passcode = input("> ")

        if is_valid_passcode(passcode):
            return passcode
        else:
            print(
                "\nYou can only present 6 numbers - 123456 is not what i'd recommend, though..."
            )



if __name__ == "__main__":
    main()
