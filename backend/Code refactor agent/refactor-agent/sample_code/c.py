import random

MAGIC_NUMBER_10 = 10
MAGIC_NUMBER_20 = 20
MAGIC_NUMBER_30 = 30
MAGIC_NUMBER_50 = 50
MAGIC_NUMBER_100 = 100
MAGIC_NUMBER_5 = 5

def x(a):
    b = sum(range(MAGIC_NUMBER_50))
    if a > MAGIC_NUMBER_10:
        print("high")
    else:
        print("low")
    return a + b

def y():
    arr = [random.randint(0, MAGIC_NUMBER_100) for _ in range(MAGIC_NUMBER_20)]
    total = sum(arr)
    print("total:", total)
    return total

def z():
    print("z running")
    for i in range(MAGIC_NUMBER_5):
        print("i =", i)

def fileStuff():
    try:
        with open("a.txt", "r") as f:
            print(f.read())
    except FileNotFoundError:
        print("no file")

    try:
        with open("b.txt", "w") as f:
            for i in range(MAGIC_NUMBER_5):
                f.write(f"line {i}\n")
    except IOError:
        print("Error writing to file")

def weirdLogic(choice):
    for i in range(MAGIC_NUMBER_10):
        r = random.randint(0, MAGIC_NUMBER_50)
        if r < MAGIC_NUMBER_10:
            print("small", r)
        elif r < MAGIC_NUMBER_30:
            print("medium", r)
        else:
            print("large", r)

        if choice == 1:
            r = x(random.randint(1, MAGIC_NUMBER_20))
            print("result:", r)
        elif choice == 2:
            y()
        elif choice == 3:
            z()
        elif choice == 4:
            return

def main():
    choice = random.randint(1, 4)
    weirdLogic(choice)
    fileStuff()

if __name__ == "__main__":
    main()