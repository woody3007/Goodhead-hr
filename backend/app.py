import os, hashlib, json
from datetime import datetime, date
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, origins='*', supports_credentials=True)

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    conn = get_db(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY, emp_id TEXT, id_card TEXT, username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, role TEXT DEFAULT 'operator', approved INT DEFAULT 0,
        name TEXT, dept TEXT, pos TEXT, salary REAL DEFAULT 0, bank TEXT,
        vacation INT DEFAULT 0, vac_used REAL DEFAULT 0,
        gys_deduct REAL DEFAULT 0, tax_deduct REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW()
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id) ON DELETE CASCADE,
        date TEXT, check_in TEXT, check_out TEXT, shift TEXT DEFAULT 'morning',
        late_min REAL DEFAULT 0, late_ded REAL DEFAULT 0,
        forget INT DEFAULT 0, ot_h REAL DEFAULT 0, ot_amt REAL DEFAULT 0,
        absent INT DEFAULT 0, lat REAL, lng REAL, gps_acc REAL, note TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS leaves (
        id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id) ON DELETE CASCADE,
        type TEXT, start_date TEXT, end_date TEXT, days REAL, hours REAL DEFAULT 0,
        reason TEXT, doc TEXT, ded REAL DEFAULT 0, status TEXT DEFAULT 'pending',
        approved_by INT, created_at TIMESTAMP DEFAULT NOW()
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS payroll (
        id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id) ON DELETE CASCADE,
        name TEXT, dept TEXT, pos TEXT, bank TEXT, period TEXT,
        start_date TEXT, end_date TEXT,
        salary REAL DEFAULT 0, extra REAL DEFAULT 0, pos_pay REAL DEFAULT 0,
        ot_h REAL DEFAULT 0, ot_amt REAL DEFAULT 0, comm REAL DEFAULT 0,
        ss_base REAL DEFAULT 0, ss REAL DEFAULT 0,
        late_min REAL DEFAULT 0, late_ded REAL DEFAULT 0,
        fgt_count INT DEFAULT 0, fgt_ded REAL DEFAULT 0,
        lv_days REAL DEFAULT 0, lv_ded REAL DEFAULT 0,
        gys REAL DEFAULT 0, other_ded REAL DEFAULT 0, tax REAL DEFAULT 0,
        net REAL DEFAULT 0, status TEXT DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT NOW()
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT
    )''')
    # Default manager
    c.execute("SELECT id FROM users WHERE username='manager'")
    if not c.fetchone():
        c.execute("""INSERT INTO users (emp_id,username,password,role,approved,name,dept,pos,salary,bank)
            VALUES ('MGR001','manager',%s,'manager',1,'นายวุฒิไกร บุญลาภงามดี','Management','MD',100000,'2302832098')""",
            (hp('1234'),))
    conn.commit(); conn.close()

# ===== SERVE FRONTEND =====
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# ===== CORS =====
@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,X-Role'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return r
@app.route('/api/<path:p>', methods=['OPTIONS'])
def options(p): return ''

# ===== AUTH =====
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=%s AND password=%s", (d['username'], hp(d['password'])))
    u = c.fetchone(); conn.close()
    if not u: return jsonify({'error': 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'}), 401
    if not u['approved']: return jsonify({'error': 'บัญชีรอการอนุมัติจาก Manager'}), 403
    return jsonify({'id':u['id'],'username':u['username'],'role':u['role'],
        'name':u['name'],'dept':u['dept'],'pos':u['pos'],'empId':u['emp_id'],'salary':u['salary']})

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json
    conn = get_db(); c = conn.cursor()
    try:
        c.execute("""INSERT INTO users (emp_id,id_card,username,password,role,name,dept,pos,salary,bank)
            VALUES (%s,%s,%s,%s,'operator',%s,%s,%s,%s,%s)""",
            (d.get('empId'),d.get('idCard'),d['username'],hp(d['password']),
             d.get('name'),d.get('dept'),d.get('pos'),d.get('salary',0),d.get('bank','')))
        conn.commit(); conn.close()
        return jsonify({'message':'ส่งคำขอแล้ว รอการอนุมัติ'})
    except Exception as e:
        conn.close(); return jsonify({'error':'Username ซ้ำ'}), 400

# ===== USERS =====
@app.route('/api/users', methods=['GET'])
def get_users():
    role = request.args.get('role','operator')
    conn = get_db(); c = conn.cursor()
    if role == 'manager':
        c.execute("SELECT id,emp_id,id_card,username,name,dept,pos,role,approved,salary,bank,vacation,vac_used FROM users WHERE approved=1 ORDER BY dept,name")
    else:
        c.execute("SELECT id,emp_id,username,name,dept,pos,role,approved,vacation,vac_used FROM users WHERE approved=1 ORDER BY dept,name")
    rows = c.fetchall(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users/pending', methods=['GET'])
def pending_users():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id,username,name,dept,pos,created_at FROM users WHERE approved=0")
    rows = c.fetchall(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/users/<int:uid>/approve', methods=['POST'])
def approve_user(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE users SET approved=1 WHERE id=%s", (uid,))
    conn.commit(); conn.close()
    return jsonify({'message':'อนุมัติแล้ว'})

@app.route('/api/users/<int:uid>', methods=['PUT'])
def update_user(uid):
    d = request.json; role = request.headers.get('X-Role','')
    conn = get_db(); c = conn.cursor()
    if role == 'manager':
        if d.get('password'):
            c.execute("""UPDATE users SET name=%s,emp_id=%s,dept=%s,pos=%s,salary=%s,role=%s,bank=%s,vacation=%s,username=%s,password=%s WHERE id=%s""",
                (d.get('name'),d.get('empId'),d.get('dept'),d.get('pos'),d.get('salary',0),
                 d.get('role','operator'),d.get('bank'),d.get('vacation',0),d.get('username'),hp(d['password']),uid))
        else:
            c.execute("""UPDATE users SET name=%s,emp_id=%s,dept=%s,pos=%s,salary=%s,role=%s,bank=%s,vacation=%s,username=%s WHERE id=%s""",
                (d.get('name'),d.get('empId'),d.get('dept'),d.get('pos'),d.get('salary',0),
                 d.get('role','operator'),d.get('bank'),d.get('vacation',0),d.get('username'),uid))
    else:
        if d.get('password'):
            c.execute("UPDATE users SET name=%s,bank=%s,username=%s,password=%s WHERE id=%s",
                (d.get('name'),d.get('bank'),d.get('username'),hp(d['password']),uid))
        else:
            c.execute("UPDATE users SET name=%s,bank=%s,username=%s WHERE id=%s",
                (d.get('name'),d.get('bank'),d.get('username'),uid))
    conn.commit(); conn.close()
    return jsonify({'message':'อัพเดทแล้ว'})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def delete_user(uid):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=%s", (uid,)); conn.commit(); conn.close()
    return jsonify({'message':'ลบแล้ว'})

# ===== ATTENDANCE =====
@app.route('/api/attendance/checkin', methods=['POST'])
def checkin():
    d = request.json; uid = d['user_id']; today = date.today().isoformat()
    now = datetime.now().strftime('%H:%M')
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT id FROM attendance WHERE user_id=%s AND date=%s", (uid, today))
    if c.fetchone(): conn.close(); return jsonify({'error':'เช็คอินแล้ววันนี้'}), 400
    c.execute("SELECT salary,dept FROM users WHERE id=%s", (uid,))
    u = c.fetchone()
    dept_cfg = {
        'ACC':{'inM':'09:00'},'GA':{'inM':'08:30'},'Logistic':{'inM':'08:30'},
        'Management':{'inM':'08:30'},'Production':{'inM':'08:30','inN':'20:30'},
        'Sale and marketing':{'inM':'09:00'},'จป':{'inM':'08:30'},'ทั่วไป':{'inM':'08:30'}
    }
    late_min = 0; late_ded = 0
    shift = d.get('shift','morning')
    cfg = dept_cfg.get(u['dept'],{'inM':'08:30'})
    exp = cfg.get('inN','20:30') if shift=='night' else cfg.get('inM','08:30')
    eh,em = map(int,exp.split(':'))
    ah,am = map(int,now.split(':'))
    diff = (ah*60+am)-(eh*60+em)
    if diff > 5: late_min=diff; late_ded=diff*5
    c.execute("""INSERT INTO attendance (user_id,date,check_in,shift,late_min,late_ded,lat,lng,gps_acc)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (uid,today,now,shift,late_min,late_ded,d.get('lat'),d.get('lng'),d.get('gpsAcc')))
    conn.commit(); conn.close()
    return jsonify({'message':f'เช็คอินสำเร็จ {now}','lateMin':late_min,'lateDed':late_ded})

@app.route('/api/attendance/checkout', methods=['POST'])
def checkout():
    d = request.json; uid = d['user_id']; today = date.today().isoformat()
    now = datetime.now().strftime('%H:%M')
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM attendance WHERE user_id=%s AND date=%s", (uid, today))
    att = c.fetchone()
    if not att or not att['check_in']: conn.close(); return jsonify({'error':'ยังไม่ได้เช็คอิน'}), 400
    c.execute("SELECT salary,dept FROM users WHERE id=%s", (uid,))
    u = c.fetchone()
    dept_cfg = {
        'GA':{'outM':'17:30','hasOT':True},'Logistic':{'outM':'17:30','hasOT':True},
        'Production':{'outM':'17:30','outN':'05:30','hasOT':True},
    }
    ot_h=0; ot_amt=0
    cfg = dept_cfg.get(u['dept'],{})
    if cfg.get('hasOT'):
        exp_out = cfg.get('outN','05:30') if att['shift']=='night' else cfg.get('outM','17:30')
        oh,om = map(int,exp_out.split(':'))
        ah,am = map(int,now.split(':'))
        ot_mins=(ah*60+am)-(oh*60+om+30)
        if ot_mins>0:
            ot_h=round(ot_mins/60*4)/4
            ot_amt=round((u['salary']/30/8)*ot_h*1.5*100)/100
    c.execute("UPDATE attendance SET check_out=%s,ot_h=%s,ot_amt=%s,note=%s WHERE user_id=%s AND date=%s",
        (now,ot_h,ot_amt,d.get('note',''),uid,today))
    conn.commit(); conn.close()
    return jsonify({'message':f'เช็คเอาท์ {now}','otH':ot_h,'otAmt':ot_amt})

@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    uid = request.args.get('user_id'); role = request.args.get('role','operator')
    month = request.args.get('month','')
    conn = get_db(); c = conn.cursor()
    if role=='operator':
        c.execute("SELECT a.*,u.name,u.dept FROM attendance a JOIN users u ON a.user_id=u.id WHERE a.user_id=%s AND a.date LIKE %s ORDER BY a.date DESC",
            (uid,f'{month}%'))
    else:
        c.execute("SELECT a.*,u.name,u.dept FROM attendance a JOIN users u ON a.user_id=u.id WHERE a.date LIKE %s ORDER BY a.date DESC,u.name",
            (f'{month}%',))
    rows = c.fetchall(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/attendance/<int:aid>', methods=['PUT'])
def update_att(aid):
    d = request.json; conn = get_db(); c = conn.cursor()
    c.execute("""UPDATE attendance SET check_in=%s,check_out=%s,ot_h=%s,ot_amt=%s,late_min=%s,late_ded=%s,forget=%s,absent=%s,note=%s WHERE id=%s""",
        (d.get('checkIn'),d.get('checkOut'),d.get('otH',0),d.get('otAmt',0),
         d.get('lateMin',0),d.get('lateDed',0),d.get('forget',0),d.get('absent',0),d.get('note'),aid))
    conn.commit(); conn.close()
    return jsonify({'message':'อัพเดทแล้ว'})

# ===== LEAVES =====
@app.route('/api/leaves', methods=['POST'])
def create_leave():
    d = request.json; uid = d['userId']
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT salary FROM users WHERE id=%s", (uid,))
    u = c.fetchone()
    days=(datetime.strptime(d['end'],'%Y-%m-%d')-datetime.strptime(d['start'],'%Y-%m-%d')).days+1
    hours=d.get('hours',0); ded=0
    if d['type']=='ลากิจ':
        ded=round(u['salary']/30/8*hours) if hours>0 else round(u['salary']/30*days)
    c.execute("""INSERT INTO leaves (user_id,type,start_date,end_date,days,hours,reason,doc,ded)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (uid,d['type'],d['start'],d['end'],days,hours,d.get('reason'),d.get('doc',''),ded))
    conn.commit(); conn.close()
    return jsonify({'message':'ส่งใบลาแล้ว รอการอนุมัติ','days':days,'ded':ded})

@app.route('/api/leaves', methods=['GET'])
def get_leaves():
    uid = request.args.get('userId'); role = request.args.get('role','operator')
    conn = get_db(); c = conn.cursor()
    if role=='operator':
        c.execute("SELECT l.*,u.name,u.dept FROM leaves l JOIN users u ON l.user_id=u.id WHERE l.user_id=%s ORDER BY l.created_at DESC",(uid,))
    else:
        c.execute("SELECT l.*,u.name,u.dept FROM leaves l JOIN users u ON l.user_id=u.id ORDER BY l.created_at DESC")
    rows = c.fetchall(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/leaves/<int:lid>/approve', methods=['POST'])
def approve_leave(lid):
    d = request.json; status = d.get('status','approved')
    conn = get_db(); c = conn.cursor()
    c.execute("UPDATE leaves SET status=%s,approved_by=%s WHERE id=%s",(status,d.get('approvedBy'),lid))
    if status=='approved':
        c.execute("SELECT * FROM leaves WHERE id=%s",(lid,))
        lv=c.fetchone()
        if lv and lv['type']=='ลาพักร้อน':
            c.execute("UPDATE users SET vac_used=vac_used+%s WHERE id=%s",(lv['days'],lv['user_id']))
    conn.commit(); conn.close()
    return jsonify({'message':'อัพเดทแล้ว'})

# ===== PAYROLL =====
@app.route('/api/payroll/calculate', methods=['POST'])
def calc_payroll():
    d = request.json; period=d['period']
    yr,mo=map(int,period.split('-'))
    from datetime import date as dt
    import calendar
    start=f"{yr}-{mo-1 if mo>1 else yr-1}-22" if mo>1 else f"{yr-1}-12-22"
    start=f"{yr if mo>1 else yr-1}-{str(mo-1 if mo>1 else 12).zfill(2)}-22"
    end=f"{yr}-{str(mo).zfill(2)}-22"
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM users WHERE approved=1 AND role='operator'")
    users=c.fetchall()
    c.execute("DELETE FROM payroll WHERE period=%s",(period,))
    count=0
    for u in users:
        uid=u['id']
        c.execute("SELECT * FROM attendance WHERE user_id=%s AND date>=%s AND date<=%s",(uid,start,end))
        atts=c.fetchall()
        c.execute("SELECT * FROM leaves WHERE user_id=%s AND status='approved' AND start_date>=%s AND start_date<=%s",(uid,start,end))
        lvs=c.fetchall()
        ot_h=sum(a['ot_h'] or 0 for a in atts)
        ot_amt=sum(a['ot_amt'] or 0 for a in atts)
        late_min=sum(a['late_min'] or 0 for a in atts)
        late_ded=sum(a['late_ded'] or 0 for a in atts)
        fgt_count=sum(1 for a in atts if a['forget'])
        fgt_ded=fgt_count*100
        lv_days=sum(l['days'] for l in lvs if l['type']=='ลากิจ')
        lv_ded=sum(l['ded'] for l in lvs if l['type']=='ลากิจ')
        sal=u['salary'] or 0
        ss_base=min(sal,17500); ss=round(ss_base*0.05)
        taxable=sal+ot_amt; annual=taxable*12
        tax=round(taxable*0.1) if annual>500000 else round(taxable*0.05) if annual>300000 else 0
        gys=u.get('gys_deduct',0) or 0
        net=round(taxable-ss-late_ded-fgt_ded-lv_ded-gys-tax)
        c.execute("""INSERT INTO payroll (user_id,name,dept,pos,bank,period,start_date,end_date,
            salary,ot_h,ot_amt,ss_base,ss,late_min,late_ded,fgt_count,fgt_ded,lv_days,lv_ded,gys,tax,net)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid,u['name'],u['dept'],u['pos'],u['bank'],period,start,end,
             sal,round(ot_h,2),round(ot_amt,2),ss_base,ss,round(late_min,2),round(late_ded,2),
             fgt_count,fgt_ded,round(lv_days,2),round(lv_ded,2),gys,tax,net))
        count+=1
    conn.commit(); conn.close()
    return jsonify({'message':f'คำนวณแล้ว {count} คน','count':count})

@app.route('/api/payroll', methods=['GET'])
def get_payroll():
    uid=request.args.get('userId'); role=request.args.get('role','operator')
    period=request.args.get('period','')
    conn=get_db(); c=conn.cursor()
    if role=='operator':
        c.execute("SELECT * FROM payroll WHERE user_id=%s ORDER BY period DESC",(uid,))
    elif role=='admin':
        c.execute("SELECT id,user_id,name,dept,period,ot_h,status FROM payroll WHERE period LIKE %s ORDER BY dept,name",(f'{period}%',))
    else:
        c.execute("SELECT * FROM payroll WHERE period LIKE %s ORDER BY dept,name",(f'{period}%',))
    rows=c.fetchall(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/payroll/<int:pid>', methods=['PUT'])
def update_payroll(pid):
    d=request.json; conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM payroll WHERE id=%s",(pid,))
    p=c.fetchone()
    if p:
        comm=d.get('comm',p['comm'] or 0)
        gys=d.get('gys',p['gys'] or 0)
        other_ded=d.get('otherDed',p['other_ded'] or 0)
        tax=d.get('tax',p['tax'] or 0)
        taxable=(p['salary'] or 0)+(p['ot_amt'] or 0)+comm
        net=round(taxable-(p['ss'] or 0)-(p['late_ded'] or 0)-(p['fgt_ded'] or 0)-(p['lv_ded'] or 0)-gys-other_ded-tax)
        status=d.get('status','confirmed')
        c.execute("UPDATE payroll SET comm=%s,gys=%s,other_ded=%s,tax=%s,net=%s,status=%s WHERE id=%s",
            (comm,gys,other_ded,tax,net,status,pid))
    conn.commit(); conn.close()
    return jsonify({'message':'อัพเดทแล้ว'})

# ===== SETTINGS =====
@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT * FROM settings")
    rows={r['key']:r['value'] for r in c.fetchall()}
    conn.close(); return jsonify(rows)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    d=request.json; conn=get_db(); c=conn.cursor()
    for k,v in d.items():
        c.execute("INSERT INTO settings (key,value) VALUES (%s,%s) ON CONFLICT (key) DO UPDATE SET value=%s",(k,json.dumps(v),json.dumps(v)))
    conn.commit(); conn.close()
    return jsonify({'message':'บันทึกแล้ว'})

# ===== DASHBOARD =====
@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    uid=request.args.get('userId'); role=request.args.get('role','operator')
    today=date.today().isoformat(); month=datetime.now().strftime('%Y-%m')
    conn=get_db(); c=conn.cursor(); data={}
    if role in ['manager','admin']:
        c.execute("SELECT COUNT(*) as n FROM users WHERE approved=1 AND role='operator'")
        data['totalEmployees']=c.fetchone()['n']
        c.execute("SELECT COUNT(*) as n FROM users WHERE approved=0")
        data['pendingUsers']=c.fetchone()['n']
        c.execute("SELECT COUNT(*) as n FROM attendance WHERE date=%s AND check_in IS NOT NULL",(today,))
        data['checkedInToday']=c.fetchone()['n']
        c.execute("SELECT COUNT(*) as n FROM leaves WHERE status='pending'")
        data['pendingLeaves']=c.fetchone()['n']
        if role=='manager':
            c.execute("SELECT COALESCE(SUM(ot_amt),0) as n FROM attendance WHERE date LIKE %s",(f'{month}%',))
            data['otAmtMonth']=float(c.fetchone()['n'])
    if role=='operator':
        c.execute("SELECT * FROM attendance WHERE user_id=%s AND date=%s",(uid,today))
        att=c.fetchone(); data['todayAtt']=dict(att) if att else None
        c.execute("SELECT COUNT(*) as n FROM leaves WHERE user_id=%s AND status='pending'",(uid,))
        data['pendingLeaves']=c.fetchone()['n']
        c.execute("SELECT vacation,vac_used FROM users WHERE id=%s",(uid,))
        u=c.fetchone()
        data['vacRemaining']=(u['vacation'] or 0)-(u['vac_used'] or 0)
        c.execute("SELECT COALESCE(SUM(ot_h),0) as h,COALESCE(SUM(ot_amt),0) as a FROM attendance WHERE user_id=%s AND date LIKE %s",(uid,f'{month}%'))
        ot=c.fetchone(); data['otHMonth']=float(ot['h']); data['otAmtMonth']=float(ot['a'])
    conn.close(); return jsonify(data)

if __name__=='__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
