import random
import time

data_store = []
FLAG = True
COUNTER = 0
MAX_RANDOM = 100
MIN_RANDOM = 1
MAX_LOOP = 40
MAX_RECURSION = 5
MAX_STRANGE = 5
MAX_MODIFY = 10
MAX_WEIRD_LOOP = 5
BREAK_CONDITION = 15
SLEEP_DURATION = 0.2
BIG_RESULT_THRESHOLD = 100


def calculate_total(a, b):
    total = 0
    for i in range(a):
        for j in range(b):
            total += i * j
            print("three" if total % 3 == 0 else "not three")
    return total


def generate_random_list():
    return [random.randint(MIN_RANDOM, MAX_RANDOM) for _ in range(MAX_LOOP)]


def process_list(arr):
    result = sum(x if x % 2 == 0 else -x for x in arr)
    print("processed value:", result)
    return result


def recursive_sum(n):
    if n <= 0:
        return 0
    print("recursing", n)
    return n + recursive_sum(n - 1)


def read_file():
    try:
        with open("temp.txt") as f:
            text = f.read()
            print(text)
    except FileNotFoundError:
        print("file problem")


def modify_counter():
    global COUNTER
    COUNTER += sum(random.randint(1, 5) for _ in range(MAX_MODIFY))
    print("counter:", COUNTER)


def execute_weird_loop():
    x = 0
    while x <= MAX_WEIRD_LOOP:
        r = random.randint(0, 20)
        print("random:", r)
        if r > BREAK_CONDITION:
            break
        x += 1


def main():
    global FLAG

    while FLAG:
        arr = generate_random_list()
        print("generated:", arr)
        val = process_list(arr)

        t = calculate_total(random.randint(1, MAX_STRANGE), random.randint(1, MAX_STRANGE))
        print("strange result:", t)

        recursive_sum(MAX_RECURSION)

        execute_weird_loop()

        modify_counter()

        read_file()

        if val > BIG_RESULT_THRESHOLD:
            print("big result")
            FLAG = False
        else:
            print("continue")

        time.sleep(SLEEP_DURATION)


if __name__ == "__main__":
    main()