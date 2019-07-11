import hashlib

def first_item(obj):
    if isinstance(obj, list):
        return first_item(obj[0])
    elif isinstance(obj, dict):
        return first_item(next(iter(obj.values())))
    else:
        return obj


def recursive_items(dictionary):
    # https://stackoverflow.com/questions/39233973/get-all-keys-of-a-nested-dictionary
    for key, value in dictionary.items():
        yield (key, value)
        if isinstance(value, dict):
            yield (key, value)
            yield from recursive_items(value)
        elif isinstance(value, list) and any([isinstance(item, dict) for item in value]):
            for item in value:
                if isinstance(item, dict):
                    yield from recursive_items(item)


def apply_func(obj, func):
    # https://stackoverflow.com/questions/32935232/python-apply-function-to-values-in-nested-dictionary
    def comp_helper(x):
        if isinstance(x, dict):
            return apply_func(x, func)
        else:
            return func(x)

    if isinstance(obj, dict):
        return {key: apply_func(value, func) for key, value in obj.items()}
    elif isinstance(obj, list):
        # The obj is a list and there's a dictionary in there somewhere
        return [comp_helper(item) for item in obj]
    else:
        return func(obj)


def hash(row):
    m = hashlib.md5()
    m.update(bytes(row.name.strftime('%Y-%m-%d'), encoding='UTF-8', errors='strict'))
    m.update(bytes(row['Description'], encoding='UTF-8', errors='strict'))
    m.update(bytes(
        int(row['Amount'] * 100).to_bytes(24, byteorder='big', signed=True)
    ))
    return m.hexdigest()
