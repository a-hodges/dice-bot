#!/usr/bin/env python3

operations = {
    '+': lambda a, b: a + b,
    '-': lambda a, b: a - b,
    '*': lambda a, b: a * b,
    '/': lambda a, b: a / b,
    '^': lambda a, b: a ** b,
}
order_of_operations = [
    ['^'],
    ['*', '/'],
    ['+', '-'],
]


def infix2postfix(
        equation,
        operations=operations,
        order_of_operations=order_of_operations):
    equation.append(')')
    stack = ['(']
    output = []

    for item in equation:
        if isinstance(item, int):
            output.append(item)
        elif item == '(':
            stack.append(item)
        elif item == ')':
            while stack[-1] != '(':
                output.append(stack.pop())
            stack.pop()
        elif item in operations:
            higher_or_equal_priority = []
            for line in order_of_operations:
                higher_or_equal_priority.extend(line)
                if item in line:
                    break
            while stack[-1] in higher_or_equal_priority:
                output.append(stack.pop())
            stack.append(item)
        else:
            raise ValueError('Invalid character found: {} in {}'.format(
                item, equation))

    if len(stack) != 0:
        raise ValueError('Invalid equation: {}'.format(equation))

    return output


def solve_postfix(
        equation,
        operations=operations,
        order_of_operations=order_of_operations):
    stack = []

    for item in equation:
        if isinstance(item, int):
            stack.append(item)
        elif item in operations:
            if len(stack) < 2:
                raise ValueError('Not enough operands for {} in {}'.format(
                    item, equation))
            else:
                b = stack.pop()
                a = stack.pop()
                stack.append(operations[item](a, b))
        else:
            raise ValueError('Invalid operand/operator: {} in '.format(
                item, equation))

    if len(stack) != 1:
        raise ValueError('Invalid equation: {}'.format(equation))

    return stack[0]


def solve(
        equation,
        operations=operations,
        order_of_operations=order_of_operations):
    stack = []
    equation = equation.replace(' ', '')
    for c in equation:
        if c.isdigit():
            if stack and isinstance(stack[-1], int):
                stack[-1] = stack[-1] * 10 + int(c)
            else:
                stack.append(int(c))
        else:
            stack.append(c)

    postfix = infix2postfix(stack, operations, order_of_operations)
    value = solve_postfix(postfix, operations, order_of_operations)
    return value

if __name__ == '__main__':
    print(solve(input()))
