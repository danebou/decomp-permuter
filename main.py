import perm
from pathlib import Path
import argparse

def permuate(filename, func):
    original_c_source = Path(filename).read_text()
    p = perm.perm_gen(original_c_source)
    for permutation in perm.perm_evaluate_all(p):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Permuate')
    parser.add_argument('filename', type=str,
                        help='')
    parser.add_argument('func', type=str,
                        help='')

    args = parser.parse_args()
    permuate(args.filename, args.func)