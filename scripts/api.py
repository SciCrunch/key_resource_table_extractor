import shutil
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.encoders import jsonable_encoder
import aiofiles

from pg_config import get_api_key, get_rm_model_dir
from task_manager import TaskManager, create_db_pool, get_job_details_async, remove_job_async
from task_manager import remove_job_by_paper_id_async, list_jobs_async

WD = "/tmp/cache"
Path(WD).mkdir(exist_ok=True)

# con = connect()
API_KEY = get_api_key()
rm_model_dir = model_dir = get_rm_model_dir()
task_manager = TaskManager(Path(model_dir))


def save_upload_file(upload_file: UploadFile, destination: Path) -> None:
    try:
        with destination.open("wb") as f:
            shutil.copyfileobj(upload_file.file, f)
    finally:
        upload_file.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _app.state.pool = await create_db_pool()
    print("Created db connection pool.", flush=True)
    task_manager.start()
    yield
    print("shutting down task manager...", flush=True)
    task_manager.shutdown()
    print("shut down task manager.", flush=True)
    if _app.state.pool:
        await _app.state.pool.close()
        print("shut down connection pool.", flush=True)
    # con.close()


app = FastAPI(lifespan=lifespan)


@app.post("/pdf_table_extractor/submit_paper")
async def submit_paper(paper_id: str, pdf_file: UploadFile, use_row_info: bool = False):
    paper_dir = Path(WD, paper_id + "_use_row_info") if use_row_info else Path(WD, paper_id)
    if paper_dir.is_dir():
        raise HTTPException(status_code=400, detail="Already exists")
        # shutil.rmtree(paper_dir)

    paper_dir.mkdir(parents=True, exist_ok=True)
    dest = Path(paper_dir, pdf_file.filename)
    async with aiofiles.open(dest, 'wb') as f:
        content = await pdf_file.read()
        await f.write(content)
    # _job_id = task_manager.add_job(con, paper_id, pdf_file.filename, paper_dir, use_row_info=use_row_info)
    pool = app.state.pool
    _job_id = await task_manager.add_job_async(pool, paper_id, pdf_file.filename, paper_dir,
                                               use_row_info=use_row_info)
    return {"filename": pdf_file.filename, "paper_id": paper_id, "job_id": _job_id}


@app.get("/pdf_table_extractor/list_jobs")
async def list_jobs(api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="You are not authorized to list jobs!")
    pool = app.state.pool
    ji_list = await list_jobs_async(pool)
    return jsonable_encoder(ji_list)


@app.get("/pdf_table_extractor/get_job_results")
async def get_job_results(job_id: str):
    # get job results and/or job status
    # job_detail = task_manager.get_job_detail(con, job_id)
    pool = app.state.pool
    job_detail = await get_job_details_async(pool, int(job_id))

    if not job_detail:
        raise HTTPException(status_code=404, detail="Job with ID %s Not found".format(job_id))
    return jsonable_encoder(job_detail)


@app.delete("/pdf_table_extractor/remove_job")
async def remove_job(job_id: str, api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="You are not authorized to remove a job!")
    pool = app.state.pool
    ok = await remove_job_async(pool, int(job_id))
    return jsonable_encoder({"job_id": job_id, 'removed': ok})


@app.delete("/pdf_table_extractor/remove_jobs_by")
async def remove_job(paper_id: str, api_key: str):
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="You are not authorized to remove a job!")
    pool = app.state.pool
    ok = await remove_job_by_paper_id_async(pool, paper_id)
    return jsonable_encoder({"paper_id": paper_id, "removed": ok})
