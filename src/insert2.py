import psycopg2
import random




def insert_floats():
    sql = 'INSERT INTO suppliers(voltage, temp) VALUES(%s)'
    conn = psycopg2.connect(host="localhost",database="suppliers",user="postgres", password="post")
    vendor_list = []
    for n in range(0,10):
        v = random.uniform(100.0,200.0)
        t = random.uniform(10.5,30.0)
        entry = (str(v),str(t),)
        vendor_list.append(entry)
    try:
        cur = conn.cursor()
        cur.executemany(sql,vendor_list)
        conn.commit()
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
