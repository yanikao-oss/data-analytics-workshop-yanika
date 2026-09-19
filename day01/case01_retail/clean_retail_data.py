from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent
INPUT_PATH = BASE_DIR / "data" / "retail_sales_dirty.csv"
OUTPUT_PATH = BASE_DIR / "data" / "retail_sales_cleaned.csv"
REVIEW_PATH = BASE_DIR / "data" / "retail_sales_quality_review.csv"


def main() -> None:
    data = pd.read_csv(INPUT_PATH)
    review_rows = []

    def record(row_number: int, issue: str, action: str) -> None:
        review_rows.append(
            {
                "csv_data_row": row_number,
                "issue": issue,
                "action": action,
            }
        )

    # Normalize categorical values using the observed canonical spellings.
    region_before = data["Region"].copy()
    data["Region"] = data["Region"].str.strip().str.title()
    for index in data.index[region_before != data["Region"]]:
        record(index + 2, "Region format inconsistency", "Normalized to title case")

    category_before = data["Category"].copy()
    data["Category"] = data["Category"].replace({"Electronic": "Electronics"})
    for index in data.index[category_before != data["Category"]]:
        record(index + 2, "Category spelling inconsistency", "Electronic -> Electronics")

    # P-A is Home in every other observed record; correct the single conflicting row.
    product_category_mask = (data["Product"] == "P-A") & (data["Category"] == "Electronics")
    for index in data.index[product_category_mask]:
        data.at[index, "Category"] = "Home"
        record(index + 2, "Product-category mismatch", "P-A -> Home based on the observed product mapping")

    # Reconstruct missing derived values only where the arithmetic inputs exist.
    missing_sales = data["Sales"].isna() & data["Cost"].notna() & data["Profit"].notna()
    data.loc[missing_sales, "Sales"] = data.loc[missing_sales, "Cost"] + data.loc[missing_sales, "Profit"]
    for index in data.index[missing_sales]:
        record(index + 2, "Missing Sales", "Calculated as Cost + Profit")

    missing_profit = data["Profit"].isna() & data["Sales"].notna() & data["Cost"].notna()
    data.loc[missing_profit, "Profit"] = data.loc[missing_profit, "Sales"] - data.loc[missing_profit, "Cost"]
    for index in data.index[missing_profit]:
        record(index + 2, "Missing Profit", "Calculated as Sales - Cost")

    # Remove only exact duplicate records; repeated business keys are retained.
    duplicate_mask = data.duplicated(keep="first")
    for index in data.index[duplicate_mask]:
        record(index + 2, "Exact duplicate row", "Removed duplicate")
    data = data.loc[~duplicate_mask].reset_index(drop=True)

    # These values need business confirmation and are intentionally preserved.
    for index in data.index[data["Quantity"] < 0]:
        record(index + 2, "Negative Quantity", "Preserved; confirm return/adjustment or correction")
    for index in data.index[data["Discount"] > 1]:
        record(index + 2, "Discount outside 0-1 range", "Preserved; confirm unit or source value")

    data.to_csv(OUTPUT_PATH, index=False)
    pd.DataFrame(review_rows).to_csv(REVIEW_PATH, index=False)
    print(f"cleaned_rows={len(data)}")
    print(f"review_items={len(review_rows)}")
    print(f"output={OUTPUT_PATH}")
    print(f"review={REVIEW_PATH}")


if __name__ == "__main__":
    main()