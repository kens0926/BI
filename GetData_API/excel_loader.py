import pandas as pd


def load_excel_file(path: str):
    # Excel 第一行為欄位名稱，明確使用 header=0
    df = pd.read_excel(path, header=0, dtype=str)
    df = df.fillna("")
    return df
