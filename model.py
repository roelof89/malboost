# importing
import pandas as pd
import sys

from distributed import Client, LocalCluster
from arboreto.utils import load_tf_names
from arboreto.algo import grnboost2, genie3
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
load_dotenv()

db_con = create_engine(os.getenv('SQLALCHEMY_DATABASE_URI'))

def model_execute(in_file, tf_file, out_file, opt):
    # ex_matrix is a DataFrame with gene names as column names
    e_q = f"SELECT * FROM [{in_file}]"
    ex_matrix = pd.read_sql(e_q, con=db_con)
    ex_matrix = ex_matrix.set_index(ex_matrix.columns[0])
    ex_matrix = ex_matrix.transpose()

    # tf_names is read using a utility function included in Arboreto
    t_q = f"SELECT * FROM [{tf_file}]"
    tf_names = pd.read_sql(t_q, con=db_con)
    tf_names = tf_names['genes'].tolist()

    # instantiate a custom Dask distributed Client
    client = Client(LocalCluster())

    # compute the GRN
    if opt == 'GRNBoost2':
        network = grnboost2(expression_data=ex_matrix,
                        tf_names=tf_names,
                        client_or_address=client)
    elif opt == 'GENIE3':
        network = genie3(expression_data=ex_matrix,
                        tf_names=tf_names,
                        client_or_address=client)
    else:
        network = grnboost2(expression_data=ex_matrix,
                        tf_names=tf_names,
                        client_or_address=client)
    
    # Add Pearsons
    ex_matrix = ex_matrix.corr()
    ex_matrix = ex_matrix.stack()
    ex_matrix.index = ex_matrix.index.set_names(['TF','target'])
    ex_matrix = ex_matrix.reset_index()
    ex_matrix = ex_matrix.rename({0:'corr'},axis=1)
    ex_matrix['edge'] = ex_matrix['TF'] + ":" + ex_matrix['target']
    ex_matrix = ex_matrix.sort_values('edge').reset_index(drop=True)

    # Merge correlation to network
    network['edge'] = network['TF'] + ":" + network['target']
    network = network.sort_values('edge').reset_index(drop=True)
    network['corr'] = network.merge(ex_matrix, how='left', on='edge')['corr']
    network = network.drop('edge',axis=1)

    # write the GRN to file
    network.to_sql(name=out_file, con=db_con, if_exists='replace',index=False)
