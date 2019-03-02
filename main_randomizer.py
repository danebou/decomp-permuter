

from compiler import Compiler
from scorer import Scorer
from randomizer import Randomizer
import sys
from pycparser import parse_file

filename = sys.argv[1]
target_o = sys.argv[2]
compile_cmd = sys.argv[3]

assert target_o.endswith('.o')

compiler = Compiler(compile_cmd, False)
scorer = Scorer(target_o)

def score(source):
    cand_o = compiler.compile(source)
    return scorer.score(cand_o)

ctr = 0
def write_high_scorer(source):
    global ctr
    while True:
        ctr += 1
        try:
            fname = f'output-{ctr}.c'
            with open(fname, 'x') as f:
                f.write(source)
            break
        except FileExistsError:
            pass
    print(f"wrote to {fname}")

def main():
    start_ast = parse_file(filename, use_cpp=False)
    randomizer = Randomizer(start_ast)
    source = randomizer.get_current_source()
    base_score, base_hash = score(source)
    hashes = {base_hash}
    if base_score == scorer.PENALTY_INF:
        print("unable to compile original .c file")
        exit(1)
    print(f"base score = {base_score}")

    iteration = 0
    errors = 0
    while True:
        randomizer.permute()
        source = randomizer.get_current_source()
        new_score, new_hash = score(source)
        iteration += 1
        if new_hash is None:
            errors += 1
        disp_score = 'inf' if new_score == scorer.PENALTY_INF else new_score
        sys.stdout.write("\b"*10 + " "*10 + f"\riteration {iteration}, {errors} errors, score = {disp_score}")
        sys.stdout.flush()
        if new_score < base_score or (new_score == base_score and new_hash not in hashes):
            hashes.add(new_hash)
            print()
            if new_score < base_score:
                print("found a better score!!")
            else:
                print("found different asm with same score", new_hash)

            source = randomizer.get_current_source()
            write_high_scorer(source)

main()