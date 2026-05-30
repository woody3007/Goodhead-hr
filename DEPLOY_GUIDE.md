# คู่มือ Deploy GoodHead HR System บน Railway
## ใช้เวลาประมาณ 15 นาที

---

## ขั้นตอนที่ 1 — สมัคร GitHub (ฟรี)
1. เปิด **github.com** → คลิก "Sign up"
2. กรอก Email, Password, Username
3. ยืนยัน Email

---

## ขั้นตอนที่ 2 — Upload โค้ดขึ้น GitHub

### วิธีง่ายที่สุด (ไม่ต้องใช้ command line):
1. Login GitHub → คลิก **"+"** มุมบนขวา → **"New repository"**
2. ตั้งชื่อ: `goodhead-hr`
3. เลือก **Private** (ข้อมูลบริษัท)
4. คลิก **"Create repository"**
5. คลิก **"uploading an existing file"**
6. ลากไฟล์ทั้งหมดจากโฟลเดอร์ `goodhead-hr` ขึ้นไป:
   ```
   goodhead-hr/
   ├── backend/
   │   └── app.py
   ├── frontend/
   │   └── index.html
   ├── requirements.txt
   ├── Procfile
   ├── railway.json
   └── .gitignore
   ```
7. คลิก **"Commit changes"**

---

## ขั้นตอนที่ 3 — สมัคร Railway (ฟรี)
1. เปิด **railway.app** → คลิก "Start a New Project"
2. เลือก **"Login with GitHub"** → อนุญาต
3. Railway จะเชื่อมกับ GitHub ของคุณ

---

## ขั้นตอนที่ 4 — Deploy โปรเจค
1. ใน Railway Dashboard คลิก **"New Project"**
2. เลือก **"Deploy from GitHub repo"**
3. เลือก repo `goodhead-hr`
4. Railway จะ detect Python อัตโนมัติและเริ่ม build

---

## ขั้นตอนที่ 5 — เพิ่ม PostgreSQL Database
1. ใน Railway Project คลิก **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway จะสร้าง database และเพิ่ม `DATABASE_URL` ให้อัตโนมัติ
3. รอ build เสร็จ (ประมาณ 2-3 นาที)

---

## ขั้นตอนที่ 6 — เปิดระบบ
1. คลิกที่ service ของคุณ → **"Settings"** → **"Domains"**
2. คลิก **"Generate Domain"**
3. ได้ URL เช่น `goodhead-hr.up.railway.app`
4. เปิด URL นั้นในเบราว์เซอร์ → เข้าสู่ระบบได้เลย!

---

## ขั้นตอนที่ 7 — แก้ไข Frontend ให้ชี้ไป Railway
เปิดไฟล์ `frontend/index.html` แล้วหาบรรทัด:
```javascript
const API_URL = window.location.hostname === 'localhost' || window.location.protocol === 'file:'
  ? '' 
  : window.location.origin + '/api';
```
ไม่ต้องแก้อะไร — ระบบจะ detect อัตโนมัติว่าอยู่บน Railway และใช้ Backend จริง

---

## Login ครั้งแรก
- Username: `manager`
- Password: `1234`
- **แนะนำ: เปลี่ยนรหัสผ่านทันทีหลัง login ครั้งแรก**

---

## ราคา Railway (ฟรีเดือนแรก)
| Plan | ราคา | เหมาะกับ |
|------|------|----------|
| Hobby (Free) | $0/เดือน (500 ชม) | ทดสอบ |
| Hobby ($5) | $5/เดือน | พนักงาน < 50 คน |
| Pro | $20/เดือน | พนักงาน > 50 คน |

> สำหรับ 138 คน แนะนำ **Hobby $5/เดือน** ครับ

---

## ปัญหาที่พบบ่อย

### Build ล้มเหลว
- ตรวจสอบว่า upload ไฟล์ `requirements.txt` ครบ

### เข้าระบบไม่ได้
- รอ database initialize (ครั้งแรกใช้เวลา 1-2 นาที)
- ลอง refresh หน้าเว็บ

### ต้องการความช่วยเหลือ
- ติดต่อผ่าน Claude ได้เลยครับ
