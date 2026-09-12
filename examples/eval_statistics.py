import random

random.seed(7)
a = [1, 1, 0, 1, 0, 1, 1, 0, 1, 1]
b = [1, 1, 1, 1, 0, 1, 1, 1, 1, 1]
print(
    {
        "A_pass_rate": sum(a) / len(a),
        "B_pass_rate": sum(b) / len(b),
        "paired_improvements": sum(x < y for x, y in zip(a, b)),
    }
)
