from pathlib import Path

import pandas as pd

from src.utils.normalization import normalize_physics_scientific_text


def resolve_physics_csv() -> Path:
	candidates = [Path.cwd() / "data" / "physics.csv", Path.cwd() / "data" / "physics.csv"]
	candidates += [parent / "data" / "physics.csv" for parent in Path.cwd().parents]
	for candidate in candidates:
		if candidate.exists():
			return candidate
	raise FileNotFoundError("physics.csv not found from current working directory")


def collect_unique_chars(frame: pd.DataFrame) -> str:
	chars = set()
	for col in frame.columns:
		for value in frame[col]:
			chars.update(value)
	return "".join(sorted(chars))


def main() -> None:
	csv_path = resolve_physics_csv()
	df = pd.read_csv(csv_path)

	text_cols = df.select_dtypes(include=["object", "string"]).columns
	text_data = df[text_cols].fillna("").astype(str)

	unique_chars_before = collect_unique_chars(text_data)

	df_norm = df.copy()
	for col in text_cols:
		df_norm[col] = df_norm[col].fillna("").astype(str).map(normalize_physics_scientific_text)

	unique_chars_after = collect_unique_chars(df_norm[text_cols])

	diff_mask = df_norm[text_cols] != text_data
	changed_rows = diff_mask.any(axis=1).sum()

	print(f"Unique chars before: {len(unique_chars_before)}")
	print(unique_chars_before)
	print(f"Unique chars after: {len(unique_chars_after)}")
	print(unique_chars_after)
	print(f"Rows with changes: {changed_rows}")

	if changed_rows:
		sample = pd.concat(
			{
				"before": df.loc[diff_mask.any(axis=1), text_cols].head(5),
				"after": df_norm.loc[diff_mask.any(axis=1), text_cols].head(5),
			},
			axis=0,
		)
		print(sample.to_string())

	output_path = csv_path.parent / "processed" / "physics.csv"
	output_path.parent.mkdir(parents=True, exist_ok=True)
	df_norm.to_csv(output_path, index=False)
	print(output_path.as_posix())


if __name__ == "__main__":
	main()
