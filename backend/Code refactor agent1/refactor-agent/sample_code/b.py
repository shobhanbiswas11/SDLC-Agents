import random, math

initial_value = 0
upper_limit = 10
data_label = "data"
data_list = []
data_dict = {}

def function_one(input_value):
    total = 0

def function_three():
    print("start function_three")
    for i, j in ((i, j) for i in range(5) for j in range(5)):
        print(i, j)
    print("end function_three")
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    output = []
    for number in numbers:
        output.append(math.sqrt(number))
    print(output)

def perform_duplicate_task(prefix):
    sum_result = 0
    for i in range(100):
        sum_result += i
    print(prefix, sum_result)

def duplicate1():
    perform_duplicate_task("d1")

def duplicate2():
    perform_duplicate_task("d2")

def duplicate3():
    perform_duplicate_task("d3")

def weird():
    counter = 0
    while counter < 10:
        random_number = random.randint(0, 100)
        if random_number % 2 == 0:
            print("even", random_number)
        else:
            print("odd", random_number)
        counter += 1

def pointless():
    squares = []
    for i in range(50):
        squares.append(i * i)
    print(squares)

def globals_change():
    global initial_value, upper_limit
    for i in range(5):
        initial_value += i
        upper_limit -= i
    print("globals", initial_value, upper_limit)

def fake_menu():
    print("1 run")
    print("2 compute")
    print("3 loop")
    print("4 quit")

def main():
    running = True
    while running:
        fake_menu()
        choice=random.randint(1,4)

        if choice==1:
            print("running f1")
            print(f1(random.randint(1,10)))

        try:
            read("input.txt")
        except IOError as e:
            print(f"Error reading file: {e}")

        try:
            write("output.txt")
        except IOError as e:
            print(f"Error writing file: {e}")