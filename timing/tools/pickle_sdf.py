import parse_sdf
import sys, pickle

def main():
    parsed = parse_sdf.parse_sdf_file(sys.argv[1])
    with open(sys.argv[2], "wb") as pickled:
        pickle.dump(parsed, pickled)

if __name__ == '__main__':
    main()
