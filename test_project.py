from project import is_valid_name, is_valid_passcode, hash_passcode, UserSavegame, Maze

def test_name_input():

    assert is_valid_name("John") == True
    assert is_valid_name("John Doe") == False
    assert is_valid_name("Scary@Hunter") == False
    assert is_valid_name("1a") == False

def test_passcode_input():

    assert is_valid_passcode("123456") == True
    assert is_valid_passcode("111") == False
    assert is_valid_passcode("cat") == False

def test_hash_passcode():

    assert hash_passcode("John", "123456") == "bace68308735a7033efeaf5aed0a3b2bbe0e27ecf77903fddb7cf09744dfa200"

def test_score_calculation():

    user = UserSavegame()

    user.user_id = 1
    user.name = "John"
    user.diamond = 1
    user.score = 100
    user.rank = "Newbie"

    maze = Maze(user)

    maze.total_diamond_in_session = 1
    maze.score_multiplier = 1

    maze.calculate_victory_score()

    assert maze.score == 100
