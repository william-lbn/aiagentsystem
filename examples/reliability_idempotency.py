seen = {}


def effect(key, amount):
    if key in seen:
        return {"deduplicated": True, "result": seen[key]}
    seen[key] = {"charged": amount}
    return {"deduplicated": False, "result": seen[key]}


print(effect("k-1", 10))
print(effect("k-1", 10))
