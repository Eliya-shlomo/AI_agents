from nt import error


def twosum(arr,target):
    seen = {}

    for i in range(len(arr)):

        num = arr[i]
        complement = target - arr[i]

        if complement in seen:
            return [seen[complement],i]

        
        seen[num] = i

    return -1


def subarray(arr):
    if len(arr) == 0:
        return error('empty arr')
    
    best = arr[0]
    current = arr[0]    

    for i in range(1,len(arr)):

        current = max(arr[i],current+arr[i])

        if current > best:
            best = current

    return best


def Valid_Parentheses(s):
    if len(s) == 0:
        raise ValueError('String is empty')

    mapping = {")": "(", "]": "[", "}": "{"}
    stack = []

    for char in s:
        if char in mapping:
            top_element = stack.pop() if stack else '#'
            
            if mapping[char] != top_element:
                return False
        else:
            stack.append(char)


    return len(stack) == 0