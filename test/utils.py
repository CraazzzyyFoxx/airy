from random import randint

# minimum = int(input('Введите минимальное число:'))
# maximum = int(input('Введите максимальное число:'))
# quantity = int(input('Введите кол-во случайных чисел:'))
#
# print('Вывод случайных целых чисел:')
# arr = [randint(minimum, maximum) for i in range(0, quantity)]
# print(arr)


def find_min_max(iterable: list) -> tuple[int, int]:
    return min(iterable), max(iterable)