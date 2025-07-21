import pymysql as conn

conn = conn.connect(host='localhost',user='root',password='Razi@123',database='construction_site_management')
cursor = conn.cursor()