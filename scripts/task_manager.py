import json
import time
import traceback
from pathlib import Path

import psycopg
import asyncio
import asyncpg
from multiprocessing import Queue, Process
from pg_config import config
from collections import namedtuple
from datetime import datetime

from pdf_table_extractor_api import PDFTableExtractor

Job = namedtuple("Job", "id job_status start_time job_detail_id")
JobDetail = namedtuple("JobDetail", "id paper_id pdf_file err_msg last_modified tables_data")


def consumer_test(queue: Queue):
    print("Consumer running", flush=True)
    while True:
        job = queue.get()
        if job and "sentinel" in job.keys():
            print("consumer exiting", flush=True)
            break
        print(f"got {job}", flush=True)
    print("consumer done", flush=True)


def job_consumer(queue: Queue, model_dir: Path):
    _con = None
    try:
        _con = connect()
        table_extractor = PDFTableExtractor(model_dir)
        print("Consumer running", flush=True)
        while True:
            try:
                job = queue.get()
                if job and "sentinel" in job.keys():
                    print("consumer exiting", flush=True)
                    break
                print(f"got {job}", flush=True)
                try:
                    _pdf_file_path = Path(job['work_dir'], job['pdf_file'])
                    result_json = table_extractor.extract_table_contents_from_pdf(_pdf_file_path, job['work_dir'],
                                                                                  use_row_info=job['use_row_info'])
                    _job_id = job['job_id']
                    if result_json:
                        rj_str = json.dumps(result_json, indent=2)
                    else:
                        rj_str = "{}"
                    print(rj_str)
                    print('---------------')
                    update_job(_con, _job_id, 'finished', _results_json=rj_str)
                except Exception as err:
                    print("Error during Resources table extraction: " + str(err))
                    print(traceback.format_exc())
                    update_job(_con, job['job_id'], 'error', _err_msg=str(err))
            except (KeyboardInterrupt, SystemExit):
                print("consumer exiting on system exit/keyboard interrupt ...")
                break
        print("consumer done.", flush=True)
    finally:
        if _con:
            _con.close()
            print("job consumer: connection closed.", flush=True)


class TaskManager(object):
    def __init__(self, model_dir: Path):
        self.queue = Queue(maxsize=1000)
        # self.consumer_proc = Process(target=consumer_test, args=(self.queue,))
        self.consumer_proc = Process(target=job_consumer, args=(self.queue, model_dir,))

    def start(self):
        self.consumer_proc.start()

    def shutdown(self):
        if self.queue:
            self.queue.put({'sentinel': True})
            self.consumer_proc.join()

    def add_job(self, _con, _paper_id, _pdf_file, _work_dir, use_row_info=False):
        _job_id = create_job(_con, _paper_id, _pdf_file)
        self.queue.put({'job_id': _job_id, 'paper_id': _paper_id,
                        'pdf_file': _pdf_file,
                        'work_dir': _work_dir,
                        'use_row_info': use_row_info})
        return _job_id

    async def add_job_async(self, _pool,  _paper_id, _pdf_file, _work_dir, use_row_info=False):
        _job_id = await create_job_async(_pool, _paper_id, _pdf_file, use_row_info=use_row_info)
        self.queue.put({'job_id': _job_id, 'paper_id': _paper_id,
                        'pdf_file': _pdf_file,
                        'work_dir': _work_dir,
                        'use_row_info': use_row_info})
        return _job_id


def connect():
    params = config()
    params2 = params.copy()
    del params2['database']
    params2['dbname'] = params['database']
    con = psycopg.connect(**params2)
    return con


async def connect2():
    params = config()
    con = await asyncpg.connect(**params)
    return con


async def create_db_pool():
    params = config()
    pool = await asyncpg.create_pool(**params)
    return pool


def create_job(_con, _paper_id, _pdf_file):
    q = """insert into job_detail (paper_id, pdf_file, last_modified) values(%s, %s, %s) returning job_detail_id"""
    cur_time = datetime.now()
    cursor = _con.cursor()
    cursor.execute(q, (_paper_id, _pdf_file, cur_time))
    job_detail_id = cursor.fetchone()[0]
    jq = """insert into jobs (job_status, start_time, job_detail_id) values(%s, %s, %s) returning job_id"""
    cursor.execute(jq, ('waiting', cur_time, job_detail_id))
    _job_id = cursor.fetchone()[0]
    _con.commit()
    cursor.close()
    return _job_id


async def create_job_async(_pool, _paper_id, _pdf_file, use_row_info: bool):
    q = """insert into job_detail (paper_id, pdf_file, last_modified, params) values($1, $2, $3, $4) returning 
           job_detail_id """
    jq = """insert into jobs (job_status, start_time, job_detail_id) values($1, $2, $3) returning job_id"""
    async with _pool.acquire() as conn:
        async with conn.transaction():
            cur_time = datetime.now()
            params = "use_row_info=True" if use_row_info else None
            job_detail_id = await conn.fetchval(q, _paper_id, _pdf_file, cur_time, params)
            _job_id = await conn.fetchval(jq, 'waiting', cur_time, job_detail_id)
            return _job_id


def update_job(_con, _job_id, _job_status, _results_json=None, _err_msg=None):
    q = """update jobs set job_status = %s where job_id = %s returning job_detail_id"""
    jq = """update job_detail set tables_data = %s, err_msg = %s, last_modified = %s where job_detail_id = %s"""
    cursor = None
    try:
        cursor = _con.cursor()
        cursor.execute(q, (_job_status, _job_id))
        job_detail_id = cursor.fetchone()[0]
        if _results_json is not None or _err_msg is not None:
            cur_time = datetime.now()
            json_str = None
            if _results_json is not None:
                json_str = _results_json
            cursor.execute(jq, (json_str, _err_msg, cur_time, job_detail_id))
        _con.commit()
    except (Exception, psycopg.Error) as error:
        print("Database error", error)
    finally:
        if cursor:
            cursor.close()


async def remove_job_async(_pool, _job_id):
    q = "select job_detail_id from jobs where job_id = $1"
    async with _pool.acquire() as conn:
        async with conn.transaction():
            jd_ids = []
            async for rec in conn.cursor(q, _job_id):
                jd_ids.append(rec[0])
            print(f"deleting job_id={_job_id}")
            await conn.execute("delete from jobs where job_id = $1", _job_id)
            for jd_id in jd_ids:
                print(f"deleting jd_id {jd_id}")
                await conn.execute("delete from job_detail where job_detail_id = $1", jd_id)
            return True


async def remove_job_by_paper_id_async(_pool, _paper_id):
    q = '''select j.job_id, d.job_detail_id from jobs j, job_detail d where j.job_detail_id = d.job_detail_id and 
           d.paper_id = $1 '''
    async with _pool.acquire() as conn:
        async with conn.transaction():
            job_ids = set()
            jd_ids = set()
            async for rec in conn.cursor(q, _paper_id):
                job_ids.add(rec[0])
                jd_ids.add((rec[1]))
            for job_id in job_ids:
                print(f"deleting job_id={job_id}")
                await conn.execute("delete from jobs where job_id = $1", job_id)
            for jd_id in jd_ids:
                print(f"deleting jd_id {jd_id}")
                await conn.execute("delete from job_detail where job_detail_id = $1", jd_id)
            return True


def remove_job(_con, _job_id):
    cursor = None
    try:
        cursor = _con.cursor()
        with _con.transaction():
            cursor.execute("select job_detail_id from jobs where job_id = %s", (_job_id,))
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    cursor.execute("delete from job_detail where job_detail_id = %s", (row[0],))
            cursor.execute("delete from jobs where job_id = %s", (_job_id,))
    finally:
        if cursor:
            cursor.close()


async def list_jobs_async(_pool):
    q = """select a.job_id, a.job_status, b.paper_id, b.pdf_file, b.params from jobs a, 
           job_detail b where a.job_detail_id = b.job_detail_id"""
    ji_list = []
    async with _pool.acquire() as conn:
        async with conn.transaction():
            async for rec in conn.cursor(q):
                ji = {'job_id': rec[0], 'job_status': rec[1], 'paper_id': rec[2],
                      'pdf_file': rec[3], 'params': rec[4]}
                ji_list.append(ji)
    return ji_list


async def get_job_details_async(_pool, _job_id):
    q = """select a.job_id, a.job_status, b.err_msg, b.tables_data, b.paper_id, b.pdf_file, b.params from jobs a, 
           job_detail b where a.job_detail_id = b.job_detail_id and a.job_id = $1"""
    async with _pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(q, _job_id)
            if row:
                result_json_data = {}
                if row[3]:
                    result_json_data = json.loads(row[3])
                params = ""
                if row[6]:
                    params = row[6]
                return {'job_id': row[0], 'job_status': row[1],
                        'paper_id': row[4], 'pdf_file': row[5],
                        'params': params,
                        "err_msg": row[2], "result": result_json_data}
            else:
                return None


def get_job_details(_con, _job_id):
    q = """select a.job_id, a.job_status, b.err_msg, b.tables_data from jobs a, job_detail b 
           where a.job_detail_id = b.job_detail_id and a.job_id = %s"""
    cursor = None
    try:
        cursor = _con.cursor()
        cursor.execute(q, (_job_id,))
        row = cursor.fetchone()
        if row:
            result_json_data = {}
            if row[3]:
                result_json_data = json.loads(row[3])
                print("Type:", type(result_json_data))
                # print("result_json_data")
                # print(result_json_data)

            return {'job_id': row[0], 'job_status': row[1],
                    "err_msg": row[2], "result": result_json_data}
        else:
            return None
    except (Exception, psycopg.Error) as error:
        print("Database error", error)
        return None
    finally:
        if cursor:
            cursor.close()


def get_jobs_with_status(_con, _job_status):
    q = """select job_id, job_status, start_time, job_detail_id from jobs where job_status = %s"""
    cursor = None
    jobs = []
    try:
        cursor = _con.cursor()
        cursor.execute(q, (_job_status,))
        for row in iter_row(cursor):
            job = Job(id=row[0], job_status=row[1], start_time=row[2], job_detail_id=row[3])
            jobs.append(job)
        return jobs
    except (Exception, psycopg.Error) as error:
        print("Database error", error)
    finally:
        if cursor:
            cursor.close()


async def get_jobs_with_status_async(_pool, _job_status):
    q = """select job_id, job_status, start_time, job_detail_id from jobs where job_status = $1"""
    jobs = []
    async with _pool.acquire() as conn:
        async with conn.transaction():
            async for rec in conn.cursor(q, _job_status):
                job = Job(id=rec[0], job_status=rec[1], start_time=rec[2], job_detail_id=rec[3])
                jobs.append(job)
    return jobs


def iter_row(_cursor, size=10):
    while True:
        rows = _cursor.fetchmany(size)
        if not rows:
            break
        for row in rows:
            yield row


def test_task_manager(model_dir: Path):
    task_man = None
    conn = connect()
    try:

        task_man = TaskManager(conn, model_dir)
        task_man.start()
        for i in range(10):
            pif = 'paper_{:d}'
            task_man.add_job(pif.format(i), "main.pdf", "/tmp")
            time.sleep(1)
        print("Jobs submission is finished.", flush=True)
        time.sleep(2)
    finally:
        if task_man:
            task_man.shutdown()
        if conn:
            conn.close()


def test_driver():
    conn = connect()
    job_id = create_job(conn, "my_paper", "main.pdf")
    print(f"job id:{job_id}")

    if conn:
        conn.close()


async def async_test_driver():
    conn = await connect2()
    row = await conn.fetchrow('select * from jobs where job_id = $1', 2)
    if row:
        print(row)
    await conn.close()


async def async_test_pool():
    pool = await create_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow('select * from jobs where job_id = $1', 2)
        if row:
            print(row)
    jobs = await get_jobs_with_status_async(pool, 'finished')
    print("Finished Jobs")
    for job in jobs:
        print(job)
        job_detail = await get_job_details_async(pool, job.id)
        print(job_detail)
        print('-' * 60)

    print('=' * 80)
    res = await get_job_details_async(pool, 2)
    print(res)
    await pool.close()


if __name__ == '__main__':
    # test_task_manager()
    asyncio.get_event_loop().run_until_complete(async_test_pool())

