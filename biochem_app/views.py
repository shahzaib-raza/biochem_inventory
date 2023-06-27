from django.shortcuts import render, redirect
from django.http import HttpResponse
import pandas as pd
import sqlite3
import datetime as dt
from io import BytesIO


loggedin = False

NAME = None

def get_table_names():
    conn = sqlite3.connect("biochem.sqlite")
    q = """
        SELECT name FROM sqlite_schema
        WHERE type='table'
        ORDER BY name;
    """
    cur = conn.cursor()
    r = cur.execute(q)
    cols = [i[0] for i in r.fetchall()]
    conn.close()
    return cols

cols = get_table_names()

def get_table(name):
    conn = sqlite3.connect("biochem.sqlite")
    try:
        df = pd.read_sql(con=conn, sql=f"SELECT * FROM {name};")
    except:
        df = pd.DataFrame()
    conn.close()
    return df

def auth_login(user, pas):
    con = sqlite3.connect("db.sqlite3")
    cur = con.cursor()
    q = f"SELECT * FROM users WHERE (user='{user}') AND (password='{pas}')"
    res = cur.execute(q).fetchall()
    con.close()
    if len(res) > 0:
        return True
    return False


def download_inv(request):

    global cols

    m = str(dt.datetime.now().month)
    if len(m) < 2:
        m = "0"+m

    y = str(dt.datetime.now().year)

    filt = f"/{m}/{y}"

    conn = sqlite3.connect('biochem.sqlite')

    fn = f"inventory_{m}_{y}.xlsx"

    with BytesIO() as b:
        with pd.ExcelWriter(b) as writer:
            for col in cols:
                df = pd.read_sql(con=conn, sql=f"SELECT * FROM '{col}'")
                df = df[df["Date"].apply(lambda x: True if filt in str(x) else False)]
                df.to_excel(writer, sheet_name=col, index=False)
        res = HttpResponse(
            b.getvalue(), # Gives the Byte string of the Byte Buffer object
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    res['Content-Disposition'] = f'attachment; filename={fn}'

    conn.close()

    return res


def ins_defaults(request):
    
    global cols
    global NAME

    tod = dt.datetime.now().strftime("%d/%m/%Y")

    conn = sqlite3.connect("biochem.sqlite")

    cur = conn.cursor()

    for col in cols:

        df = pd.read_sql(con=conn, sql=f"SELECT * FROM '{col}';")
        vs = list(df.iloc[-1].values)
        
        if str(vs[1]) != tod:

            nid = int(vs[0])+1
            dat = tod
            nam = vs[2]
            qi = 0
            qo = 0
            bal = vs[5]
            rem = None

            q = f"INSERT INTO '{col}' VALUES ({nid}, '{dat}', '{nam}', {qi}, {qo}, {bal}, '{NAME}', '{rem}');"

            cur.execute(q)
    conn.commit()
    conn.close()

    return ims(request, notify="Successfully inserted default values!")


# Create your views here.
def ims(request, notify=None):
    
    global cols
    global loggedin
    global NAME

    if loggedin == True:

        if request.method == "POST":
            if 'dropdown_up' in request.POST:
                tn = request.POST.get("dropdown_up")
                if tn != '' or tn != None:
                    tab = get_table(str(tn).strip())
                    try:
                        balance = int(tab['Balance'].to_list()[-1])
                    except:
                        balance = 0
                    if balance < 5:
                        div_color = False
                    else:
                        div_color = True
                    tab = tab.to_html()
                    return render(
                        request,
                        'dashboard/ims.html',
                        {'cols': cols, 'tab_data': tab, 'div_color': div_color}
                    )
                else:
                    return render(request, 'dashboard/ims.html', {'cols': cols})
            elif "dropdown" in request.POST:

                dat = dt.datetime.now().strftime("%d/%m/%Y")

                try:
                    tn = request.POST.get("dropdown")
                except:
                    tn = None
                try:
                    qn = request.POST.get("quantityIn")
                except:
                    qn = 0
                try:
                    qo = request.POST.get("quantityOut")
                except:
                    qo = 0
                try:
                    remarks = request.POST.get("remarks")
                except:
                    remarks = None

                if notify == None:
                    notify = "Unable to add the entry"

                if (qn == None and qo == None) or (qn == '' and qo == ''):
                    return render(
                        request,
                        'dashboard/ims.html',
                        {'cols': cols, 'notify': notify}
                    )
                else:
                    p_tab = get_table(tn)
                    
                    last = int(p_tab['Balance'].to_list()[-1])
                    nid = int(p_tab['id'].to_list()[-1]) + 1
                    item = p_tab["Brand_Name"].to_list()[-1]
                    
                    if qn != None and qn != '':
                        last = last + int(qn)
                    else:
                        qn = 0
                    
                    if qo != None and qo != '':
                        last = last - int(qo)
                    else:
                        qo = 0

                    conn = sqlite3.connect('biochem.sqlite')
                    q = f"INSERT INTO '{tn}' VALUES ({nid}, '{dat}', '{item}', {qn}, {qo}, {last}, '{NAME}', '{remarks}');"
                    
                    print(q)

                    cur = conn.cursor()
                    cur.execute(q)

                    conn.commit()
                    conn.close()
                
                notify = "Successfully inserted the record"

                return render(
                    request,
                    'dashboard/ims.html',
                    {'cols': cols, 'notify': notify}
                )
            elif "logout" in request.POST:
                loggedin = False
                return redirect(to='/login/')
            else:
                return render(request, 'dashboard/ims.html', {'cols': cols})
        else:
            return render(request, 'dashboard/ims.html', {'cols': cols})
    else:
        return redirect(to="/login/")


def index(request):

    global loggedin
    global NAME
    global cols

    print(loggedin)

    if loggedin == False:
        if request.method == 'POST':
            if 'user' in request.POST and 'password' in request.POST:
                un = request.POST.get('user')
                pas = request.POST.get('password')
                check = auth_login(un, pas)
                if check == True:
                    loggedin = True
                    NAME = un
                    return redirect(to='/dashboard/')
                else:
                    return render(
                        request,
                        'login/login.html',
                        {'note': 'Wrong User or Password!'}
                    )
            else:
                return render(request, 'login/login.html')
        else:
            return render(request, 'login/login.html')
    else:
        return redirect(to='/dashboard/')



def signup(request):
    global loggedin
    if request.method == "POST":
        print(request.POST)
        un = request.POST.get('username_su')
        pas = request.POST.get('password_su')
        conn = sqlite3.connect("db.sqlite3")
        cur = conn.cursor()
        q = f"INSERT INTO 'users' VALUES('{un}', '{pas}');"
        cur.execute(q)
        conn.commit()
        conn.close()
        return redirect(to='/login')
    
    if loggedin == True:
        return redirect(to='/dashboard/')
    return render(request, 'signup/sign_up.html')
