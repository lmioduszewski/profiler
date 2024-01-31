import duckdb
from pathlib import Path
import pandas as pd
import numpy as np

explo_database = Path.home() / "Python\Projects\qgis-plugin-xsections\Exploration_Database.csv"
"""explo_database = pd.read_csv(explo_database)
explo_database = explo_database.iloc[1:, :]
explo_database[explo_database == '--'] = np.nan
explo_database = explo_database.iloc[:111, :]"""

with duckdb.connect("file.db") as con:
    # con.from_df(explo_database).create('explo')
    # print(con.table('explo'))
    con.execute("SELECT COUNT(*) from explo WHERE exploration LIKE 'EB-%'")
    print(con.fetchall())

