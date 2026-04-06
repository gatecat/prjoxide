"""
General Utilities for Fuzzing
"""
import asyncio
import logging
import os
import signal
import threading
import time
import traceback
from asyncio import CancelledError
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, Future
from contextlib import contextmanager
from signal import SIGINT, SIGTERM
from threading import Thread, RLock

import lapie

async def wrap_future(f):
    if f is not None:
        await asyncio.wrap_future(f)

is_in_loop = False

def jobs():
    if "OXIDE_JOBS" in os.environ:
        jobs = int(os.environ["OXIDE_JOBS"])
    else:
        jobs = 4
    return jobs

@contextmanager
def Executor(executor=None):
    cleanup = executor is None
    if executor is None:
        executor = ThreadPoolExecutor(jobs())
    try:
        yield executor
    finally:
        if cleanup:
            executor.shutdown(wait=True)

error_count = 0
def parallel_foreach(items, func, jobs = None):
    """
    Run a function over a list of values, running a number of jobs
    in parallel. OXIDE_JOBS should be set to the number of jobs to run,
    defaulting to 4.
    """
    if jobs is None:
        if "OXIDE_JOBS" in os.environ:
            jobs = int(os.environ["OXIDE_JOBS"])
        else:
            jobs = 4

    items_queue = list(items)
    items_lock = RLock()

    exception = None

    global is_in_loop
    is_in_loop = True
    def runner():
        nonlocal exception

        try:            
            while True:
                with items_lock:
                    if len(items_queue) == 0:
                        return
                    item = items_queue[0]
                    items_queue.pop(0)

                func(item)
        except Exception as e:
            global error_count
            if error_count < 10:
                error_count = error_count + 1
                logging.error(f"Error: {e}")
                traceback.print_exc()
            
            exception = e
            with items_lock:
                items_queue.clear()

    threads = [Thread(target=runner) for i in range(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if exception is not None:
        raise exception
    is_in_loop = False

def gather_futures(futures, name = None):
    """
    Returns a Future that completes when all input futures complete.
    Result is a list of results in the same order.
    """
    out = Future()
    n = len(futures)
    results = [None] * n
    remaining = n
    lock = threading.Lock()

    def _done(i, fut):
        nonlocal remaining
        try:
            if hasattr(fut, "result"):
                res = fut.result()
            else:
                res = fut
        except Exception as e:
            # fail fast: propagate first exception
            with lock:
                if not out.done():
                    out.set_exception(e)
            return

        with lock:
            if out.done():
                return
            results[i] = res
            remaining -= 1
            if remaining == 0:
                out.set_result(results)

    executor = None
    for i, fut in enumerate(futures):
        if hasattr(fut, 'executor'):
            executor = fut.executor
        if hasattr(fut, "result"):
            fut.add_done_callback(lambda f, i=i: _done(i, f))
        else:
            _done(i, fut)

    if executor is not None and hasattr(executor, "register_future"):
        executor.register_future(out)

    if name is not None:
        out.name = name

    if n == 0:
        out.set_result([])

    return out

def chain(future, func, *args, **kwargs):
    name = None
    if isinstance(func, str):
        name = func
        func = args[0]
        args = args[1:]

    if isinstance(future, list):
        future = gather_futures(future)

    fut = Future()

    def _done(f):
        r = None
        try:
            r = f.result()
            if hasattr(f, 'executor'):
                new_f = f.executor.submit(func, r, *args, **kwargs)
                new_f.add_done_callback(lambda f, fut=fut: fut.set_result(f.result()))
                new_f.name = name
            else:
                fut.set_result(func(r, *args, **kwargs))
        except CancelledError as e:
            fut.set_exception(e)
        except BaseException as e:
            logging.error(f"Encountered exception while calling {func} with {r} {args} {kwargs}")
            traceback.print_exception(e)
            try:
                raise RuntimeError(f"Encountered exception while calling {func} with {r} {args} {kwargs}") from e
            except BaseException as f:
                fut.set_exception(f)

        except:
            fut.set_exception(Exception("Unknown exception in future"))

    future.add_done_callback(_done)
    if hasattr(future, 'executor'):
        future.executor.register_future(fut)

    if name is not None:
        fut.name = name

    return fut

class AsyncExecutor:
    def __init__(self, executor):
        self.futures = []
        self.lock = RLock()
        self.loop = asyncio.get_running_loop()
        self.executor = executor
    def submit(self, f, *args, **kwargs):
        future = self.loop.run_in_executor(None, lambda args=args,kwargs=kwargs: f(*args, **kwargs))

        future.name = f.__name__
        self.register_future(future)
        return future

    def register_future(self, future):
        future.executor = self
        with self.lock:
            self.futures.append(future)

    def iterate_futures(self):
        with self.lock:
            local_futures = self.futures
            self.futures = []

        new_futures = []
        for f in local_futures:
            yield f
            if not f.done():
                new_futures.append(f)

        with self.lock:
            self.futures.extend(new_futures)

    def busy(self):
        return len(self.futures) > 0

    def task_count(self):
        return len(self.futures)

    def shutdown(self):
        self.executor.shutdown(wait=True, cancel_futures=True)

def FuzzerAsyncMain(f, *args, **kwargs):
    from fuzzconfig import FuzzConfig

    import rich.console
    from rich.live import Live
    from rich.panel import Panel

    console = rich.console.Console()
    import sys
    orignal_stdout = sys.stdout
    sys.stdout = console.file

    from rich.logging import RichHandler

    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(
        level=LOGLEVEL,
        handlers=[RichHandler(console=console, show_time=False, show_path=False, rich_tracebacks=True)],
        force=True
    )

    start_time = time.time()

    async def start(f):
        async_executor = None

        int_count = 0
        def sighandler(sig, frame):
            nonlocal int_count
            int_count = int_count + 1
            if int_count > 2:
                logging.warning("Forcing exit")
                os._exit(-1)

            for t in asyncio.all_tasks():
                t.cancel("Signal interrupt")

            if async_executor is not None:
                async_executor.shutdown()

        for sig in [SIGINT, SIGTERM]:
            signal.signal(sig, sighandler)

        try:
            FUZZER_TITLE = os.environ.get("FUZZER_TITLE", "")
            def status_panel(status: str) -> Panel:
                return Panel(
                    f"[bold cyan]{status}[/bold cyan]",
                    title=f"Status - {FUZZER_TITLE}",
                    border_style="blue",
                    height=3,
                )

            async def ui(async_executor, task):
                try:
                    with Live(status_panel(""), refresh_per_second=10, console=console) as live:
                        finished_tasks = 0

                        while async_executor.busy() or not task.done():
                            histogram = defaultdict(int)

                            def process_future(fut):
                                nonlocal finished_tasks

                                name = "anon"
                                if hasattr(fut, "name"):
                                    name = fut.name
                                elif hasattr(fut, "get_stack"):
                                    fn = fut.get_stack()[-1].f_code.co_name
                                    if fn != "ui" and fn != "start":
                                        ln = fut.get_stack()[-1].f_lineno
                                        name = f"{fn}:{ln}"
                                    else:
                                        name = None

                                if name is not None:
                                    histogram[name] = histogram[name] + 1

                                if fut.done():
                                    try:
                                        if fut.exception() is not None:
                                            if not isinstance(fut.exception(), CancelledError):
                                                logging.error(f"Encountered exception in future {fut}: {fut.exception()}")
                                                traceback.print_exception(fut.excecption())
                                                all_exceptions.append(fut.exception())
                                        else:
                                            finished_tasks = finished_tasks + 1
                                            fut.result()
                                    except CancelledError as e:
                                        pass
                                    except BaseException as e:
                                        all_exceptions.append(e)

                            for fut in async_executor.iterate_futures(): process_future(fut)
                            for fut in asyncio.all_tasks(): process_future(fut)

                            text = f"{list(histogram.items())} {async_executor.task_count()} {finished_tasks} finished {len(all_exceptions)} errors, built/cached {FuzzConfig.radiant_builds}/{FuzzConfig.radiant_cache_hits} tool queries {lapie.run_with_udb_cnt} {int(time.time() - start_time)}s"

                            live.update(status_panel(text))
                            await asyncio.sleep(1)
                except BaseException as e:
                    logging.warning(f"Shutting down UI due to exception {e}")
                    traceback.print_exception(e)
                    raise
                finally:
                    logging.info("Exit ui thread")


            with Executor() as executor:
                try:
                    asyncio.get_running_loop().set_default_executor(executor)

                    async_executor = AsyncExecutor(executor)

                    all_exceptions = []

                    task = asyncio.create_task(f(async_executor, *args, **kwargs))
                    ui_task = ui(async_executor, task)

                    (_, task_result) = await asyncio.gather(ui_task, task, return_exceptions=False)

                    logging.info(f"UI and main task finished {task_result}")

                except CancelledError as e:
                    logging.warning("Cancelling all executor jobs")
                    #traceback.print_exception(e)
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                except BaseException as e:
                    logging.warning(f"Shutting down executor due to exception {e}")
                    traceback.print_exception(e)
                    executor.shutdown(wait=True, cancel_futures=True)
                    raise
                finally:
                    logging.info("Shutting down threads")
            logging.info("Shut down threads")

        except KeyboardInterrupt:
            logging.warning("Keyboard interrupt")
        except CancelledError:
            logging.warning("Cancelled")
            raise

        if len(all_exceptions):
            logging.error(f"Encountered the following {len(all_exceptions)} errors:")
            for e in all_exceptions:
                traceback.print_exception(e)

        logging.info(f"Processed {FuzzConfig.radiant_builds}/{FuzzConfig.radiant_cache_hits} bitfiles in {time.time() - start_time} seconds. Skipped {FuzzConfig.delta_skips} solves due to existing .delta files")

    asyncio.run(start(f))



def FuzzerMain(f):
    async def async_main(executor):
        if f.__code__.co_argcount > 0:
            return f(executor)
        return f()

    FuzzerAsyncMain(async_main)
