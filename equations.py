#!/usr/bin/env python3

import math
import operator

operations = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.floordiv,
    '^': operator.pow,
}
order_of_operations = [
    ['^'],
    ['*', '/'],
    ['+', '-'],
]


class EquationError (Exception):
    pass


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
            ops = iter(order_of_operations)
            line = next(ops)
            while item not in line:
                higher_or_equal_priority.extend(line)
                line = next(ops)

            while stack[-1] in higher_or_equal_priority:
                output.append(stack.pop())
            stack.append(item)
        else:
            raise EquationError('Invalid character found: {} in {}'.format(
                item, equation))

    if len(stack) != 0:
        raise EquationError('Invalid equation: {}'.format(equation))

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
                raise EquationError('Not enough operands for {} in {}'.format(
                    item, equation))
            else:
                b = stack.pop()
                a = stack.pop()
                stack.append(operations[item](a, b))
        else:
            raise EquationError('Invalid operand/operator: {} in '.format(
                item, equation))

    if len(stack) != 1:
        raise EquationError('Invalid equation: {}'.format(equation))

    return stack[0]


def solve(
        equation,
        operations=operations,
        order_of_operations=order_of_operations):
    stack = []
    equation = equation.replace(' ', '')
    for i, c in enumerate(equation):
        if c.isdigit():
            if stack and isinstance(stack[-1], (int, float)):
                stack[-1] = stack[-1] * 10 + int(
                    math.copysign(int(c), stack[-1]))
                # poor way to handle the negatives
                if stack and isinstance(stack[-1], float):
                    stack[-1] = int(stack[-1])
            else:
                stack.append(int(c))
        # poor way to handle the negatives
        elif c == '-' and (
                i == 0 or
                stack[-1] == '(' or
                stack[-1] in operations):
            stack.append(-0.0)
        elif (stack and
                not isinstance(stack[-1], int) and
                not stack[-1] in ['(', ')']):
            stack[-1] += c
        else:
            stack.append(c)

    postfix = infix2postfix(stack, operations, order_of_operations)
    value = solve_postfix(postfix, operations, order_of_operations)
    return value

if __name__ == '__main__':
    print(solve(input()))
