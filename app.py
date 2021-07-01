# Make a Flask website for running GRNBoost2 on transcriptomes
from logging import error
from flask import Flask, request, redirect, render_template, jsonify, make_response, send_file, url_for
from flask_mail import Mail, Message, Attachment
from flask_sqlalchemy import SQLAlchemy
from flask_celery import make_celery
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from werkzeug.utils import secure_filename
from io import BytesIO
from sklearn.linear_model import LinearRegression
import pickle

# Control handlers
import uuid
import datetime
import pandas as pd
import os
from dotenv import load_dotenv
import sys
import ast
from itertools import chain
import re

# External python models
from model import model_execute

# App configuration
app = Flask(__name__)
load_dotenv()

app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'thisissecret'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

db_con = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

app_url = os.getenv('app_url')
app.config['CELERY_BROKER_URL'] = os.getenv('CELERY_BROKER_URL')
app.config['CELERY_RESULT_BACKEND'] = os.getenv('CELERY_RESULT_BACKEND')

# File archive configurations
app.config['FILE_UPLOADS'] = "data/uploads/"
app.config['FILE_RESULTS'] = "data/results/"
app.config['ALLOWED_FILE_EXTENSIONS'] = ["TXT", "TSV", "CSV"]

celery = make_celery(app)
db = SQLAlchemy(app)

class ResultsRequest(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    request_no      = db.Column(db.String(2000), unique=True)
    email           = db.Column(db.String(100))
    url             = db.Column(db.String(500))
    request_time    = db.Column(db.DateTime)
    complete_time   = db.Column(db.DateTime)
    run_time        = db.Column(db.Float)
    status          = db.Column(db.String(100))
    error           = db.Column(db.String(2000))
    downloaded      = db.Column(db.Boolean)

# Estimate
loaded_model = pickle.load(open('estimate.sav', 'rb'))

def estimate_time(loaded_model, X):
    est = loaded_model.predict(X)
    return est

# Schedular
def truncateResults():
    cnx = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

    try:
        requests = pd.read_sql("SELECT request_no FROM results_request WHERE complete_time <= date('now','-3 day')", cnx)
        requests = requests['request_no'].tolist()

        for f in requests:
            name = "table_" + str(f) + "_RES"
            try:
                q = f"DROP TABLE [{name}]"
                cnx.execute(q)
            except:
                pass
            try:
                os.remove('tmp_'+str(f)+'.txt')
            except:
                print(f"File {f} not found!")
    except:
        pass

    String_sql = "DELETE FROM results_request WHERE complete_time <= date('now','-3 day')"
    try:
        cnx.execute(String_sql)
    except:
        pass

scheduler = BackgroundScheduler()
job = scheduler.add_job(truncateResults, 'interval', minutes=720)
scheduler.start()

def special_char(gene):
    r = re.compile(r'[ !@#%&*+-]')
    r2 = re.compile(r'[\:";<>,./()[\]{}\']')
    if r.search(gene) or r2.search(gene):
        return True

def allowed_files(filename):

    if not "." in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1]

    if ext.upper() in app.config['ALLOWED_FILE_EXTENSIONS']:
        return True
    else:
        return False

def file_loader_expression(_file):

    ext = _file.filename.rsplit('.',1)[1]

    if ext.upper() == 'TXT' or ext.upper() == 'TSV':
        try:
            df = pd.read_csv(_file, sep='\t', index_col=0)
        except Exception as e:
            print(f"Expression file {_file.filename} did not read")
            print(e)
    elif ext.upper() == 'CSV':
        try:
            df = pd.read_csv(_file, index_col=0)
        except Exception as e:
            print(f"Expression file {_file.filename} did not read")
            print(e)
    df.index = df.index.str.upper()
    return df

def col_numeric(df):
    numerics = ['int16', 'int32', 'int64', 'float16', 'float32', 'float64']
    try:
        df = df.apply(lambda s: pd.to_numeric(s, errors='coerce'))
        df = df.fillna(0)
        return df
    except Exception as e:
        print(e)
        num_cols = df.select_dtypes(include=numerics).columns
        char_cols = [x for x in df.columns if x not in num_cols]
        error = f"Columns not numeric: {', '.join(char_cols)}"
        return error

#######
# email functions
def check_email(email):
    regex = '\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
    if(re.search(regex, email)):
        return True
    else:
        return False

def mail_submit(send_url, email, request_no):
    subject = f"MALBoost results id = {request_no}"
    body = f"""\nDear User,\n\n
               Your job {request_no} has been submitted.\n
               You may check the status of the job at\n\n
               {send_url}\n\n
               From MALBoost\n\n
            """
    os.system(f"echo -e '{body}' | mail -s '{subject}' -a static/img/email_footer.jpg {email}")
    return print(f"results email sent to {email} for {request_no}")

def mail_reults(send_url, email, request_no):
    subject = f"MALBoost results id = {request_no}"
    body = f"""\nDear User,\n\n
               Your results are ready.\n
               It may be retrieved from the following link\n\n
               {send_url}\n\n
               From MALBoost\n\n
            """
    os.system(f"echo -e '{body}' | mail -s '{subject}' -a static/img/email_footer.jpg {email}")
    return print(f"results email sent to {email} for {request_no}")

def mail_error(email, request_no):

    subject = f"MALBoost failed submission for id = {request_no}"
    body = f"""\nHi,\n\n
               Analysis for {request_no} failed.\n\n
               Please check the file types, file orientation and that the regulatory genes are in the expression set\n\n
               From MALBoost\n\n
               """
    os.system(f"echo -e '{body}' | mail -s '{subject}' -a static/img/email_footer.jpg {email}")
    return print(f"error response email sent to {email} for {request_no}")

def filter_tfs(in_file):
    
    # All the TF's from the orininal network
    tfs = ['PF3D7_1330800', 'PF3D7_0516800', 'PF3D7_0802100', 'PF3D7_1234700',
           'PF3D7_1129600', 'PF3D7_0823200', 'PF3D7_1309800', 'PF3D7_0403900',
           'PF3D7_0105800', 'PF3D7_1346300', 'PF3D7_1441100', 'PF3D7_1347500',
           'PF3D7_1006100', 'PF3D7_0730300', 'PF3D7_0508100', 'PF3D7_0723300',
           'PF3D7_1432500', 'PF3D7_1143100', 'PF3D7_1322000', 'PF3D7_1310700',
           'PF3D7_0711400', 'PF3D7_0416500', 'PF3D7_1328800', 'PF3D7_0934800',
           'PF3D7_1455000', 'PF3D7_0711500', 'PF3D7_1139300', 'PF3D7_0814200',
           'PF3D7_0110700', 'PF3D7_1037600', 'PF3D7_0603600', 'PF3D7_0613800',
           'PF3D7_0419300', 'PF3D7_1141800', 'PF3D7_1429200', 'PF3D7_0811500',
           'PF3D7_1466400', 'PF3D7_1110400', 'PF3D7_0604100', 'PF3D7_0217500',
           'PF3D7_0719200', 'PF3D7_1223100', 'PF3D7_0906600', 'PF3D7_0927600',
           'PF3D7_1202900', 'PF3D7_1225200', 'PF3D7_1241700', 'PF3D7_0404100',
           'PF3D7_0218000', 'PF3D7_1107400', 'PF3D7_1234100', 'PF3D7_0923500',
           'PF3D7_0934400', 'PF3D7_1458600', 'PF3D7_1228300', 'PF3D7_1366900',
           'PF3D7_1033700', 'PF3D7_1422400', 'PF3D7_1445600', 'PF3D7_1433900',
           'PF3D7_0611200', 'PF3D7_1222400', 'PF3D7_0310200', 'PF3D7_1408200',
           'PF3D7_0910000', 'PF3D7_1317200', 'PF3D7_0724600', 'PF3D7_0410800',
           'PF3D7_0933700', 'PF3D7_0506200', 'PF3D7_0622900', 'PF3D7_0910900',
           'PF3D7_1322100', 'PF3D7_0929200', 'PF3D7_0717500', 'PF3D7_1011100',
           'PF3D7_1475600', 'PF3D7_1450400', 'PF3D7_1108000', 'PF3D7_0420000',
           'PF3D7_1118600', 'PF3D7_0812500', 'PF3D7_0706500', 'PF3D7_0810300',
           'PF3D7_1222600', 'PF3D7_1437200', 'PF3D7_1331600', 'PF3D7_0905800',
           'PF3D7_0716400', 'PF3D7_1305200', 'PF3D7_0416000', 'PF3D7_1315800',
           'PF3D7_1308500', 'PF3D7_1463200', 'PF3D7_1474900', 'PF3D7_1449500',
           'PF3D7_0409800', 'PF3D7_1212900', 'PF3D7_0926100', 'PF3D7_0703200',
           'PF3D7_1022000', 'PF3D7_0818500', 'PF3D7_1417200', 'PF3D7_0525600',
           'PF3D7_1366500', 'PF3D7_1472200', 'PF3D7_1015800', 'PF3D7_1451400',
           'PF3D7_1404000', 'PF3D7_0925700', 'PF3D7_1342900', 'PF3D7_1235500',
           'PF3D7_1123000', 'PF3D7_0622500', 'PF3D7_0505600', 'PF3D7_0217400',
           'PF3D7_0605100', 'PF3D7_0506800', 'PF3D7_1009400', 'PF3D7_1016900',
           'PF3D7_0409600', 'PF3D7_1332100', 'PF3D7_1356900', 'PF3D7_1007700']
    
    in_file = in_file[in_file.genes.isin(tfs)]

    return in_file

def gene_checker(in_file):

    # Checking genes submitted
    genes = pd.read_csv('total_genes.tsv', sep='\t', names=['genes'])
    genes = genes['genes'].to_list()

    in_file = [x for x in in_file if x in genes]

    return in_file

def clean_tmp(filename):

    os.remove(filename)

def reg_parse(string):
    string = string.replace(' ','')
    if '\r\n' in string and ',' in string:
        string = string.replace('\r\n','')
        string = string.split(',')
    elif ',' in string:
        string = string.split(',')
    elif '\r\n' in string:
        string = string.split('\r\n')
    elif len(string) == 13:
        string = [string]
    if string[-1] == '':
        string = string[:-1]
    string = [x.upper() for x in string]
    
    return string

def reg_found(l1,l2):
    regs_found = [x for x in l1 if x in l2]
    return regs_found

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/submit', methods=["GET", "POST"])
def submit_file():

    msg = "Expression set max limit is 5200 genes and regulators is 5-50"

    if request.method == "POST":
        cnx = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        
        if request.files:
            exp = request.files['expression']
            reg = request.form['regulators']
            reg = reg_parse(reg)

            spec = [x for x in reg if special_char(x) != None]
            if len(spec) > 0:
                error = f"Found special characters in regulators {', '.join(spec)}"
                return render_template('submit.html', error=error)

            if len(reg) < 1:
                error = 'Please enter valid regulators in the text area'
                return render_template('submit.html', error=error)

            if len({len(i) for i in reg}) != 1:
                error = 'Please use new line or comma separator on regulator list'
                return render_template('submit.html', error=error)
            
            if len(reg) > 50 or len(reg) < 5:
                error = f'The regulator list is not within the permitted range. Regs submitted = {len(reg)}'
                return render_template('submit.html', error=error)
            
            if len(reg) != len(set(reg)):
                error = f"Duplicate IDs found in regulator list"
                return render_template('submit.html', error=error)
            
            if exp.filename != '':
                if not allowed_files(exp.filename):
                    error = f'File type of {exp.filename} not supported: .txt .tsv and .csv only'
                    return render_template('submit.html', error=error)
            else:
                error = f'Please upload an expression set'
                return render_template('submit.html', error=error)

            try:
                expression = file_loader_expression(request.files.get("expression"))
                expression = col_numeric(expression)
                if isinstance(expression, str):
                    return render_template('submit.html', error=expression)
                if len(expression) > 5200 or len(expression) < 1:
                    error = f"Expression set is not within the permitted range, submitted = {len(expression)}"
                    return render_template('submit.html', error=error)
                genes = list(expression.index)
                spec = [x for x in genes if special_char(x) != None]
                if len(spec) > 0:
                    error = f"Found special characters in expression set {', '.join(spec)}"
                    return render_template('submit.html', error=error)
                
            except:
                error = "Expression set did not load. Please check format and upload again"
                return render_template('submit.html', error=error)
            
            try:
                genes = list(expression.index)
                found = reg_found(reg, genes)
                if len(found) < 1:
                    error = "We didn't find any regulators. Please enter some and upload"
                    return render_template('submit.html', error=error)
                elif len(found) < len(reg):
                    outliers = [x for x in reg if x not in genes]
                    error = f"We didn't find the following regulators {', '.join(outliers)}"
                    return render_template('submit.html', error=error)
                regulators = pd.DataFrame(reg,columns=['genes'])
            except:
                error = "Something unexpected happened with the regulators set"
                return render_template('submit.html', error=error)
            
            try:
                email = request.form.get('email')
            except:
                error = "Please enter a valid email address"
                return render_template('submit.html', error=error)

            if not email:
                error = "Please enter a valid email address"
                return render_template('submit.html', error=error)
            
            opt = request.form['myList']

            request_no = uuid.uuid4()

            # estimation of run time
            X = pd.DataFrame([{'exp':len(expression),
                               'reg': len(regulators),
                               'samples': expression.shape[1]}])
            est = estimate_time(loaded_model, X)
            est = est[0]/60

            # Define some parameters for job logging
            in_file  = "table_" + str(request_no) + "_EXP"
            tf_file  = "table_" + str(request_no) + "_REG"
            out_file = "table_" + str(request_no) + "_RES"
            send_url = app_url + 'fetch/' + str(request_no)

            expression.to_sql(name=in_file, con=cnx, if_exists='replace')
            regulators.to_sql(name=tf_file, con=cnx, if_exists='replace')

            # Time to update the db
            new_submit = ResultsRequest(
                            request_no   = str(request_no),
                            email        = email,
                            url          = send_url,
                            request_time = datetime.datetime.now(),
                            run_time     = est,
                            status       = 'running')
            db.session.add(new_submit)
            db.session.commit()

            modelrun.delay(request_no, send_url, in_file, tf_file, out_file, opt, email)
            mail_submit(send_url, email, request_no)
            
            return render_template('success.html', send_url=send_url)

    return render_template('submit.html', msg=msg)

@celery.task(name='app.modelrun',bind=True)
def modelrun(self, request_no, send_url, in_file, tf_file, out_file, opt, email):
    
    # Run the results
    try:
        model_execute(in_file, tf_file, out_file, opt)

        print(f"Model ran for {request_no}")
        
        # Remove input files
        db_con.execute(f"DROP TABLE [{in_file}]")
        db_con.execute(f"DROP TABLE [{tf_file}]")
        
        # Update the db
        update_submit = ResultsRequest.query.filter_by(request_no=request_no).first()
        update_submit.complete_time = datetime.datetime.now()
        update_submit.status = 'complete'
        db.session.commit()

        mail_reults(send_url, email, request_no)

    except Exception as e:
        print(f"Model didn't run for {request_no}")
        print(e)

        # Remove input files
        db_con.execute(f"DROP TABLE [{in_file}]")
        db_con.execute(f"DROP TABLE [{tf_file}]")

        # Update the db
        update_submit = ResultsRequest.query.filter_by(request_no=request_no).first()
        update_submit.complete_time = datetime.datetime.now()
        update_submit.status = 'failed'
        update_submit.error = e[:1500]
        db.session.commit()

        mail_error(send_url, email)

def time_left(est_run, start_time):
    end_est_time = start_time + datetime.timedelta(minutes=est_run)
    comp_time = end_est_time - datetime.datetime.now()
    comp_time = comp_time.total_seconds()/60
    if comp_time < 0:
        comp_time = 0.00
    return round(comp_time,2)

@app.route('/fetch/<request_no>', methods=["GET"])
def fetch(request_no):
    feedback = {}
    try:
        req = ResultsRequest.query.filter_by(request_no=request_no).first()
        if req.status == 'running':
            run_left = time_left(req.run_time,req.request_time)
        else:
            run_left = 0.00
        feedback['status'] = req.status
        feedback['request_no'] = req.request_no
        feedback['run_time'] = str(run_left)
    except Exception as e:
        feedback['error'] = 'Request no not found'
        feedback['request_no'] = request_no
        return render_template('badreq.html',feedback=feedback)
    
    return render_template('wait.html', feedback=feedback)

@app.route('/fetch/download/<request_no>', methods=["GET"])
def network_download(request_no):
    # Download link
    if request.method == "GET":
        cnx = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        try:
            table_name = "[table_" + str(request_no) + "_RES]"
            df = pd.read_sql(f"SELECT * FROM {table_name}", con=cnx)
            df.to_csv('tmp_'+str(request_no)+'.txt', sep='\t', index=False)

            update = ResultsRequest.query.filter_by(request_no=request_no).first()
            update.downloaded = True

            db.session.commit()

            return send_file('tmp_'+str(request_no)+'.txt', as_attachment=True), clean_tmp('tmp_'+str(request_no)+'.txt')
            
        except:
            print("not ready")

@app.route('/download', methods=['POST','GET'])
def download():

    if request.method == "POST":
        reg = request.form['regulators']
        reg = reg_parse(reg)
        spec = [x for x in reg if special_char(x) != None]
        if len(spec) > 0:
            error = f"Found special characters in regulators {', '.join(spec)}"
            return render_template('download.html', error=error)

        if len(reg) < 1:
            error = 'Please enter valid regulators in the text area'
            return render_template('download.html', error=error)
        
        if len({len(i) for i in reg}) != 1:
            error = 'Please use new line or comma separator on regulator list'
            return render_template('download.html', error=error)
        
        if len(reg) != len(set(reg)):
            error = f"Duplicate IDs found in regulator list"
            return render_template('download.html', error=error)

        regulators = gene_checker(reg)
    
        opt = request.form['myList']

        df = pd.read_csv('data/Global_GRN.txt.gz', sep='\t', compression='gzip')

        df = df[(df.TF.isin(regulators)) | (df.target.isin(regulators))] # Filter
        df = df[(df.importance >= int(opt))] # Filter

        filename = str(uuid.uuid4())
        filename = 'data/' + filename + '.txt.gz'

        df.to_csv(filename, sep='\t', compression='gzip', index=False)

        return send_file(filename, as_attachment=True), clean_tmp(filename)
            
    return render_template('download.html')

@app.route('/mail_test')
def mail_test():
    subject = 'Test msg from MALBoost'
    body = f"""\n
               Hi Guys,\n\n
               Testing my app for email access.\n\n
               {app_url}\n\n
               Rudels\n\n
               """
    os.system(f"echo -e '{body}' | mail -s '{subject}' -a static/img/email_footer.jpg roelofvanwyk89@gmail.com")
    return "results email sent to to myself"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
