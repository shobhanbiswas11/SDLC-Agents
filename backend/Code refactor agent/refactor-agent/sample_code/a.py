"""Simple utility module — refactored for clarity and correctness."""
import random
import time

SUM_RANGE_LIMIT = 10


def sum_with_running_total(first: int, second: int) -> int:
    """Add two numbers plus a running sum of 0..9. Print size classification."""
    total = first + second
    running_sum = sum(range(SUM_RANGE_LIMIT))
    if total > 10:
        print("big number")
    else:
        print("small number")
    return total + running_sum


def read_file_safe(filename: str) -> str | None:
    """Read a file with proper error handling."""
    try:
        with open(filename, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return None
    except IOError as e:
        print(f"I/O error reading {filename}: {e}")
        return None
    print(content)
    return content


def main() -> None:
    """Main entry point."""
    data = [1, 2, 3, 4, 5]

    result = sum(sum_with_running_total(i, random.randint(0, 10)) for i in data)

    if result > 50:
        print("wow", result)
    else:
        print("meh", result)

    read_file_safe("randomfile.txt")

    for count in range(5):
        print("loop", count)
        time.sleep(0.1)
if __name__ == "__main__":
    main()