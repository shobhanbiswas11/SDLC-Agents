def binary_search(arr, target):
    """
    Perform binary search on a sorted array.

    :param arr: List of elements to search.
    :param target: The element to search for.
    :return: Index of the target element if found, otherwise -1.
    """
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = left + (right - left) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1

# Example usage
if __name__ == "__main__":
    array = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    target = 6
    result = binary_search(array, target)
    print(f"Element {target} is at index: {result}")