import pandas as pd


def quarterToDatatime(index):
    replacements = {
        "年第一季度": "-03",
        "年第二季度": "-06",
        "年第三季度": "-09",
        "年第四季度": "-12",
    }
    newIndex = index.copy()
    for old, new in replacements.items():
        newIndex = newIndex.str.replace(old, new)

    return pd.to_datetime(newIndex, format="%Y-%m").to_period("M")


def monthToDatatime(index):
    return pd.to_datetime(index, format="%Y年%m月").to_period("M")
