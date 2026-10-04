import argparse
import csv
import os

def create_sample(input_path, output_path, max_rows):
    if max_rows < 1:
        raise ValueError("--rows must be a positive integer")
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    copied = 0
    with open(input_path, "r", encoding="utf-8-sig", errors="replace", newline="") as infile, \
         open(output_path, "w", encoding="utf-8", newline="") as outfile:
        reader, writer = csv.reader(infile), csv.writer(outfile)
        try:
            writer.writerow(next(reader))
        except StopIteration:
            raise ValueError("Input CSV is empty")
        for row in reader:
            writer.writerow(row)
            copied += 1
            if copied >= max_rows:
                break
    print(f"[Sample] created {output_path}; rows={copied}")
    return copied

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a reproducible CSV sample without loading it into memory")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="data/orders_sample.csv")
    parser.add_argument("--rows", type=int, default=100000)
    args = parser.parse_args()
    create_sample(args.input, args.output, args.rows)
