from random import randint


def fisher_yates_shuffle(arr):
    for i in range(len(arr) - 1, 0, -1):
        j = randint(0, i)  # Random index from 0 to i
        arr[i], arr[j] = arr[j], arr[i]  # Swap elements

    return arr


def shuffle_list(list_arg):

    len_arg = len(list_arg)  # Length of the argument

    new_list = [None for i in range(len_arg)]  # New array of the same length
    numbers_used = []  # Array to store used random numbers

    for elem in list_arg:  # Go through the elements
        new_pos = randint(0, len_arg-1)  # New randomized position

        if new_pos in numbers_used:  # If position was used before
            for ind in range(len_arg):  # Go through indices
                if new_list[ind] is None:  # If this position is not taken
                    new_list[ind] = elem  # Put the element into the new array
                    numbers_used.append(ind)  # Note that we have already used this index
                    # print(f"Inserting element {elem} to position {ind}")  # DEBUGGING
                    break  # Exit the loop

        else:
            new_list[new_pos] = elem  # Put the element into the new array
            # print(f"Inserting element {elem} to position {new_pos}")  # DEBUGGING
            numbers_used.append(new_pos)  # Note that we have already used this index

    return new_list  # Return the new array





