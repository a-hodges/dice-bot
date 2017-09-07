#!/usr/bin/env python3

import operator
import re

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


def parse_number(num):
    '''
    Converts a string to an int if possible,
    otherwise float if possible,
    otherwise returns the original string
    '''
    try:
        return int(num)
    except ValueError:
        try:
            return float(num)
        except ValueError:
            return num


def tokenize(equation):
    '''
    Tokenizes an infix equation to create a list
    '''
    # things to split by
    text = r'[a-zA-Z]+'
    num = r'(?<!\d)-?\d*\.?\d+'
    parens = r'[()]'
    #
    stack = re.split('({}|{}|{})'.format(text, num, parens), equation)
    stack = filter(None, stack)
    stack = map(parse_number, stack)
    return list(stack)


def infix2postfix(
        equation,
        operations=operations,
        order_of_operations=order_of_operations):
    '''
    Converts a tokenized infix equation to postfix
    '''
    equation = list(equation)
    stack = []
    output = []

    for item in equation:
        if isinstance(item, int):
            output.append(item)
        elif item == '(':
            stack.append(item)
        elif item == ')':
            if '(' not in stack:
                raise EquationError('Invalid equation: {}'.format(equation))
            while stack[-1] != '(':
                output.append(stack.pop())
            stack.pop()
        elif item in operations:
            higher_or_equal_priority = []
            ops = iter(order_of_operations)
            line = next(ops)
            try:
                while item not in line:
                    higher_or_equal_priority.extend(line)
                    line = next(ops)
            except StopIteration:
                raise SyntaxError('Operator and Order of Operations mismatch')

            while stack and stack[-1] in higher_or_equal_priority:
                output.append(stack.pop())
            stack.append(item)
        else:
            raise EquationError('Invalid character found: {} in {}'.format(
                item, equation))

    if '(' in stack:
        raise EquationError('Invalid equation: {}'.format(equation))

    while stack:
        output.append(stack.pop())

    return output


def solve_postfix(
        equation,
        operations=operations,
        order_of_operations=order_of_operations):
    '''
    Solves a tokenized postfix equation
    '''
    equation = list(equation)
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
    '''
    Runs equation2list, infix2postfix, and solve_postfix in order
    '''
    equation = tokenize(equation)
    postfix = infix2postfix(equation, operations, order_of_operations)
    value = solve_postfix(postfix, operations, order_of_operations)
    return value

if __name__ == '__main__':
    print(solve(input()))
