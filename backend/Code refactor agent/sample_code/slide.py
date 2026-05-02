def max_sum_subarray(arr, k):
    """Find the maximum sum of a subarray of size k using the sliding window technique."""
    if len(arr) < k:
        return None

    # Calculate the sum of the first window
    window_sum = sum(arr[:k])
    max_sum = window_sum

    # Slide the window from start to end of the array
    for i in range(len(arr) - k):
        window_sum = window_sum - arr[i] + arr[i + k]
        max_sum = max(max_sum, window_sum)

    return max_sum

# Example usage
print(max_sum_subarray([1, 2, 3, 4, 5, 6, 7, 8, 9], 3))  # Output: 24