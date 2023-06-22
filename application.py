from flask import Flask,redirect,url_for,render_template,request,flash,abort,session
from itsdangerous import URLSafeTimedSerializer
from flask_session import Session
from key import secret_key,salt1,salt2
from tokens import token
from cmail import sendmail
import mysql.connector
import os
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
app.config['MESSAGE_FLASHING_OPTIONS'] = {'duration': 2}
Session(app)
#mydb=mysql.connector.connect(host='localhost', user='root', password='Shanu@1234', db='project')
db= os.environ['RDS_DB_NAME']
user=os.environ['RDS_USERNAME']
password=os.environ['RDS_PASSWORD']
host=os.environ['RDS_HOSTNAME']
port=os.environ['RDS_PORT']
with mysql.connector.connect(host=host,user=user,password=password,db=db) as conn:
    cursor=conn.cursor(buffered=True)
    cursor.execute('create table if not exists admin(username varchar(30) unique,email varchar(50) primary key,password varchar(30),email_status enum("verified","not verified"))')
    cursor.execute('create table if not exists employee(empname varchar(30),empdept varchar(15),empmail varchar(50) primary key,emppassword varchar(20),added_by varchar(50),FOREIGN KEY (added_by) REFERENCES admin(email))')
    cursor.execute('create table if not exists tasks(taskid int primary key,title varchar(25),duedate date,content text,empmail varchar(50),assigned_by varchar(50),status varchar(20),FOREIGN KEY (empmail) REFERENCES employee(empmail),FOREIGN KEY (assigned_by) REFERENCES admin(email))')
mydb=mysql.connector.connect(host=host,user=user,password=password,db=db)

@app.route('/')
def title():
    return render_template('title.html')

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if session.get('user'):
        if session['admin']:
            adminname=session.get('user')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select * from tasks where assigned_by=%s',[adminname])
            data=cursor.fetchall()
            cursor.close()
            return render_template('table.html',tasks=data)
        else:
            name=session.get('user')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select * from tasks where empmail=%s',[name])
            data=cursor.fetchall()
            cursor.close()
            return render_template('table.html',tasks=data)
    else:
        return redirect(url_for('admin_login'))

@app.route('/registration',methods=['GET','POST'])
def admin_registration():
    if request.method=="POST":
        username=request.form['username']
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into admin (username,email,password) values(%s,%s,%s)',(username,email,password))
        except mysql.connector.IntegrityError:
            flash('Email is already used!!!')
            return render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            session['name']=username
            subject="Verification"
            confirm_link=url_for('confirm', token=token(email,salt=salt1),_external=True)
            body=f"Thanks for Signing up. Click the link for verification \n {confirm_link}"
            sendmail(to=email,subject=subject,body=body)
            flash("Check the mail for verification link")
            return render_template('registration.html')
    else:
        return render_template('registration.html')

@app.route('/resendconfirmation')
def resend():
    if session.get('user') and session['admin']:
        email=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.execute('select email from admin where email=%s',[email])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('dashboard'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('admin_login'))

@app.route('/confirm/<token>',methods=['GET','POST'])
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=180)
    except Exception:
        abort(404,'Link Expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='verified':
            flash('Email already confirmed')
            return redirect(url_for('admin_login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update admin set email_status='verified' where email=%s",[email])
            mydb.commit()
            flash("Email Confirmation Success")
            return redirect(url_for('admin_login'))

@app.route('/login',methods=['GET','POST'])
def admin_login():
    if session.get('user') and session['admin']:
        return redirect(url_for('dashboard'))
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where email=%s',[email])
        count=cursor.fetchone()[0]
        try:
            cursor.execute('select username from admin where email=%s',[email])
            session['name']=cursor.fetchone()[0]
        except:
            flash('Only Admins are allowed')
            return render_template('login.html')
        else:
            if count==1:
                cursor.execute('select count(*) from admin where email=%s and password=%s',[email,password])
                pcount=cursor.fetchone()[0]
                if pcount==1:
                    session['user']=email
                    session['admin']=True
                    cursor.execute('select email_status from admin where email=%s',[email])
                    status=cursor.fetchone()[0]
                    cursor.close()
                    if status!='verified':
                        return redirect(url_for('inactive'))
                    else:
                        return redirect(url_for('dashboard'))
                else:
                    cursor.close()
                    flash("Invalid Password")
                    return render_template('login.html')
            else:
                cursor.close()
                flash("Invalid Mail ID")
                return render_template('login.html')
    return render_template('login.html')

@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.execute('select count(*) from employee where empmail=%s',[email])
        ecount=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from admin where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='verified':
                flash('Please Confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('admin_login'))
        elif ecount==1:
            subject='Forget Password'
            confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
            body=f"Use this link to reset your password-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Reset link sent check your email')
            return redirect(url_for('emplogin'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')

@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select count(*) from admin where email=%s',[email])
                count=cursor.fetchone()[0]
                cursor.execute('select count(*) from employee where empmail=%s',[email])
                ecount=cursor.fetchone()[0]
                if count==1:
                    cursor.execute('update admin set password=%s where email=%s',[newpassword,email])
                    mydb.commit()
                    flash('Password Reset Successful')
                    return redirect(url_for('admin_login'))
                elif ecount==1:
                    cursor.execute('update employee set emppassword=%s where empmail=%s',[newpassword,email])
                    mydb.commit()
                    flash('Password Reset Successful')
                    return redirect(url_for('emplogin'))
                else:
                    flash('Sorry your data not found!!')
                    return render_template('title.html')
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/inactive')
def inactive():
    if session.get('user') and session['admin']:
        email=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='verified':
            return redirect(url_for('dashboard'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('admin_login'))

@app.route('/logout')
def logout():
    if session.get('user') and session['admin']:
        session['admin']=False
        session['name']=None
        session.pop('user')
        return redirect(url_for('title'))
    else:
        session.pop('user')
        session['name']=None
        return redirect(url_for('title'))

@app.route('/emplogin',methods=['POST','GET'])
def emplogin():
    if session.get('user') and not session['admin']:
        return redirect(url_for('dashboard'))
    if request.method=='POST':
        empmail=request.form['empmail']
        emppassword=request.form['emppassword']
        cursor=mydb.cursor(buffered=True)
        cursor.execute("select count(*) from employee where empmail=%s",[empmail])
        count=cursor.fetchone()[0]
        cursor.execute('select empname from employee where empmail=%s',[empmail])
        session['name']=cursor.fetchone()[0]
        if count==1:
            cursor.execute("select count(*) from employee where empmail=%s and emppassword=%s",[empmail,emppassword])
            pcount=cursor.fetchone()[0]
            if pcount==1:
                session['user']=empmail
                session['admin']=False
                cursor.close()
                return redirect(url_for('dashboard'))
            else:
                cursor.close()
                flash("Invalid Password")
                return render_template('emplogin.html')
        else:
            cursor.close()
            flash("Invalid mail id")
            return render_template('emplogin.html')
    else:
        return render_template('emplogin.html')
    return render_template('emplogin.html')

@app.route('/empregister',methods=['GET','POST'])
def empregister():
    if session.get('user') and session['admin']:
        if request.method=='POST':
            empname=request.form['empname']
            empdept=request.form['empdept']
            empmail=request.form['empmail']
            emppassword=request.form['emppassword']
            added_by=session.get('user')
            cursor=mydb.cursor(buffered=True)
            try:
                cursor.execute('insert into employee (empname,empdept,empmail,emppassword,added_by) values (%s,%s,%s,%s,%s)',[empname,empdept,empmail,emppassword,added_by])
            except:
                flash('Employee mail is already used')
                return render_template('empregister.html')
            else:
                mydb.commit()
                cursor.close()
                subject='User Login Credentials'
                body=f"Welcome to Tasking Bar. These are your login credentials.\n Email={empmail} \n Password={emppassword}"
                sendmail(to=empmail,subject=subject,body=body)
                return redirect(url_for('dashboard'))
        else:
            return render_template('empregister.html')
    else:
        flash('Login as admin and proceed')
        return render_template('login.html')

@app.route('/addtask',methods=['POST','GET'])
def addtask():
    if session.get('user') and session['admin']:
        if request.method=='POST':
            taskid=request.form['taskid']
            title=request.form['title']
            duedate=request.form['duedate']
            assign=request.form['assign']
            content=request.form['content']
            admin=session.get('user')
            cursor=mydb.cursor(buffered=True)
            try:
                cursor.execute('insert into tasks (taskid,title,duedate,content,empmail,assigned_by) values (%s,%s,%s,%s,%s,%s)',[taskid,title,duedate,content,assign,admin])
            except:
                flash('Task ID already used or employee is not registered')
                return render_template('addtask.html')
            else:
                mydb.commit()
                cursor.close()
                subject='New Task Assigned'
                body=f"This is a mail regarding the task assigned to you by {admin}.\nTask title: {title}\nDetails: {content}\nDuedate: {duedate}"
                sendmail(to=assign,subject=subject,body=body)
                return redirect(url_for('dashboard'))
        else:
            return render_template('addtask.html')
    return redirect(url_for('dashboard'))

@app.route('/updatetask/<taskid>', methods=['GET','POST'])
def updatetask(taskid):
    if session.get('user') and session['admin']:
        if request.method=='POST':
            title=request.form['title']
            duedate=request.form['duedate']
            assign=request.form['assign']
            content=request.form['content']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update tasks set title=%s, duedate=%s, empmail=%s, content=%s where taskid=%s',[title,duedate,assign,content,taskid])
            mydb.commit()
            cursor.close()
            return redirect(url_for('dashboard'))
        else:
            return render_template('update.html')
    else:
        return render_template('login.html')

@app.route('/deletetask/<taskid>')
def deletetask(taskid):
    if session.get('user') and session['admin']:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from tasks where taskid=%s',[taskid])
        mydb.commit()
        cursor.close()
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')
    
@app.route('/submit/<taskid>', methods=['GET','POST'])
def submit(taskid):
    if session.get('user'):
        if request.method=='POST':
            stat = request.form['stat']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('update tasks set status=%s where taskid=%s',[stat,taskid])
            mydb.commit()
            cursor.close()
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('submit',taskid=taskid))
    return redirect(url_for('dashboard'))

if __name__=="__main__":
    app.run()