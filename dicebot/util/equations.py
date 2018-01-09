'''
An extensible module for evaluation of arbitrary mathematical expressions
'''

import operator
import re

operations = [
    {
        '+': operator.add,
        '-': operator.sub,
    },
    {
        '*': operator.mul,
        '/': operator.truediv,
        '//': operator.floordiv,
        '%': operator.mod,
    },
    {
        '^': operator.pow,
    },
]

unary = {
    '+': operator.pos,
    '-': operator.neg,
    '~': operator.neg,
}


class EquationError (Exception):
    pass


def types(stack):
    '''
    Gets the types list from a token list
    '''
    return next(zip(*stack)) if stack else []


def tokenize(expression, operations=operations, unary=unary):
    '''
    Parses a mathematic expression into tokens
    '''
    def token(t):
        def callback(scanner, match):
            return t, match
        return callback
    operators = {op for ops in operations for op in ops}
    unary_operators = [op for op in unary if op not in operators]
    tokens = [(r'\s+', 'WHITESPACE')]
    tokens.extend((r'|'.join(map(re.escape, ops)), i) for i, ops in enumerate(operations))
    tokens.append((r'|'.join(map(re.escape, unary_operators)), 'UNARY'))
    tokens.extend([
        (r'-', len(operations)),  # ???
        (r'\d*\.\d+', 'FLOAT'),
        (r'\d+', 'INT'),
        (r'\(', 'PAREN_OPEN'),
        (r'\)', 'PAREN_CLOSE'),
    ])
    scanner = re.Scanner([(p, token(t)) for p, t in tokens])
    out, rest = scanner.scan(expression)
    if rest:
        raise ValueError('Could not parse equation from: {}'.format(rest))
    return [(t, m) for t, m in out if t != 'WHITESPACE']


def infix2postfix(expression, operations=operations, unary=unary):
    '''
    Converts an infix expression to a postfix token list
    '''
    equation = tokenize(expression, operations=operations, unary=unary)
    stack = []
    output = []

    prev_type = -1
    for item in equation:
        type, token = item
        if type in ('INT', 'FLOAT'):
            output.append(item)
        elif type == 'PAREN_OPEN':
            stack.append(item)
        elif type == 'PAREN_CLOSE':
            if 'PAREN_OPEN' not in types(stack):
                raise EquationError('Missing open parenthesis: {}'.format(expression))
            while stack[-1][0] != 'PAREN_OPEN':
                output.append(stack.pop())
            stack.pop()
        elif type == 'UNARY':
            stack.append(item)
        elif isinstance(type, int):  # operators
            if prev_type == 'PAREN_OPEN' or isinstance(prev_type, int):
                # unary operation
                stack.append(('UNARY', token))
            else:
                while stack and isinstance(stack[-1][0], int) and stack[-1][0] >= type:
                    output.append(stack.pop())
                stack.append(item)
        else:
            raise EquationError('Invalid token found: {} in {}'.format(token, equation))
        prev_type = type

    if 'PAREN_OPEN' in types(stack):
        raise EquationError('Missing closing parenthesis: {}'.format(expression))

    while stack:
        output.append(stack.pop())

    return output


def solve(expression, operations=operations, unary=unary):
    '''
    Solves an infix expression

    Operations is a list of operation dicts in reverse precedence order
        The keys of each dict should be the operator and the values should be
        a binary function to apply to the operands
        The functions should be able to take int or float arguments
    
    Unary is a dict of unary operations
        The keys of the dict should be the operator and the values should be
        a unary function to apply to the operands
        The functions should be able to take int or float arguments
    '''
    equation = infix2postfix(expression, operations=operations, unary=unary)
    stack = []

    for type, token in equation:
        # print(equation, stack, token, sep='\n')
        if type == 'INT':
            stack.append(int(token))
        elif type == 'FLOAT':
            stack.append(float(token))
        elif type == 'UNARY':
            if len(stack) < 1:
                raise EquationError('Not enough operands for unary {} in {}'.format(token, expression))
            else:
                stack.append(unary[token](stack.pop()))
        elif isinstance(type, int):
            if len(stack) < 2:
                raise EquationError('Not enough operands for {} in {}'.format(token, expression))
            else:
                b, a = stack.pop(), stack.pop()
                stack.append(operations[type][token](a, b))
        else:
            raise EquationError('Invalid token: {} in {}'.format(token, expression))

    if len(stack) != 1:
        raise EquationError('Too many operands for operators in {}'.format(expression))

    return stack[0]


if __name__ == '__main__':
    print(solve(input('Eq: ')))
