# importing
import pandas as pd
import sys

from distributed import Client, LocalCluster
from arboreto.utils import load_tf_names
from arboreto.algo import grnboost2, genie3
from sqlalchemy import create_engine

try:
    db_con = create_engine('sqlite:///data/GRNBoost2.db')
    names = pd.read_sql("select name from sqlite_master where type = 'table'", db_con)

    for table in names['name'].tolist():
        if table == 'results_request':
            pass
        else:
            q = f"DROP TABLE [{table}]"
            db_con.execute(q)
except:
    pass

