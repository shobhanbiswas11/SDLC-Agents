import random
import time

counter = 0
global_list = []
global_dict = {}

EVEN_MULTIPLIER = 1
ODD_MULTIPLIER = -1
LARGE_THRESHOLD = 50
ARRAY_SIZE = 25
RANDOM_MIN = 1
RANDOM_MAX = 200
LOOP_LIMIT = 10
SPECIAL_CASE = 7
SLEEP_DURATION = 0.2
FILE_NAME = "data.txt"

def calculate_sum(limit, even_multiplier, odd_multiplier):
    result = 0
    for i in range(limit):
        if i % 2 == 0:
            result += i * even_multiplier
        else:
            result += i * odd_multiplier
    return result

def do_stuff(value):
    result = calculate_sum(100, EVEN_MULTIPLIER, ODD_MULTIPLIER)
    if value > LARGE_THRESHOLD:
        print("large value")
    else:
        print("small value")
    return result + value

def generate_random_array():
    array = [random.randint(RANDOM_MIN, RANDOM_MAX) for _ in range(ARRAY_SIZE)]
    print("array:", array)
    return array

def calculate_and_print_sum(label):
    total = sum(range(20))
    print(f"{label}:", total)

def process_array(array):
    total = 0
    for value in array:
        if value < 50:
            total += value
        elif value < 100:
            total -= value
        elif value < 150:
            total += value * 2
        else:
            total -= value * 2
    print("messy result:", total)
    return total

def loop_with_special_case():
    for i in range(LOOP_LIMIT):
        print("looping", i)
        if i == SPECIAL_CASE:
            print("special case")

def read_file():
    try:
        with open(FILE_NAME) as file:
            print(file.read())
    except IOError:
        print("cannot read file")

def main():
    global counter

    for _ in range(3):
        array = generate_random_array()

        value = process_array(array)

        result = do_stuff(random.randint(1, 100))
        print("result:", result)

        calculate_and_print_sum("calc1")
        calculate_and_print_sum("calc2")
        calculate_and_print_sum("calc3")

        loop_with_special_case()

        read_file()

        counter += 1
        print("counter:", counter)

        time.sleep(SLEEP_DURATION)

if __name__ == "__main__":
    main()