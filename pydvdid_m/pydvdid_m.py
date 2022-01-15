from sys import argv

from pydvdid_m import DvdId


def main():
    if len(argv) == 2:
        dvd_id = DvdId(argv[1])
        if not argv[1].startswith(r"\\."):
            dvd_id.dump(argv[1])
        print(dvd_id.dumps())

        exit(0)
    print("Usage: pydvdid <path>")
    exit(1)


if __name__ == "__main__":
    main()
