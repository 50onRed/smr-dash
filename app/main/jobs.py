from ..models import Job
from flask import current_app, json
import tempfile
import redis
import subprocess

if hasattr(tempfile, "TemporaryDirectory"):
    TemporaryDirectory = tempfile.TemporaryDirectory
else:
    # not in python versions < 3.2
    import shutil as _shutil
    class TemporaryDirectory(object):
        # Handle mkdtemp raising an exception
        name = None
        _closed = False

        def __init__(self, suffix="", prefix=tempfile.template, dir=None):
            self.name = tempfile.mkdtemp(suffix, prefix, dir)

        def __enter__(self):
            return self.name

        def __exit__(self, exc, value, tb):
            if self.name is not None and not self._closed:
                _shutil.rmtree(self.name)
                self._closed = True

def get_redis_connection():
    return redis.from_url(current_app.config.get("REDIS_URI"))

def enqueu_job(job_id, date_range, start_date, end_date):
    redis = get_redis_connection()
    job_definition = {
        "id": job_id,
        "date_range": date_range,
        "start_date": start_date,
        "end_date": end_date
    }
    redis.rpush("jobs", json.dumps(job_definition))

def job_runner():
    redis = get_redis_connection()
    while True:
        job_definition = json.loads(redis.blpop("jobs"))
        run_job(
            job_definition["id"],
            job_definition["date_range"],
            job_definition["start_date"],
            job_definition["end_date"]
        )

def run_job(job_id, date_range, start_date, end_date):
    job = Job.query.get(job_id)

    with TemporaryDirectory(dir=current_app.config.get("SMR_JOB_DEFINITION_DIRECTORY")) as temp_dir:
        with tempfile.NamedTemporaryFile(delete=False, prefix="smr", suffix=".py", dir=temp_dir) as job_definition_file:
            with tempfile.NamedTemporaryFile(delete=False, dir=current_app.config.get("SMR_JOB_OUTPUT_DIRECTORY")) as job_output_file:
                # TODO: job might have changed since the time it was scheduled, need to snapshot
                job_definition_file.write(job.body)

                args = ["smr", "--no-output-job-progress", "--output-filename", job_output_file.name]
                if job.author.aws_access_key:
                    args.append("--aws-access-key")
                    args.append(job.author.aws_access_key)
                if job.author.aws_secret_key:
                    args.append("--aws-secret-key")
                    args.append(job.author.aws_secret_key)
                if date_range:
                    args.append("--date-range")
                    args.append(str(date_range))
                if start_date:
                    args.append("--start-sate")
                    args.append(start_date)
                if end_date:
                    args.append("--end-date")
                    args.append(end_date)
                args.append(job_definition_file.name)
                print " ".join(args)

                # run in a separate process cause we don't want different jobs to interfere with each other
                p = subprocess.Popen(args)
                p.wait() # blocks until the job is finished
                # TODO: notify someone/something
